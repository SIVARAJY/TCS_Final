"""Detector A09: Dispersal Account (Out-Degree Concentration).
Uses out-degree counts to identify hub accounts dispersing funds to multiple disparate destinations.
"""
from __future__ import annotations
from typing import Dict, Any, List
import networkx as nx
import pandas as pd


def detect_a09_dispersal_account(
    G: nx.MultiDiGraph,
    data_dict: Dict[str, pd.DataFrame],
) -> List[Dict[str, Any]]:
    """A09 Dispersal Account: Identifies high out-degree accounts rapidly distributing funds."""
    findings = []
    if "transactions" not in data_dict or data_dict["transactions"] is None or data_dict["transactions"].empty:
        return findings

    # Evaluate out-degree across accounts in the graph
    for node, d in G.nodes(data=True):
        if d.get("type") != "account":
            continue

        out_edges = [ed for ed in G.out_edges(node, data=True) if ed[2].get("type") == "TRANSFERRED"]
        receivers = set(ed[1] for ed in out_edges)
        out_degree = len(receivers)

        if out_degree >= 3:
            total_outflow = sum(float(ed[2].get("amount", 0.0)) for ed in out_edges)
            tx_ids = [ed[2].get("transaction_id") for ed in out_edges if ed[2].get("transaction_id")]

            severity = "CRITICAL" if (out_degree >= 5 or total_outflow >= 40000) else "HIGH"
            score = 86 if severity == "CRITICAL" else 74

            score_reasons = {
                "out_degree_count": out_degree,
                "total_outflow_volume": round(total_outflow, 2),
                "fan_out_ratio": out_degree,
                "base_risk": score,
            }

            all_entities = sorted(list(set([node] + list(receivers))))
            desc = f"Account {node} operates as an out-degree dispersal hub, distributing ${total_outflow:,.2f} to {out_degree} distinct recipient accounts."

            findings.append({
                "finding_id": f"FND-A09-{len(findings)+1:03d}",
                "pattern_id": "A09",
                "pattern_name": "Dispersal Account",
                "severity": severity,
                "risk_score": score,
                "score_reasons": score_reasons,
                "entities": all_entities,
                "transaction_ids": tx_ids,
                "evidence": [
                    f"Dispersal Hub Account: {node}",
                    f"Out-Degree Count: {out_degree} distinct recipient accounts",
                    f"Aggregate Outflow Volume: ${total_outflow:,.2f}",
                    f"Recipient Accounts: {', '.join(sorted(receivers)[:6])}",
                ],
                "alternative_explanation": "Corporate enterprise payroll execution, supplier payment run, or affiliate marketing commission disbursement.",
                "recommended_review": "Cross-reference payout recipients against audited employee payroll rolls or active vendor contracts.",
                "title": f"A09 Dispersal Account: {node}",
                "description": desc,
                "score": score,
                "detector": "A09 Dispersal Account",
                "legitimate_alternative": "Routine corporate payroll or vendor commission payment run.",
            })

    return findings
