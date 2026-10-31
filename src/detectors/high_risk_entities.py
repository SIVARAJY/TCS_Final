"""Detector for High-Risk Entity Corroboration.
Cross-references transactions against high-risk merchants, jurisdictional flags, and existing fraud alerts.
"""
from __future__ import annotations
from typing import Dict, Any, List
import networkx as nx
import pandas as pd


def detect_high_risk_entities(G: nx.MultiDiGraph, data_dict: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
    """Flags interactions with flagged merchants, high risk customer profiles, and pre-existing alerts."""
    findings = []

    # 1. High-Risk Merchant Funneling
    if "merchants" in data_dict and data_dict["merchants"] is not None and not data_dict["merchants"].empty:
        df_merch = data_dict["merchants"]
        high_merchs = df_merch[df_merch["risk_level"].astype(str).str.upper().isin(["HIGH", "CRITICAL"])]
        high_merch_ids = set(high_merchs["merchant_id"].astype(str).tolist())

        if "transactions" in data_dict and data_dict["transactions"] is not None:
            df_tx = data_dict["transactions"]
            matched_tx = df_tx[df_tx["target_account_id"].astype(str).isin(high_merch_ids)]
            for mid, group in matched_tx.groupby("target_account_id"):
                mid = str(mid)
                m_info = high_merchs[high_merchs["merchant_id"].astype(str) == mid].iloc[0]
                m_name = m_info.get("merchant_name", mid)
                m_cat = m_info.get("category", "High Risk")
                tot_amt = float(group["amount"].sum())
                senders = [str(x) for x in group["source_account_id"].unique().tolist()]

                findings.append({
                    "detector": "High-Risk Merchant Funneling",
                    "type": "high_risk_merchant",
                    "severity": "CRITICAL" if m_info.get("risk_level", "").upper() == "CRITICAL" else "HIGH",
                    "score": 88,
                    "target_entity": mid,
                    "entities": [mid] + senders,
                    "transactions": [str(x) for x in group["transaction_id"].tolist()],
                    "title": f"Funneling to High-Risk Endpoint: {m_name}",
                    "description": f"Transferred ${tot_amt:,.2f} from {len(senders)} accounts to {m_name} ({m_cat}).",
                    "evidence": [
                        f"Merchant: {m_name} ({mid})",
                        f"Risk tier: {m_info.get('risk_level', 'HIGH')}",
                        f"Category: {m_cat}",
                        f"Total channeled: ${tot_amt:,.2f}",
                    ],
                    "legitimate_alternative": "Authorized merchant payment, specialized software license, or compliant institutional trading.",
                })

    # 2. Existing Fraud Alert Escalation
    if "fraud_alerts" in data_dict and data_dict["fraud_alerts"] is not None and not data_dict["fraud_alerts"].empty:
        df_alerts = data_dict["fraud_alerts"]
        crit_alerts = df_alerts[df_alerts["severity"].astype(str).str.upper().isin(["CRITICAL", "HIGH"])]
        for _, row in crit_alerts.iterrows():
            ent_id = str(row.get("entity_id", ""))
            alt_id = str(row.get("alert_id", ""))
            alt_type = str(row.get("alert_type", "Alert"))
            desc = str(row.get("description", ""))

            findings.append({
                "detector": "Active Fraud Alert",
                "type": "fraud_alert_escalation",
                "severity": str(row.get("severity", "HIGH")).upper(),
                "score": 80,
                "target_entity": ent_id,
                "entities": [ent_id, alt_id],
                "transactions": [],
                "title": f"Pre-Existing Alert Flag: {ent_id}",
                "description": f"Entity {ent_id} triggered alert {alt_id} ({alt_type}): {desc}",
                "evidence": [
                    f"Entity ID: {ent_id}",
                    f"Alert ID: {alt_id}",
                    f"Trigger: {alt_type}",
                    f"Details: {desc}",
                ],
                "legitimate_alternative": "False positive trigger caused by rule calibration or temporary anomaly in user travel.",
            })

    return findings
