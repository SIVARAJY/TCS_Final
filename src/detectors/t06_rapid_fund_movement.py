"""Detector T06: Rapid Fund Movement.
Flags pass-through conduits where funds are deposited and immediately forwarded in a short time window.
"""
from __future__ import annotations
from typing import Dict, Any, List
import networkx as nx
import pandas as pd


def detect_t06_rapid_fund_movement(
    G: nx.MultiDiGraph,
    data_dict: Dict[str, pd.DataFrame],
) -> List[Dict[str, Any]]:
    """T06 Rapid Fund Movement: Uses simple time logic to detect accounts receiving funds
    and rapidly moving them out (latency <= 120 minutes with high turnover ratio).
    """
    findings = []
    if "transactions" not in data_dict or data_dict["transactions"] is None or data_dict["transactions"].empty:
        return findings

    df_tx = data_dict["transactions"].copy()
    if "timestamp" not in df_tx.columns:
        return findings

    try:
        df_tx["dt"] = pd.to_datetime(df_tx["timestamp"], errors="coerce")
    except Exception:
        return findings

    df_valid = df_tx.dropna(subset=["dt"]).sort_values("dt")
    if df_valid.empty:
        return findings

    # Fast dictionary grouping using itertuples (orders of magnitude faster than repeated DataFrame slicing)
    inflows_by_acc: Dict[str, list] = {}
    outflows_by_acc: Dict[str, list] = {}

    for row in df_valid.itertuples(index=False):
        src = str(getattr(row, "source_account_id", "")).strip()
        tgt = str(getattr(row, "target_account_id", "")).strip()
        amt = float(getattr(row, "amount", 0.0) or 0.0)
        dt = getattr(row, "dt")
        tid = str(getattr(row, "transaction_id", ""))
        ts_str = str(getattr(row, "timestamp", ""))

        if tgt:
            inflows_by_acc.setdefault(tgt, []).append((dt, amt, tid, src, ts_str))
        if src:
            outflows_by_acc.setdefault(src, []).append((dt, amt, tid, tgt, ts_str))

    # Look for accounts with both incoming and outgoing transfers within 2 hours (7200s)
    all_accounts = set(inflows_by_acc.keys()).intersection(set(outflows_by_acc.keys()))

    for acc in all_accounts:
        in_list = sorted(inflows_by_acc[acc], key=lambda x: x[0])
        out_list = sorted(outflows_by_acc[acc], key=lambda x: x[0])

        for in_time, in_amt, in_id, src_sender, in_ts in in_list:
            if in_amt < 1000:
                continue

            for out_time, out_amt, out_id, dest_receiver, out_ts in out_list:
                diff_sec = (out_time - in_time).total_seconds()
                if diff_sec < 0:
                    continue
                if diff_sec > 7200:
                    break

                turnover = out_amt / in_amt if in_amt > 0 else 0
                if 0.65 <= turnover <= 1.35:
                    delta_min = diff_sec / 60.0
                    severity = "CRITICAL" if out_amt >= 15000 or delta_min <= 45 else "HIGH"
                    score = 92 if severity == "CRITICAL" else 82

                    score_reasons = {
                        "transit_time_minutes": round(delta_min, 1),
                        "turnover_ratio_pct": round(turnover * 100, 1),
                        "transferred_volume": out_amt,
                        "rapid_depletion": True,
                        "base_risk": score,
                    }

                    all_entities = sorted(list(set([acc, src_sender, dest_receiver])))
                    desc = f"Account {acc} received ${in_amt:,.2f} from {src_sender} and forwarded ${out_amt:,.2f} to {dest_receiver} within {delta_min:.1f} minutes ({turnover*100:.1f}% turnover)."

                    findings.append({
                        "finding_id": f"FND-T06-{len(findings)+1:03d}",
                        "pattern_id": "T06",
                        "pattern_name": "Rapid Fund Movement",
                        "severity": severity,
                        "risk_score": score,
                        "score_reasons": score_reasons,
                        "entities": all_entities,
                        "transaction_ids": [in_id, out_id],
                        "evidence": [
                            f"Conduit Account: {acc}",
                            f"Inflow: ${in_amt:,.2f} from {src_sender} ({in_id}) at {in_ts}",
                            f"Outflow: ${out_amt:,.2f} to {dest_receiver} ({out_id}) at {out_ts}",
                            f"Turnover latency: {delta_min:.1f} minutes ({turnover*100:.1f}% of inflow)",
                        ],
                        "alternative_explanation": "Automated payroll dispersal, commercial escrow clearance, automated forex conversion, or securities purchase settlement.",
                        "recommended_review": "Place temporary outbound hold on conduit account; verify invoice contracts connecting sender and receiver.",
                        "title": f"T06 Rapid Fund Movement: {acc}",
                        "description": desc,
                        "score": score,
                        "detector": "T06 Rapid Fund Movement",
                        "legitimate_alternative": "Commercial escrow, payroll dispersal, or automated securities settlement.",
                    })
                    break  # Matched once for this inflow

    return findings
