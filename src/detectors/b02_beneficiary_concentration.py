"""Detector B02: Beneficiary Concentration.
Uses single formula (Dominant Beneficiary Outflow / Total Outflow >= 0.70) to identify extreme payee concentration.
"""
from __future__ import annotations
from typing import Dict, Any, List
import networkx as nx
import pandas as pd


def detect_b02_beneficiary_concentration(
    G: nx.MultiDiGraph,
    data_dict: Dict[str, pd.DataFrame],
) -> List[Dict[str, Any]]:
    """B02 Beneficiary Concentration: One formula evaluating disproportionate capital concentration
    into a single beneficiary endpoint (>= 70% of total account outflows, min $5,000).
    """
    findings = []
    if "transactions" not in data_dict or data_dict["transactions"] is None or data_dict["transactions"].empty:
        return findings

    df_tx = data_dict["transactions"]
    min_volume_threshold = 5000.0
    concentration_threshold = 0.70

    # Group outflows by source_account_id
    for src_acc, group in df_tx.groupby("source_account_id"):
        src_str = str(src_acc).strip()
        total_outflow = float(group["amount"].sum())

        if total_outflow < min_volume_threshold or len(group) < 1:
            continue

        # Outflow per target endpoint
        target_breakdown = group.groupby("target_account_id")["amount"].sum()
        top_target = str(target_breakdown.idxmax())
        top_amount = float(target_breakdown.max())

        ratio = top_amount / total_outflow if total_outflow > 0 else 0.0

        if ratio >= concentration_threshold:
            tx_ids = [str(x) for x in group[group["target_account_id"].astype(str) == top_target]["transaction_id"].tolist()]
            
            severity = "HIGH" if (ratio >= 0.90 or top_amount >= 20000) else "MEDIUM"
            score = 82 if severity == "HIGH" else 68

            score_reasons = {
                "concentration_formula_ratio": round(ratio, 4),
                "concentration_percentage": round(ratio * 100, 1),
                "dominant_payee_outflow": round(top_amount, 2),
                "total_account_outflow": round(total_outflow, 2),
                "formula_threshold": concentration_threshold,
                "base_risk": score,
            }

            all_entities = sorted(list(set([src_str, top_target])))
            desc = f"Account {src_str} concentrated {ratio*100:.1f}% (${top_amount:,.2f} of ${total_outflow:,.2f}) of its total outflows into a single payee: {top_target}."

            findings.append({
                "finding_id": f"FND-B02-{len(findings)+1:03d}",
                "pattern_id": "B02",
                "pattern_name": "Beneficiary Concentration",
                "severity": severity,
                "risk_score": score,
                "score_reasons": score_reasons,
                "entities": all_entities,
                "transaction_ids": tx_ids,
                "evidence": [
                    f"Originating Account: {src_str}",
                    f"Concentration Formula: ${top_amount:,.2f} / ${total_outflow:,.2f} = {ratio*100:.1f}%",
                    f"Dominant Destination Payee: {top_target}",
                    f"Associated Transactions: {len(tx_ids)} transfers",
                ],
                "alternative_explanation": "Exclusive supplier contract, high-value mortgage principal repayment, real estate acquisition escrow, or structured tax settlement.",
                "recommended_review": "Validate invoices from dominant beneficiary and confirm commercial necessity for single-vendor outflow concentration.",
                "title": f"B02 Beneficiary Concentration: {src_str} → {top_target}",
                "description": desc,
                "score": score,
                "detector": "B02 Beneficiary Concentration",
                "legitimate_alternative": "Exclusive supplier contract or mortgage principal settlement.",
            })

    return findings
