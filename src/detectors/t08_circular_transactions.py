"""Detector T08: Circular Transactions.
Uses nx.simple_cycles to identify closed directed loops (A -> B -> C -> A) designed to obscure origin of funds.
"""
from __future__ import annotations
from typing import Dict, Any, List
import networkx as nx
import pandas as pd


def detect_t08_circular_transactions(
    G: nx.MultiDiGraph,
    data_dict: Dict[str, pd.DataFrame],
) -> List[Dict[str, Any]]:
    """T08 Circular Transactions: Uses nx.simple_cycles to uncover closed money round-trips."""
    findings = []
    if "transactions" not in data_dict or data_dict["transactions"] is None or data_dict["transactions"].empty:
        return findings

    # Construct directed transaction graph
    trans_graph = nx.DiGraph()
    edge_map: Dict[tuple, List[Dict[str, Any]]] = {}

    for u, v, d in G.edges(data=True):
        if d.get("type") == "TRANSFERRED":
            trans_graph.add_edge(u, v)
            edge_map.setdefault((u, v), []).append(d)

    if trans_graph.number_of_nodes() < 3 or trans_graph.number_of_edges() < 3:
        return findings

    # Fast k-core cycle pruning: remove nodes that cannot be part of a cycle (in_degree == 0 or out_degree == 0)
    pruned = True
    while pruned:
        pruned = False
        dead_nodes = [n for n in trans_graph.nodes() if trans_graph.in_degree(n) == 0 or trans_graph.out_degree(n) == 0]
        if dead_nodes:
            trans_graph.remove_nodes_from(dead_nodes)
            pruned = True

    if trans_graph.number_of_nodes() < 3:
        return findings

    # Find elementary cycles of length 3 to 7 with a safe iteration cap
    cycles = []
    try:
        # NetworkX 3.0+ length_bound prevents combinatorial explosion
        cycle_iter = nx.simple_cycles(trans_graph, length_bound=7)
        for c in cycle_iter:
            if 3 <= len(c) <= 7:
                cycles.append(c)
                if len(cycles) >= 50:  # Cap at top 50 cycles for speed
                    break
    except TypeError:
        # Fallback for NetworkX versions without length_bound
        for c in nx.simple_cycles(trans_graph):
            if 3 <= len(c) <= 7:
                cycles.append(c)
                if len(cycles) >= 50:
                    break
            elif len(c) > 7:
                continue
    except Exception:
        cycles = []

    seen_cycles = set()
    for cycle in cycles:
        if len(cycle) < 3 or len(cycle) > 7:
            continue

        cycle_key = tuple(sorted(cycle))
        if cycle_key in seen_cycles:
            continue
        seen_cycles.add(cycle_key)

        cycle_tx_ids = []
        cycle_volumes = []
        cycle_hops = []

        for i in range(len(cycle)):
            src = cycle[i]
            tgt = cycle[(i + 1) % len(cycle)]
            tx_records = edge_map.get((src, tgt), [])
            for tx in tx_records:
                tid = tx.get("transaction_id")
                amt = float(tx.get("amount", 0.0))
                if tid:
                    cycle_tx_ids.append(tid)
                cycle_volumes.append(amt)
                cycle_hops.append(f"{src} → {tgt} (${amt:,.2f})")

        total_cycled = sum(cycle_volumes)
        score = 96
        score_reasons = {
            "cycle_node_count": len(cycle),
            "closed_money_ring": True,
            "cycled_volume_total": round(total_cycled, 2),
            "topological_pattern": "Elementary directed cycle",
            "base_risk": score,
        }

        path_repr = " → ".join(cycle) + f" → {cycle[0]}"
        desc = f"Closed transaction loop detected across {len(cycle)} accounts ({path_repr}) circulating ${total_cycled:,.2f}."

        findings.append({
            "finding_id": f"FND-T08-{len(findings)+1:03d}",
            "pattern_id": "T08",
            "pattern_name": "Circular Transactions",
            "severity": "CRITICAL",
            "risk_score": score,
            "score_reasons": score_reasons,
            "entities": list(cycle),
            "transaction_ids": cycle_tx_ids,
            "evidence": [
                f"Loop Trajectory: {path_repr}",
                f"Ring Participants: {len(cycle)} distinct accounts",
                f"Total Cycled Capital: ${total_cycled:,.2f}",
                f"Leg Breakdown: {'; '.join(cycle_hops[:4])}",
            ],
            "alternative_explanation": "Corporate treasury cash pooling, intra-group net debt settlement, automated multi-subsidiary liquidity sweep, or reciprocal merchant credit arrangements.",
            "recommended_review": "Subpoena full account ledgers for all cycle participants and verify underlying commercial contracts for round-trip transactions.",
            "title": f"T08 Circular Transactions: {cycle[0]} Ring",
            "description": desc,
            "score": score,
            "detector": "T08 Circular Transactions",
            "legitimate_alternative": "Corporate treasury netting or reciprocal intercompany debt settlement.",
        })

    return findings
