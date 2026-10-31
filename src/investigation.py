"""AI Investigation module for case synthesis, hypothesis testing, and cited report generation.
Groups multi-entity findings into actionable cases and generates AI case reports via Gemini API or template fallback.
"""
from __future__ import annotations
import json
import os
import re
from typing import Dict, Any, List, Optional
import networkx as nx
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are a senior financial crime intelligence investigator for a tier-1 financial intelligence unit (FIU).
You receive a structured JSON evidence package built by deterministic graph detectors and anomaly models.
Your task:
1. Conduct pattern analysis across transactions (who paid whom, velocity, amounts, intermediary hops).
2. Form 2-3 competing hypotheses (at least one legitimate/benign commercial explanation, e.g. corporate treasury, merchant escrow, family sharing).
3. For each hypothesis, cite specific supporting and contradicting record IDs (e.g. ACC-101, DEV-7, CUS-3, TXN-004) that exist strictly in the package. Never invent facts.
4. Write a 2-3 paragraph investigative narrative detailing the suspicious indicators, alternative explanations, and what evidence is needed to prove or disprove.
5. Provide actionable next steps for compliance officers (e.g. enhanced KYC, SAR filing, transaction monitoring hold, beneficiary confirmation).

Return ONLY valid JSON (no markdown formatting fences):
{
  "summary": "Concise executive overview citing case ID and risk score",
  "verdict": "likely_fraud_ring" | "suspicious" | "likely_benign",
  "pattern_analysis": "Detailed structural analysis of money movement and entity overlap",
  "narrative": "Multi-paragraph investigative brief",
  "risk_rationale": "Clear breakdown of why this score was assigned",
  "hypotheses": [
    {
      "title": "Hypothesis name",
      "confidence": 0.85,
      "supporting": ["ID1", "ID2"],
      "against": ["ID3"],
      "note": "Reasoning for hypothesis"
    }
  ],
  "legitimate_alternatives": [
    {
      "explanation": "Benign explanation",
      "how_to_verify": "Action to confirm or rule out"
    }
  ],
  "recommended_actions": [
    "Specific compliance action 1",
    "Specific compliance action 2"
  ]
}
"""


def build_investigation_cases(G: nx.MultiDiGraph, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Groups findings into unified investigation cases by overlapping entities using graph connectivity."""
    if not findings:
        return []

    # Build an undirected affiliation graph connecting findings and entities
    affil_graph = nx.Graph()
    for idx, f in enumerate(findings):
        f_node = f"FINDING_{idx}"
        affil_graph.add_node(f_node, type="finding", index=idx)
        for ent in f.get("entities", []):
            affil_graph.add_node(ent, type="entity")
            affil_graph.add_edge(f_node, ent)

    # Connected components define isolated cases
    components = list(nx.connected_components(affil_graph))
    cases = []

    for c_idx, comp in enumerate(components, 1):
        case_findings = [
            findings[affil_graph.nodes[n]["index"]]
            for n in comp
            if affil_graph.nodes[n].get("type") == "finding"
        ]
        case_entities = [n for n in comp if affil_graph.nodes[n].get("type") == "entity"]

        if not case_findings:
            continue

        # Compute case metrics
        scores = [f.get("risk_score", f.get("score", 50)) for f in case_findings]
        max_score = max(scores) if scores else 50
        avg_score = sum(scores) / len(scores) if scores else 50
        combined_score = min(100, int(max_score * 0.75 + avg_score * 0.25 + min(15, len(case_findings) * 3)))

        # Evidence strength & confidence
        if combined_score >= 80 and len(case_findings) >= 2:
            strength = "STRONG"
            conf = min(98, 75 + len(case_findings) * 5)
        elif combined_score >= 50:
            strength = "MODERATE"
            conf = 65
        else:
            strength = "WEAK"
            conf = 45

        # Extract transactions
        txns = set()
        for f in case_findings:
            raw_txs = f.get("transaction_ids", f.get("transactions", []))
            for t in raw_txs:
                if t:
                    txns.add(str(t))

        signal_types = [f.get("pattern_id", f.get("detector", "Anomaly")) for f in case_findings]
        top_name = case_findings[0].get("pattern_name", case_findings[0].get("title", "Suspicious Activity")) if case_findings else "General Alert"

        cases.append({
            "id": f"CASE-{c_idx:02d}",
            "title": f"Network Syndicate Cluster #{c_idx}",
            "risk_score": combined_score,
            "risk_level": "CRITICAL" if combined_score >= 85 else "HIGH" if combined_score >= 70 else "MEDIUM" if combined_score >= 40 else "LOW",
            "evidence_strength": strength,
            "confidence": conf,
            "entities": sorted(case_entities),
            "entity_count": len(case_entities),
            "transactions": sorted(txns),
            "findings": case_findings,
            "signals": signal_types,
            "top_signal": top_name,
        })

    # Sort cases with highest risk score first
    cases.sort(key=lambda x: x["risk_score"], reverse=True)
    return cases


