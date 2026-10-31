"""Detector for Fan-In, Fan-Out, and Pass-Through Mule Accounts.
Flags accounts with high in-degree from multiple disparate sources followed by rapid fund dispersal.
"""
from __future__ import annotations
from typing import Dict, Any, List
import networkx as nx
import pandas as pd


def detect_fan_in_out(G: nx.MultiDiGraph, data_dict: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
    """Detects accounts acting as hubs (fan-in or pass-through money mules)."""
    findings = []
    if "transactions" not in data_dict or data_dict["transactions"] is None or data_dict["transactions"].empty:
        return findings

    # Look for account nodes with high in-degree or in-degree + out-degree ratio
    for node, d in G.nodes(data=True):
        if d.get("type") != "account":
            continue

        in_edges = list(G.in_edges(node, data=True))
        out_edges = list(G.out_edges(node, data=True))

        in_txns = [ed for ed in in_edges if ed[2].get("type") == "TRANSFERRED"]
        out_txns = [ed for ed in out_edges if ed[2].get("type") == "TRANSFERRED"]

        in_senders = set(ed[0] for ed in in_txns)
        out_receivers = set(ed[1] for ed in out_txns)

        in_volume = sum(ed[2].get("amount", 0.0) for ed in in_txns)
        out_volume = sum(ed[2].get("amount", 0.0) for ed in out_txns)

        # Condition 1: Fan-In (3+ distinct senders feeding one account)
        if len(in_senders) >= 3:
            severity = "CRITICAL" if len(in_senders) >= 5 or len(out_receivers) >= 1 else "HIGH"
            txn_ids = [ed[2].get("transaction_id") for ed in in_txns if ed[2].get("transaction_id")]
            all_involved = [node] + list(in_senders)

            findings.append({
                "detector": "Mule Fan-In",
                "type": "fan_in",
                "severity": severity,
                "score": 85 if severity == "CRITICAL" else 70,
                "target_entity": node,
                "entities": all_involved,
                "transactions": txn_ids,
                "title": f"Mule Fan-In Hub: {node}",
                "description": f"Account {node} received funds from {len(in_senders)} distinct source accounts (${in_volume:,.2f} total).",
                "evidence": [
                    f"Target account: {node}",
                    f"Unique senders: {', '.join(sorted(in_senders)[:5])}",
                    f"Inflow amount: ${in_volume:,.2f}",
                ],
                "legitimate_alternative": "May represent an active merchant checkout account, charity collection, or group event organizer.",
            })

        # Condition 2: Pass-Through Mule (rapid dispersal: inflow roughly matches outflow)
        if in_volume > 5000 and out_volume > 0:
            dispersal_ratio = out_volume / in_volume
            if 0.65 <= dispersal_ratio <= 1.35 and len(in_senders) >= 2:
                all_involved = list(set([node] + list(in_senders) + list(out_receivers)))
                findings.append({
                    "detector": "Pass-Through Dispersal",
                    "type": "pass_through",
                    "severity": "CRITICAL",
                    "score": 90,
                    "target_entity": node,
                    "entities": all_involved,
                    "transactions": [ed[2].get("transaction_id") for ed in in_txns + out_txns if ed[2].get("transaction_id")],
                    "title": f"Pass-Through Conduit: {node}",
                    "description": f"Account {node} received ${in_volume:,.2f} and immediately dispersed ${out_volume:,.2f} ({dispersal_ratio*100:.1f}% velocity).",
                    "evidence": [
                        f"Conduit account: {node}",
                        f"Inflow: ${in_volume:,.2f} from {len(in_senders)} accounts",
                        f"Outflow: ${out_volume:,.2f} to {len(out_receivers)} accounts",
                        f"Dispersal ratio: {dispersal_ratio*100:.1f}%",
                    ],
                    "legitimate_alternative": "Could be escrow service, payroll intermediary, or institutional broker-dealer settlement.",
                })

    return findings
