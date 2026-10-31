"""Stage 5 - AI investigation: hypotheses, supporting + contradicting evidence, benign alternatives."""
import json, os, re
from dotenv import load_dotenv

load_dotenv()
SYSTEM = """You are a senior financial-crime investigator. You receive a JSON evidence package built by deterministic detectors and entity resolution.
Work like an investigator:
1. Form 2-3 competing hypotheses (at least one benign or low-risk explanation).
2. For each, list supporting evidence AND contradicting evidence, and give a confidence from 0 to 1.
3. Use the mitigating_findings and rejected_identity_matches fields as counter-evidence where relevant.
Rules: use ONLY facts in the package; every claim cites evidence IDs (entities like ACC-101, DEV-7, IP-55, CUS-3, transactions like TXN-004) that exist in it; never invent names, amounts or links; be honest about uncertainty.
Return ONLY JSON (no markdown fences):
{"summary": str, "verdict": "likely_fraud_ring"|"suspicious"|"likely_benign", "risk_rationale": str,
 "hypotheses": [{"title": str, "confidence": number, "supporting": [str], "against": [str], "note": str}],
 "connections": [str],
 "reasons": [{"claim": str, "evidence": [str]}],
 "recommended_actions": [str]}"""


def fallback_report(ev):
    """Deterministic report: used when no API key is set or the LLM call fails (demo safety net)."""
    score = ev["risk_score"]
    fs = ev["findings"]
    benign_ids = [e for f in fs if f["benign"] for e in f["entities"]]
    risky = [e for f in fs if not f["benign"] for e in f["entities"] + f["txns"]]
    ring = score >= 60
    return {
        "summary": f"{ev['case_id']} links {len(ev['entities'])} entities with a risk score of {score}/100 (template report - no LLM key).",
        "verdict": "likely_fraud_ring" if ring else "suspicious" if score >= 35 else "likely_benign",
        "risk_rationale": "Signals: " + ", ".join(f"{k.replace('_', ' ')} +{v}" for k, v in ev["signal_points"].items()),
        "hypotheses": [
            {"title": "Coordinated fraud network", "confidence": round(score / 100, 2), "supporting": sorted(set(risky))[:10], "against": benign_ids[:4],
             "note": "Built from detector findings."},
            {"title": "Innocent explanation (household, family or coincidence)", "confidence": round(1 - score / 100, 2), "supporting": benign_ids[:6], "against": [],
             "note": "Shared infrastructure alone does not prove fraud."}],
        "connections": [f"{r['from']} {r['type']} {r['to']}" for r in ev["relationships"]][:8],
        "reasons": [{"claim": f["description"], "evidence": f["entities"][:4] + f["txns"][:4]} for f in fs],
        "recommended_actions": ["Hold outgoing transfers on flagged accounts pending review", "Request fresh KYC for linked customers", "File a suspicious activity report if confirmed"],
        "source": "template",
    }


def generate_report(ev):
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return fallback_report(ev)
    try:
        import anthropic
        msg = anthropic.Anthropic(api_key=key).messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"), max_tokens=2500, system=SYSTEM,
            messages=[{"role": "user", "content": json.dumps(ev)}])
        text = re.sub(r"```(?:json)?", "", msg.content[0].text).strip()
        return {**json.loads(text), "source": "llm"}
    except Exception as e:  # never crash the demo
        print("LLM error:", e)
        return {**fallback_report(ev), "error": str(e)}
