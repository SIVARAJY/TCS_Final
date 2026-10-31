"""Modular Detector Registry for Financial Crime Investigations.
Implements the 10 core challenge detectors:
- G05: Shared beneficiary
- G06: Shared device (capped at Low/Medium)
- G07: Shared IP (capped at Low/Medium)
- T06: Rapid fund movement (simple time logic)
- T08: Circular transactions (nx.simple_cycles)
- A07: Funnel account (in-degree counts)
- A09: Dispersal account (out-degree counts)
- K03: Reused contact info (pandas groupby)
- D04: New device (set comparison)
- B02: Beneficiary concentration (one formula)
"""
from __future__ import annotations
from typing import Dict, Any, List, Tuple
import networkx as nx
import pandas as pd

from .g05_shared_beneficiary import detect_g05_shared_beneficiary
from .g06_shared_device import detect_g06_shared_device
from .g07_shared_ip import detect_g07_shared_ip
from .t06_rapid_fund_movement import detect_t06_rapid_fund_movement
from .t08_circular_transactions import detect_t08_circular_transactions
from .a07_funnel_account import detect_a07_funnel_account
from .a09_dispersal_account import detect_a09_dispersal_account
from .k03_reused_contact_info import detect_k03_reused_contact_info
from .d04_new_device import detect_d04_new_device
from .b02_beneficiary_concentration import detect_b02_beneficiary_concentration


DETECTOR_REGISTRY = [
    {
        "id": "G05",
        "name": "Shared Beneficiary",
        "description": "Detects multiple unrelated accounts/customers funneling to the exact same beneficiary.",
        "requires": ["beneficiaries"],
        "fn": detect_g05_shared_beneficiary,
    },
    {
        "id": "G06",
        "name": "Shared Device",
        "description": "Detects multi-accounting from identical hardware (capped at Low/Medium risk).",
        "requires": ["device_activity"],
        "fn": detect_g06_shared_device,
    },
    {
        "id": "G07",
        "name": "Shared IP",
        "description": "Detects concentrated network sessions from identical IP address (capped at Low/Medium).",
        "requires": ["device_activity"],
        "fn": detect_g07_shared_ip,
    },
    {
        "id": "T06",
        "name": "Rapid Fund Movement",
        "description": "Simple time logic detecting funds deposited and rapidly moved out within <= 2 hours.",
        "requires": ["transactions"],
        "fn": detect_t06_rapid_fund_movement,
    },
    {
        "id": "T08",
        "name": "Circular Transactions",
        "description": "Uses nx.simple_cycles to detect closed money loops (A -> B -> C -> A).",
        "requires": ["transactions"],
        "fn": detect_t08_circular_transactions,
    },
    {
        "id": "A07",
        "name": "Funnel Account",
        "description": "Uses in-degree counts to identify aggregation hubs receiving from 3+ distinct sources.",
        "requires": ["transactions"],
        "fn": detect_a07_funnel_account,
    },
    {
        "id": "A09",
        "name": "Dispersal Account",
        "description": "Uses out-degree counts to identify hub accounts distributing funds to 3+ destinations.",
        "requires": ["transactions"],
        "fn": detect_a09_dispersal_account,
    },
    {
        "id": "K03",
        "name": "Reused Contact Info",
        "description": "Uses pandas groupby to detect distinct customers sharing phone, email, or tax IDs.",
        "requires": ["customers"],
        "fn": detect_k03_reused_contact_info,
    },
    {
        "id": "D04",
        "name": "New Device",
        "description": "Uses set comparison to detect customer accounts logging in from unverified new hardware.",
        "requires": ["device_activity"],
        "fn": detect_d04_new_device,
    },
    {
        "id": "B02",
        "name": "Beneficiary Concentration",
        "description": "One formula: Outflow to dominant payee / total outflows >= 70% (min $5,000).",
        "requires": ["transactions"],
        "fn": detect_b02_beneficiary_concentration,
    },
]


def run_all_detectors(
    G: nx.MultiDiGraph,
    data_dict: Dict[str, pd.DataFrame],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Runs all 10 core detectors suitable for the current data, returning:
    - all_findings: List of all detected suspicious patterns
    - detector_status: Status report for each detector (EXECUTED, SKIPPED, or ERROR)
    """
    all_findings: List[Dict[str, Any]] = []
    detector_status: List[Dict[str, Any]] = []

    available_keys = set(k for k, v in data_dict.items() if v is not None and not v.empty)

    for entry in DETECTOR_REGISTRY:
        reqs = entry["requires"]
        missing_reqs = [r for r in reqs if r not in available_keys]
        can_run = len(missing_reqs) == 0

        # Special fallback: G05 can run on transactions if beneficiaries table is absent
        if entry["id"] == "G05" and not can_run and "transactions" in available_keys:
            can_run = True
            missing_reqs = []

        if can_run:
            try:
                results = entry["fn"](G, data_dict)
                all_findings.extend(results)
                detector_status.append({
                    "id": entry["id"],
                    "name": f"{entry['id']} {entry['name']}",
                    "status": "EXECUTED",
                    "findings_count": len(results),
                    "description": entry["description"],
                    "missing": [],
                })
            except Exception as e:
                detector_status.append({
                    "id": entry["id"],
                    "name": f"{entry['id']} {entry['name']}",
                    "status": "ERROR",
                    "findings_count": 0,
                    "description": str(e),
                    "missing": [],
                })
        else:
            detector_status.append({
                "id": entry["id"],
                "name": f"{entry['id']} {entry['name']}",
                "status": "SKIPPED",
                "findings_count": 0,
                "description": f"Missing required file: {', '.join(missing_reqs)}",
                "missing": missing_reqs,
            })

    # Annotate graph nodes with risk findings
    for finding in all_findings:
        for ent in finding.get("entities", []):
            if ent in G:
                G.nodes[ent]["flagged"] = True
                G.nodes[ent]["risk_score"] = max(
                    G.nodes[ent].get("risk_score", 0),
                    finding.get("risk_score", 50)
                )
                G.nodes[ent].setdefault("finding_types", []).append(
                    finding.get("pattern_id", "unknown")
                )

    return all_findings, detector_status
