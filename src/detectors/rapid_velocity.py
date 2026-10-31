"""Detector for Rapid Velocity Transfers and Burst Inflows.
Identifies high-frequency transaction bursts over compressed timestamps.
"""
from __future__ import annotations
from typing import Dict, Any, List
import networkx as nx
import pandas as pd


def detect_rapid_velocity(G: nx.MultiDiGraph, data_dict: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
    """Detects rapid-fire transfer sequences indicative of automated stripping or bot-driven laundering."""
    findings = []
    if "transactions" not in data_dict or data_dict["transactions"] is None or data_dict["transactions"].empty:
        return findings

    df_tx = data_dict["transactions"].copy()
    if "timestamp" not in df_tx.columns:
        return findings

    try:
        df_tx["dt"] = pd.to_datetime(df_tx["timestamp"], errors="coerce")
    except Exception:
        return findings

    df_valid = df_tx.dropna(subset=["dt"]).sort_values("dt")
    if df_valid.empty:
        return findings

    # Check for accounts with 3+ transactions within a 2-hour window
    for acc, group in df_valid.groupby("source_account_id"):
        acc = str(acc)
        if len(group) >= 3:
            group = group.sort_values("dt")
            time_span = (group["dt"].iloc[-1] - group["dt"].iloc[0]).total_seconds()
            if time_span <= 7200 and time_span >= 0:  # 2 hours
                total_val = float(group["amount"].sum())
                tx_ids = [str(x) for x in group["transaction_id"].tolist()]
                targets = [str(x) for x in group["target_account_id"].unique().tolist()]

                findings.append({
                    "detector": "Velocity Burst",
                    "type": "rapid_velocity",
                    "severity": "HIGH",
                    "score": 75,
                    "target_entity": acc,
                    "entities": [acc] + targets,
                    "transactions": tx_ids,
                    "title": f"High Velocity Outflow: {acc}",
                    "description": f"Account {acc} sent {len(group)} transactions (${total_val:,.2f}) within {int(time_span/60)} minutes.",
                    "evidence": [
                        f"Source: {acc}",
                        f"Window: {int(time_span/60)} minutes",
                        f"Count: {len(group)} transactions",
                        f"Volume: ${total_val:,.2f}",
                    ],
                    "legitimate_alternative": "Automated batch payroll run, API-driven vendor settlement, or automated sweep account.",
                })

    return findings
