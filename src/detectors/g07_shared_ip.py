"""Detector G07: Shared IP.
Identifies multiple distinct accounts or customers operating from the same network IP address.
Rule constraint: Shared IP/device alone must score Low/Medium, never Critical.
"""
from __future__ import annotations
from typing import Dict, Any, List
import networkx as nx
import pandas as pd


def detect_g07_shared_ip(
    G: nx.MultiDiGraph,
    data_dict: Dict[str, pd.DataFrame],
) -> List[Dict[str, Any]]:
    """G07 Shared IP: Multiple accounts originating sessions from the exact same IP.
    Strictly capped at Low/Medium risk severity.
    """
    findings = []
    if "device_activity" not in data_dict or data_dict["device_activity"] is None or data_dict["device_activity"].empty:
        return findings

    df_dev = data_dict["device_activity"]
    if "ip_address" not in df_dev.columns:
        return findings

    id_col = "account_id" if "account_id" in df_dev.columns else "customer_id" if "customer_id" in df_dev.columns else None
    if not id_col:
        return findings

    for ip_val, group in df_dev.groupby("ip_address"):
        clean_ip = str(ip_val).strip()
        if not clean_ip or clean_ip == "nan":
            continue

        parties = [str(x) for x in group[id_col].unique() if str(x).strip() and str(x) != "nan"]
        if len(parties) >= 2:
            count = len(parties)
            loc = str(group["location"].iloc[0]) if "location" in group.columns else "Unknown"

            # RULE: Must score Low/Medium, never Critical!
            severity = "MEDIUM" if count >= 3 else "LOW"
            score = 42 if count >= 3 else 28

            score_reasons = {
                "distinct_parties_on_ip": count,
                "ip_address": clean_ip,
                "rule_policy": "Strictly capped at Low/Medium (Shared IP alone is frequent on NAT/VPN/DHCP)",
                "calculated_score": score,
            }

            all_entities = [f"IP:{clean_ip}"] + parties
            desc = f"Network IP {clean_ip} ({loc}) handled activity for {count} distinct {id_col}s ({', '.join(parties)})."

            findings.append({
                "finding_id": f"FND-G07-{len(findings)+1:03d}",
                "pattern_id": "G07",
                "pattern_name": "Shared IP",
                "severity": severity,
                "risk_score": score,
                "score_reasons": score_reasons,
                "entities": all_entities,
                "transaction_ids": [],
                "evidence": [
                    f"Network IP Address: {clean_ip}",
                    f"Reported Geolocation: {loc}",
                    f"Active Parties: {', '.join(parties)}",
                ],
                "alternative_explanation": "Corporate VPN exit gateway, hotel public Wi-Fi, university campus NAT, or mobile cellular proxy.",
                "recommended_review": "Inspect ASN carrier type (hosting facility vs residential telecom) and examine session concurrency.",
                "title": f"G07 Shared IP: {clean_ip}",
                "description": desc,
                "score": score,
                "detector": "G07 Shared IP",
                "legitimate_alternative": "Commercial VPN, corporate proxy, hotel Wi-Fi, or university network.",
            })

    return findings
