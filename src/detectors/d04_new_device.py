"""Detector D04: New Device.
Uses set comparison on historical login telemetry to detect customer accounts logging in from an unverified new hardware device.
"""
from __future__ import annotations
from typing import Dict, Any, List
import networkx as nx
import pandas as pd


def detect_d04_new_device(
    G: nx.MultiDiGraph,
    data_dict: Dict[str, pd.DataFrame],
) -> List[Dict[str, Any]]:
    """D04 New Device: Detects accounts or customers operating from an unprecedented hardware device."""
    findings = []
    if "device_activity" not in data_dict or data_dict["device_activity"] is None or data_dict["device_activity"].empty:
        return findings

    df_dev = data_dict["device_activity"].copy()
    if "device_id" not in df_dev.columns:
        return findings

    id_col = "customer_id" if "customer_id" in df_dev.columns else "account_id" if "account_id" in df_dev.columns else None
    if not id_col:
        return findings

    # Sort chronologically if timestamp exists
    has_time = "timestamp" in df_dev.columns
    if has_time:
        try:
            df_dev["dt"] = pd.to_datetime(df_dev["timestamp"], errors="coerce")
            df_dev = df_dev.sort_values("dt")
        except Exception:
            has_time = False

    for user_id, group in df_dev.groupby(id_col):
        clean_user = str(user_id).strip()
        if not clean_user or clean_user == "nan":
            continue

        device_list = [str(d) for d in group["device_id"].tolist() if str(d).strip() and str(d) != "nan"]
        unique_devices = list(dict.fromkeys(device_list))  # preserve order

        if len(unique_devices) >= 2:
            # Baseline is previous device(s), newest is the latest device
            baseline_devices = unique_devices[:-1]
            newest_device = unique_devices[-1]
            
            # Timestamp or location of new device
            latest_row = group[group["device_id"].astype(str) == newest_device].iloc[-1]
            loc = str(latest_row.get("location", "Unknown Location"))
            ts = str(latest_row.get("timestamp", "Recent"))

            score = 62
            severity = "MEDIUM"

            score_reasons = {
                "unrecognized_hardware_signature": True,
                "baseline_devices_count": len(baseline_devices),
                "device_fingerprint": newest_device,
                "base_risk": score,
            }

            all_entities = [clean_user, newest_device] + baseline_devices
            desc = f"{id_col.replace('_', ' ').title()} {clean_user} initiated access from an unrecognized hardware device {newest_device} at {ts}."

            findings.append({
                "finding_id": f"FND-D04-{len(findings)+1:03d}",
                "pattern_id": "D04",
                "pattern_name": "New Device",
                "severity": severity,
                "risk_score": score,
                "score_reasons": score_reasons,
                "entities": all_entities,
                "transaction_ids": [],
                "evidence": [
                    f"Customer / Account: {clean_user}",
                    f"New Device Fingerprint: {newest_device}",
                    f"Established Baseline Devices: {', '.join(baseline_devices)}",
                    f"Session Geolocation: {loc} ({ts})",
                ],
                "alternative_explanation": "Customer purchased a new mobile phone, replaced workstation, or updated operating system causing canvas fingerprint hash change.",
                "recommended_review": "Prompt account holder with step-up out-of-band two-factor authentication (2FA) and verify email device authorization.",
                "title": f"D04 New Device: {clean_user} on {newest_device}",
                "description": desc,
                "score": score,
                "detector": "D04 New Device",
                "legitimate_alternative": "Hardware upgrade, replacement smartphone, or browser canvas hash change.",
            })

    return findings
