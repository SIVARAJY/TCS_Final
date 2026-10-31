"""Detector for Circular Money Laundering Flows.
Identifies closed directed transaction loops (A -> B -> C -> A) designed to obscure fund origins.
"""
from __future__ import annotations
from typing import Dict, Any, List
import networkx as nx
import pandas as pd


def detect_cycles(G: nx.MultiDiGraph, data_dict: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
    """Detects closed directed transaction cycles."""
    findings = []
    if "transactions" not in data_dict or data_dict["transactions"] is None or data_dict["transactions"].empty:
        return findings

    # Build a simple DiGraph of transaction transfers to find elementary cycles
    trans_graph = nx.DiGraph()
    edge_details: Dict[tuple, List[Dict[str, Any]]] = {}

    for u, v, d in G.edges(data=True):
        if d.get("type") == "TRANSFERRED":
            trans_graph.add_edge(u, v)
            edge_details.setdefault((u, v), []).append(d)

    try:
        cycles = list(nx.simple_cycles(trans_graph))
    except Exception:
        cycles = []

    # Filter meaningful cycles (length 3 to 6)
    seen_cycles = set()
    for cycle in cycles:
        if len(cycle) < 3 or len(cycle) > 7:
            continue

        cycle_key = tuple(sorted(cycle))
        if cycle_key in seen_cycles:
            continue
        seen_cycles.add(cycle_key)

        cycle_txns = []
        cycle_volumes = []
        for i in range(len(cycle)):
            u = cycle[i]
            v = cycle[(i + 1) % len(cycle)]
            tx_list = edge_details.get((u, v), [])
            for t in tx_list:
                if t.get("transaction_id"):
                    cycle_txns.append(t["transaction_id"])
                cycle_volumes.append(t.get("amount", 0.0))

        total_loop_vol = sum(cycle_volumes)
        findings.append({
            "detector": "Circular Flow",
            "type": "cycle",
            "severity": "CRITICAL",
            "score": 95,
            "target_entity": cycle[0],
            "entities": cycle,
            "transactions": cycle_txns,
            "title": f"Closed Money Cycle: {' → '.join(cycle)} → {cycle[0]}",
            "description": f"Detected a circular transaction path of length {len(cycle)} circulating ~${total_loop_vol:,.2f}.",
            "evidence": [
                f"Loop path: {' → '.join(cycle)} → {cycle[0]}",
                f"Involved entities: {len(cycle)} accounts",
                f"Total looped volume: ${total_loop_vol:,.2f}",
            ],
            "legitimate_alternative": "Intercompany corporate treasury netting, automated liquidity rebalancing, or intra-group loan settlement.",
        })

    return findings
