"""Detector A07: Funnel Account (In-Degree Concentration).
Uses in-degree counts to identify aggregation accounts receiving funds from multiple disparate sources.
"""
from __future__ import annotations
from typing import Dict, Any, List
import networkx as nx
import pandas as pd


def detect_a07_funnel_account(
    G: nx.MultiDiGraph,
    data_dict: Dict[str, pd.DataFrame],
) -> List[Dict[str, Any]]:
    """A07 Funnel Account: Identifies high in-degree concentration accounts acting as collection funnels."""
    findings = []
    if "transactions" not in data_dict or data_dict["transactions"] is None or data_dict["transactions"].empty:
        return findings

    # Evaluate in-degree across accounts in the graph
    for node, d in G.nodes(data=True):
        if d.get("type") != "account":
            continue

        in_edges = [ed for ed in G.in_edges(node, data=True) if ed[2].get("type") == "TRANSFERRED"]
        senders = set(ed[0] for ed in in_edges)
        in_degree = len(senders)

        if in_degree >= 3:
            total_inflow = sum(float(ed[2].get("amount", 0.0)) for ed in in_edges)
            tx_ids = [ed[2].get("transaction_id") for ed in in_edges if ed[2].get("transaction_id")]

            severity = "CRITICAL" if (in_degree >= 5 or total_inflow >= 40000) else "HIGH"
            score = 88 if severity == "CRITICAL" else 75

            score_reasons = {
                "in_degree_count": in_degree,
                "total_inflow_volume": round(total_inflow, 2),
                "fan_in_ratio": in_degree,
                "base_risk": score,
            }

            all_entities = sorted(list(set([node] + list(senders))))
            desc = f"Account {node} operates as an in-degree funnel, aggregating ${total_inflow:,.2f} from {in_degree} distinct source accounts."

            findings.append({
                "finding_id": f"FND-A07-{len(findings)+1:03d}",
                "pattern_id": "A07",
                "pattern_name": "Funnel Account",
                "severity": severity,
                "risk_score": score,
                "score_reasons": score_reasons,
                "entities": all_entities,
                "transaction_ids": tx_ids,
                "evidence": [
                    f"Funnel Hub Account: {node}",
                    f"In-Degree Count: {in_degree} distinct counterparties",
                    f"Aggregate Inflow Volume: ${total_inflow:,.2f}",
                    f"Source Accounts: {', '.join(sorted(senders)[:6])}",
                ],
                "alternative_explanation": "Point-of-sale retail merchant aggregator, non-profit charitable contribution account, or event ticketing manager.",
                "recommended_review": "Examine merchant acquiring agreement, business profile documentation, and beneficial ownership.",
                "title": f"A07 Funnel Account: {node}",
                "description": desc,
                "score": score,
                "detector": "A07 Funnel Account",
                "legitimate_alternative": "Commercial e-commerce aggregator, charity drive, or school tuition desk.",
            })

    return findings
