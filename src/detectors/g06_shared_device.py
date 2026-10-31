"""Detector G06: Shared Device.
Identifies multiple distinct customers or accounts operating from the same physical hardware fingerprint.
Rule constraint: Shared IP/device alone must score Low/Medium, never Critical.
"""
from __future__ import annotations
from typing import Dict, Any, List
import networkx as nx
import pandas as pd


def detect_g06_shared_device(
    G: nx.MultiDiGraph,
    data_dict: Dict[str, pd.DataFrame],
) -> List[Dict[str, Any]]:
    """G06 Shared Device: Distinct customers accessing through identical device fingerprint.
    Strictly capped at Low/Medium risk severity.
    """
    findings = []
    if "device_activity" not in data_dict or data_dict["device_activity"] is None or data_dict["device_activity"].empty:
        return findings

    df_dev = data_dict["device_activity"]
    if "device_id" not in df_dev.columns:
        return findings

    # Evaluate by customer_id or account_id
    id_col = "customer_id" if "customer_id" in df_dev.columns else "account_id" if "account_id" in df_dev.columns else None
    if not id_col:
        return findings

    for dev_id, group in df_dev.groupby("device_id"):
        distinct_parties = [str(x) for x in group[id_col].unique() if str(x).strip() and str(x) != "nan"]
        if len(distinct_parties) >= 2:
            dev_str = str(dev_id)
            count = len(distinct_parties)
            
            # RULE: Must score Low/Medium, never Critical!
            severity = "MEDIUM" if count >= 3 else "LOW"
            score = 48 if count >= 3 else 32

            score_reasons = {
                "shared_parties_count": count,
                "entity_type": id_col,
                "rule_policy": "Strictly capped at Low/Medium (Shared device alone is never Critical)",
                "calculated_score": score,
            }

            all_entities = [dev_str] + distinct_parties
            desc = f"Hardware device {dev_str} was utilized by {count} distinct {id_col}s ({', '.join(distinct_parties)})."

            findings.append({
                "finding_id": f"FND-G06-{len(findings)+1:03d}",
                "pattern_id": "G06",
                "pattern_name": "Shared Device",
                "severity": severity,
                "risk_score": score,
                "score_reasons": score_reasons,
                "entities": all_entities,
                "transaction_ids": [],
                "evidence": [
                    f"Device Fingerprint: {dev_str}",
                    f"Number of distinct {id_col}s: {count}",
                    f"Observed Parties: {', '.join(distinct_parties)}",
                ],
                "alternative_explanation": "Shared family tablet, household PC, corporate branch kiosk, or university library workstation.",
                "recommended_review": "Verify residential address congruence between parties and trigger step-up biometric/SMS MFA.",
                "title": f"G06 Shared Device: {dev_str}",
                "description": desc,
                "score": score,
                "detector": "G06 Shared Device",
                "legitimate_alternative": "Shared family tablet, household computer, or company shared workstation.",
            })

    return findings
