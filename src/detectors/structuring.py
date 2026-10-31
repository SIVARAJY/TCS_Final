"""Detector for Structuring (Smurfing).
Flags clusters of transactions just below regulatory reporting thresholds (e.g. $10,000).
"""
from __future__ import annotations
from typing import Dict, Any, List
import networkx as nx
import pandas as pd


def detect_structuring(G: nx.MultiDiGraph, data_dict: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
    """Flags accounts generating multiple transactions just under the $10,000 threshold."""
    findings = []
    if "transactions" not in data_dict or data_dict["transactions"] is None or data_dict["transactions"].empty:
        return findings

    df_tx = data_dict["transactions"]
    threshold_min = 8500.0
    threshold_max = 9999.0

    # Filter transactions in the suspicious structuring corridor
    df_structured = df_tx[(df_tx["amount"] >= threshold_min) & (df_tx["amount"] <= threshold_max)]

    if df_structured.empty:
        return findings

    # Group by source account
    for src_acc, group in df_structured.groupby("source_account_id"):
        src_acc = str(src_acc)
        if len(group) >= 2:
            total_amt = float(group["amount"].sum())
            txn_ids = [str(t) for t in group["transaction_id"].tolist()]
            target_accs = [str(t) for t in group["target_account_id"].unique().tolist()]

            severity = "CRITICAL" if len(group) >= 4 or total_amt >= 30000 else "HIGH"

            findings.append({
                "detector": "CTR Structuring",
                "type": "structuring",
                "severity": severity,
                "score": 90 if severity == "CRITICAL" else 75,
                "target_entity": src_acc,
                "entities": [src_acc] + target_accs,
                "transactions": txn_ids,
                "title": f"Structuring Under CTR Threshold: {src_acc}",
                "description": f"Source {src_acc} initiated {len(group)} transactions between ${threshold_min:,.0f} and ${threshold_max:,.0f} totaling ${total_amt:,.2f}.",
                "evidence": [
                    f"Account: {src_acc}",
                    f"Count: {len(group)} transactions within $8.5k–$9.99k band",
                    f"Cumulative value: ${total_amt:,.2f}",
                    f"Individual amounts: {', '.join(f'${a:,.2f}' for a in group['amount'].tolist())}",
                ],
                "legitimate_alternative": "Repeated standard invoices, installment contract payments, or scheduled high-value supplier retainers.",
            })

    return findings
