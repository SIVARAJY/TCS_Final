"""Detector for Shared Infrastructure & Syndicate Clusters.
Identifies multiple distinct customers or accounts operating from the identical hardware device or IP address.
"""
from __future__ import annotations
from typing import Dict, Any, List
import networkx as nx
import pandas as pd


def detect_shared_infrastructure(G: nx.MultiDiGraph, data_dict: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
    """Detects multi-accounting and botnet clusters sharing hardware or IP footprints."""
    findings = []
    if "device_activity" not in data_dict or data_dict["device_activity"] is None or data_dict["device_activity"].empty:
        return findings

    df_dev = data_dict["device_activity"]

    # 1. Shared Device IDs across distinct customers or accounts
    if "customer_id" in df_dev.columns:
        dev_to_custs = df_dev.groupby("device_id")["customer_id"].unique()
        for dev_id, custs in dev_to_custs.items():
            clean_custs = [str(c) for c in custs if str(c) and str(c) != "nan"]
            if len(clean_custs) >= 2:
                all_ents = [f"Device:{dev_id}"] + clean_custs
                severity = "CRITICAL" if len(clean_custs) >= 3 else "HIGH"

                findings.append({
                    "detector": "Shared Device Syndicate",
                    "type": "shared_device",
                    "severity": severity,
                    "score": 92 if severity == "CRITICAL" else 78,
                    "target_entity": str(dev_id),
                    "entities": all_ents,
                    "transactions": [],
                    "title": f"Device Collusion: {dev_id}",
                    "description": f"Hardware device {dev_id} was accessed by {len(clean_custs)} distinct customers ({', '.join(clean_custs)}).",
                    "evidence": [
                        f"Device ID: {dev_id}",
                        f"Linked customers: {', '.join(clean_custs)}",
                        f"Account sharing count: {len(clean_custs)} parties",
                    ],
                    "legitimate_alternative": "Family members sharing household tablet, company kiosk device, or shared public computer.",
                })

    # 2. Shared IP Address across accounts
    if "ip_address" in df_dev.columns and "account_id" in df_dev.columns:
        ip_to_accs = df_dev.groupby("ip_address")["account_id"].unique()
        for ip, accs in ip_to_accs.items():
            clean_accs = [str(a) for a in accs if str(a) and str(a) != "nan"]
            if len(clean_accs) >= 3:
                findings.append({
                    "detector": "Concentrated IP Cluster",
                    "type": "shared_ip",
                    "severity": "MEDIUM",
                    "score": 60,
                    "target_entity": str(ip),
                    "entities": [f"IP:{ip}"] + clean_accs,
                    "transactions": [],
                    "title": f"High Density IP: {ip}",
                    "description": f"IP address {ip} handles activity for {len(clean_accs)} separate accounts.",
                    "evidence": [
                        f"IP Address: {ip}",
                        f"Accounts: {', '.join(clean_accs[:6])}",
                    ],
                    "legitimate_alternative": "Corporate VPN gateway, shared Wi-Fi at financial institution or coworking campus.",
                })

    return findings
