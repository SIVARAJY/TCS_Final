"""Detector K03: Reused Contact Info.
Uses pandas groupby on customer KYC fields (phone, email, tax_id, address) to detect synthetic identity clusters.
"""
from __future__ import annotations
from typing import Dict, Any, List
import networkx as nx
import pandas as pd


def detect_k03_reused_contact_info(
    G: nx.MultiDiGraph,
    data_dict: Dict[str, pd.DataFrame],
) -> List[Dict[str, Any]]:
    """K03 Reused Contact Info: Identifies distinct customers sharing identical KYC contact points."""
    findings = []
    if "customers" not in data_dict or data_dict["customers"] is None or data_dict["customers"].empty:
        return findings

    df_cust = data_dict["customers"]
    check_cols = ["tax_id", "phone", "email", "address"]

    for col in check_cols:
        if col not in df_cust.columns:
            continue

        for val, group in df_cust.groupby(col):
            clean_val = str(val).strip()
            if not clean_val or clean_val.lower() in ("nan", "none", "null", ""):
                continue

            cust_ids = [str(x) for x in group["customer_id"].unique() if str(x).strip()]
            if len(cust_ids) >= 2:
                names = [str(x) for x in group["name"].tolist()] if "name" in group.columns else cust_ids
                count = len(cust_ids)

                is_tax = (col == "tax_id")
                severity = "HIGH" if (is_tax or count >= 3) else "MEDIUM"
                score = 84 if is_tax else 72 if count >= 3 else 64

                score_reasons = {
                    "contact_field": col,
                    "customer_overlap_count": count,
                    "is_government_id": is_tax,
                    "synthetic_identity_signal": True,
                    "base_risk": score,
                }

                all_entities = list(cust_ids)
                desc = f"{count} distinct customers ({', '.join(cust_ids)}) share the identical {col.replace('_', ' ')}: '{clean_val}'."

                findings.append({
                    "finding_id": f"FND-K03-{len(findings)+1:03d}",
                    "pattern_id": "K03",
                    "pattern_name": "Reused Contact Info",
                    "severity": severity,
                    "risk_score": score,
                    "score_reasons": score_reasons,
                    "entities": all_entities,
                    "transaction_ids": [],
                    "evidence": [
                        f"Shared Contact Attribute: {col.upper()}",
                        f"Reused Value: {clean_val}",
                        f"Customer Records Linked: {', '.join(f'{cid} ({name})' for cid, name in zip(cust_ids, names))}",
                    ],
                    "alternative_explanation": "Spouses or family members sharing a household phone/address, corporate authorized signatories sharing office email, or data entry clerical duplicate.",
                    "recommended_review": "Contact each customer independently via verified secondary channels and demand certified identity documentation.",
                    "title": f"K03 Reused {col.replace('_', ' ').title()}: {clean_val}",
                    "description": desc,
                    "score": score,
                    "detector": "K03 Reused Contact Info",
                    "legitimate_alternative": "Family members sharing household landline, joint accounts, or clerical duplication.",
                })

    return findings