def compile_case_evidence_package(
    G: nx.MultiDiGraph,
    case: Dict[str, Any],
    data_dict: Dict[str, pd.DataFrame],
) -> Dict[str, Any]:
    """Compiles a complete evidence package containing graph relationships, transactions, and detector findings."""
    ents = set(case.get("entities", []))

    # Collect transaction rows
    case_tx_rows = []
    if "transactions" in data_dict and data_dict["transactions"] is not None and not data_dict["transactions"].empty:
        df_tx = data_dict["transactions"]
        filtered_tx = df_tx[
            df_tx["source_account_id"].astype(str).isin(ents) |
            df_tx["target_account_id"].astype(str).isin(ents) |
            df_tx["transaction_id"].astype(str).isin(set(case.get("transactions", [])))
        ]
        case_tx_rows = filtered_tx.to_dict(orient="records")

    # Collect sub-graph edges
    relationships = []
    for u, v, d in G.edges(data=True):
        if u in ents and v in ents:
            relationships.append({
                "from": u,
                "to": v,
                "type": d.get("type", "CONNECTED"),
                "amount": d.get("amount"),
                "timestamp": d.get("timestamp"),
            })

    # Legitimate alternatives and recommended reviews to rule out
    alternatives = []
    for f in case.get("findings", []):
        alt = f.get("alternative_explanation") or f.get("legitimate_alternative")
        if alt:
            alternatives.append({
                "detector": f.get("pattern_id") or f.get("detector"),
                "pattern_name": f.get("pattern_name", ""),
                "explanation": alt,
                "recommended_review": f.get("recommended_review", ""),
            })

    return {
        "case_id": case.get("id"),
        "risk_score": case.get("risk_score"),
        "risk_level": case.get("risk_level"),
        "evidence_strength": case.get("evidence_strength"),
        "confidence": case.get("confidence"),
        "entities": case.get("entities"),
        "findings": case.get("findings"),
        "signals": case.get("signals"),
        "relationships": relationships[:30],
        "transactions": case_tx_rows[:40],
        "alternative_hypotheses": alternatives,
    }


