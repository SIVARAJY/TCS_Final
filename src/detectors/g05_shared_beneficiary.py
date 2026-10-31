"""Detector G05: Shared Beneficiary.
Identifies multiple distinct accounts or customers sharing the exact same external beneficiary/payee.
"""
from __future__ import annotations
from typing import Dict, Any, List
import networkx as nx
import pandas as pd


def detect_g05_shared_beneficiary(
    G: nx.MultiDiGraph,
    data_dict: Dict[str, pd.DataFrame],
) -> List[Dict[str, Any]]:
    """G05 Shared Beneficiary: Multiple accounts/customers linked to the identical beneficiary."""
    findings = []
    
    # 1. From beneficiaries CSV if present
    if "beneficiaries" in data_dict and data_dict["beneficiaries"] is not None and not data_dict["beneficiaries"].empty:
        df_bene = data_dict["beneficiaries"]
        col_acc = "account_id" if "account_id" in df_bene.columns else None
        col_bene = "beneficiary_account" if "beneficiary_account" in df_bene.columns else None

        if col_acc and col_bene:
            for bene_val, group in df_bene.groupby(col_bene):
                src_accs = [str(a) for a in group[col_acc].unique() if str(a).strip()]
                if len(src_accs) >= 2:
                    bene_str = str(bene_val)
                    bene_name = str(group["name"].iloc[0]) if "name" in group.columns else bene_str
                    
                    # Discover customer owners if available
                    owners = set()
                    for acc in src_accs:
                        if acc in G and "customer_id" in G.nodes[acc]:
                            owners.add(G.nodes[acc]["customer_id"])

                    # Collect any transactions from these accounts to this beneficiary
                    tx_ids = []
                    for acc in src_accs:
                        if G.has_edge(acc, bene_str):
                            for _, _, d in G.edges(acc, data=True):
                                if d.get("target") == bene_str or d.get("transaction_id"):
                                    tx_ids.append(d.get("transaction_id", ""))

                    count = len(src_accs)
                    severity = "HIGH" if count >= 3 or len(owners) >= 2 else "MEDIUM"
                    score = 78 if severity == "HIGH" else 62

                    score_reasons = {
                        "shared_source_accounts": count,
                        "distinct_customer_owners": len(owners),
                        "cross_account_overlap": True,
                        "base_risk": score,
                    }

                    all_entities = sorted(list(set([bene_str] + src_accs + list(owners))))
                    desc = f"Beneficiary {bene_name} ({bene_str}) is shared by {count} distinct accounts ({', '.join(src_accs)})."

                    findings.append({
                        "finding_id": f"FND-G05-{len(findings)+1:03d}",
                        "pattern_id": "G05",
                        "pattern_name": "Shared Beneficiary",
                        "severity": severity,
                        "risk_score": score,
                        "score_reasons": score_reasons,
                        "entities": all_entities,
                        "transaction_ids": [t for t in tx_ids if t],
                        "evidence": [
                            f"Beneficiary Account: {bene_str} ({bene_name})",
                            f"Associated Source Accounts: {', '.join(src_accs)}",
                            f"Owner Customers Identified: {', '.join(owners) if owners else 'Unresolved'}",
                        ],
                        "alternative_explanation": "Common utility billing service, university bursar, commercial landlord, or municipal tax authority.",
                        "recommended_review": "Verify corporate payee registration and cross-check relationship declarations between source account holders.",
                        "title": f"G05 Shared Beneficiary: {bene_name}",
                        "description": desc,
                        "score": score,
                        "detector": "G05 Shared Beneficiary",
                        "legitimate_alternative": "Common utility billing service, landlord, or tuition clearinghouse.",
                    })

    # 2. Corroborate via graph edges if beneficiaries table was missing but transactions exist
    elif "transactions" in data_dict and data_dict["transactions"] is not None and not data_dict["transactions"].empty:
        df_tx = data_dict["transactions"]
        for tgt, group in df_tx.groupby("target_account_id"):
            srcs = [str(s) for s in group["source_account_id"].unique() if str(s).strip()]
            if len(srcs) >= 3 and float(group["amount"].sum()) >= 10000:
                tgt_str = str(tgt)
                score = 72
                findings.append({
                    "finding_id": f"FND-G05-{len(findings)+1:03d}",
                    "pattern_id": "G05",
                    "pattern_name": "Shared Beneficiary",
                    "severity": "HIGH",
                    "risk_score": score,
                    "score_reasons": {
                        "shared_target_accounts": len(srcs),
                        "aggregate_transfer_volume": float(group["amount"].sum()),
                    },
                    "entities": [tgt_str] + srcs,
                    "transaction_ids": [str(x) for x in group["transaction_id"].tolist()],
                    "evidence": [
                        f"Common Target Entity: {tgt_str}",
                        f"Source Accounts Funneling: {', '.join(srcs)}",
                        f"Cumulative Transferred: ${group['amount'].sum():,.2f}",
                    ],
                    "alternative_explanation": "Centralized corporate vendor payment or e-commerce merchant processor.",
                    "recommended_review": "Request vendor invoices and examine beneficial ownership of target account.",
                    "title": f"G05 Shared Beneficiary: {tgt_str}",
                    "description": f"Target entity {tgt_str} received funds from {len(srcs)} separate accounts.",
                    "score": score,
                    "detector": "G05 Shared Beneficiary",
                    "legitimate_alternative": "Centralized corporate vendor payment.",
                })

    return findings