def generate_fallback_case_report(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic fallback investigation report when no LLM key is configured."""
    case_id = evidence.get("case_id", "CASE-XX")
    score = evidence.get("risk_score", 70)
    ents = evidence.get("entities", [])
    fs = evidence.get("findings", [])
    alts = evidence.get("alternative_hypotheses", [])

    finding_summaries = [f.get("description", "") for f in fs]

    return {
        "summary": f"{case_id} involves {len(ents)} connected entities with a calculated risk score of {score}/100 based on {len(fs)} graph detector signals (Deterministic Template Report).",
        "verdict": "likely_fraud_ring" if score >= 80 else "suspicious" if score >= 50 else "likely_benign",
        "pattern_analysis": " ".join(finding_summaries) or "Multi-point entity correlation across transaction corridors and infrastructure fingerprints.",
        "narrative": (
            f"Investigation of {case_id} identified multiple coordinated anomalies across {len(ents)} linked entities. "
            f"The primary detectors flagged high-risk patterns including {', '.join(set(evidence.get('signals', ['anomalous flows'])))}. "
            f"The rapid velocity, shared infrastructure, and non-linear fund movements indicate deliberate obfuscation. "
            f"\n\nHowever, before escalating to law enforcement, compliance officers must examine whether these transfers reflect legitimate business activities such as escrow management, treasury netting, or familial device sharing. "
            f"Further KYC validation is recommended."
        ),
        "risk_rationale": f"High risk score ({score}/100) triggered by {len(fs)} distinct forensic detector findings with cross-entity connectivity.",
        "hypotheses": [
            {
                "title": "Organized Money Laundering Syndicate",
                "confidence": round(score / 100, 2),
                "supporting": ents[:8],
                "against": [],
                "note": "Corroborated by deterministic graph detectors and shared entity connections.",
            },
            {
                "title": "Legitimate Commercial or Personal Clearing",
                "confidence": round(max(0.1, 1 - (score / 100)), 2),
                "supporting": ents[-3:] if len(ents) >= 3 else ents,
                "against": [f.get("target_entity", "") for f in fs if f.get("target_entity")],
                "note": alts[0]["explanation"] if alts else "Multi-account usage can arise from authorized corporate treasury or family device sharing.",
            },
        ],
        "legitimate_alternatives": alts if alts else [
            {"explanation": "Centralized merchant processing or corporate payment gateway.", "how_to_verify": "Verify merchant incorporation documents and processing licenses."}
        ],
        "recommended_actions": [
            "Place temporary monitoring holds on high-velocity outflow accounts.",
            "Issue enhanced customer due diligence (EDD) requests to primary account holders.",
            "Review device telemetry and IP login histories for automated bot behavior.",
            "Prepare a Suspicious Activity Report (SAR / STR) if beneficial ownership remains unverifiable.",
        ],
        "source": "Deterministic Template Fallback",
    }


def generate_ai_investigation_report(
    evidence: Dict[str, Any],
    api_key: Optional[str] = None,
    model: str = "gemini-2.5-flash",
) -> Dict[str, Any]:
    """Generates an AI-driven investigation case report using Google Gemini or Anthropic with fallback protection."""
    # Check for provided key or environment variables
    gemini_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    # 1. Attempt Google Gemini via google-genai SDK
    if gemini_key and gemini_key.strip() and not gemini_key.startswith("your-"):
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=gemini_key.strip())
            prompt_content = f"Here is the investigation evidence package:\n{json.dumps(evidence, indent=2, default=str)}"

            response = client.models.generate_content(
                model=model,
                contents=prompt_content,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
            raw_text = (response.text or "").strip()
            raw_text = re.sub(r"^```(?:json)?", "", raw_text)
            raw_text = re.sub(r"```$", "", raw_text).strip()
            parsed = json.loads(raw_text)
            parsed["source"] = f"Google Gemini ({model})"
            return parsed
        except Exception as e:
            fallback = generate_fallback_case_report(evidence)
            fallback["source"] = f"Template Fallback (Gemini Error: {str(e)[:120]})"
            return fallback

    # 2. Attempt Anthropic if configured
    if anthropic_key and anthropic_key.strip() and not anthropic_key.startswith("your-"):
        try:
            import anthropic
            ant_model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
            client = anthropic.Anthropic(api_key=anthropic_key.strip())
            msg = client.messages.create(
                model=ant_model,
                max_tokens=2500,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": json.dumps(evidence, indent=2, default=str)}],
            )
            raw_text = (msg.content[0].text or "").strip()
            raw_text = re.sub(r"^```(?:json)?", "", raw_text)
            raw_text = re.sub(r"```$", "", raw_text).strip()
            parsed = json.loads(raw_text)
            parsed["source"] = f"Anthropic ({ant_model})"
            return parsed
        except Exception as e:
            fallback = generate_fallback_case_report(evidence)
            fallback["source"] = f"Template Fallback (Anthropic Error: {str(e)[:120]})"
            return fallback

    # 3. Deterministic template fallback
    return generate_fallback_case_report(evidence)
