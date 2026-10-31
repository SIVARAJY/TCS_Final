"""Stage 5 - AI investigation: hypotheses, supporting + contradicting evidence, benign alternatives."""
import json, os, re
from dotenv import load_dotenv

load_dotenv()
SYSTEM = """You are a senior financial-crime investigator assistant. You receive a JSON evidence package built by deterministic detectors, entity resolution and an assessment layer.
Do this:
1. pattern_analysis: describe the pattern ACROSS multiple transactions (who paid whom, in what order, how fast). A pattern is worth investigating, not proof of fraud.
2. hypotheses: 2-3 competing hypotheses, at least one legitimate. Each has supporting AND contradicting evidence IDs, a confidence 0-1, and a note on why you generated it.
3. Use alternative_explanations, mitigating_findings and rejected_identity_matches as counter-evidence.
4. narrative: 2-3 short paragraphs, human-readable, that state the suspicious reading, then the legitimate reading, then what to verify.
5. Keep evidence strength, risk level and confidence separate. Do NOT change the numbers in assessment; explain them in risk_rationale.
Rules: use ONLY facts in the package; cite evidence IDs that exist in it (ACC-101, DEV-7, IP-55, CUS-3, TXN-004); never invent names, amounts or links. The AI recommends; a human investigator decides.
Return ONLY JSON (no markdown fences):
{"summary": str, "verdict": "likely_fraud_ring"|"suspicious"|"likely_benign", "pattern_analysis": str, "narrative": str, "risk_rationale": str,
 "hypotheses": [{"title": str, "confidence": number, "supporting": [str], "against": [str], "note": str}],
 "reasons": [{"claim": str, "evidence": [str]}],
 "recommended_actions": [str]}"""


def fallback_report(ev):
    """Deterministic report: used when no API key is set or the LLM call fails (demo safety net)."""
    a = ev.get("assessment", {})
    fs = ev.get("findings", [])
    benign_ids = [e for f in fs if f.get("benign") for e in f.get("entities", [])]
    risky = [e for f in fs if not f.get("benign") for e in f.get("entities", []) + f.get("txns", [])]
    score = a.get("risk_score", ev.get("risk_score", 0))
    alt = a.get("alternative_explanations", [])
    flows = [f.get("description", "") for f in fs if f.get("type") in ("fan_in", "pass_through", "rapid_movement", "circular_flow")]
    strength = a.get("evidence_strength", "MEDIUM").lower()
    confidence = a.get("confidence", score)
    next_inv = a.get("next_investigation", [
        "Hold outgoing transfers on flagged accounts pending review",
        "Request fresh KYC for linked customers",
        "File a suspicious activity report if confirmed",
    ])
    signals = ev.get("signal_points", {})
    sig_str = ", ".join(f"{k.replace('_', ' ')} +{v}" for k, v in signals.items()) if signals else "Detector signals"

    return {
        "summary": f"{ev.get('case_id', 'Case')}: {len(ev.get('entities', []))} linked entities, risk {score}/100, evidence {strength}, confidence {confidence}/100 (template report, no LLM key).",
        "verdict": "likely_fraud_ring" if score >= 60 else "suspicious" if score >= 35 else "likely_benign",
        "pattern_analysis": " ".join(flows) or "No multi-transaction money pattern in this case.",
        "narrative": "The detectors found: " + " ".join(f.get("description", "") for f in fs[:4])
                     + ("\n\nHowever, " + " ".join(x.get("explanation", "") for x in alt[:2]) if alt else "")
                     + ("\n\nNext: " + " ".join(next_inv[:2]) if next_inv else ""),
        "risk_rationale": "Signals: " + sig_str,
        "hypotheses": [
            {"title": "Coordinated financial activity", "confidence": round(confidence / 100, 2), "supporting": sorted(set(risky))[:10], "against": benign_ids[:4],
             "note": "Generated because several independent signals point at the same entities."},
            {"title": "Legitimate explanation", "confidence": round(max(0, 100 - confidence) / 100, 2), "supporting": benign_ids[:6], "against": [],
             "note": alt[0].get("explanation", "Shared infrastructure alone does not prove fraud.") if alt else "Shared infrastructure alone does not prove fraud."}],
        "reasons": [{"claim": f.get("description", ""), "evidence": f.get("entities", [])[:4] + f.get("txns", [])[:4]} for f in fs],
        "recommended_actions": next_inv,
        "source": "template",
    }


def generate_report(ev):
    # Support Gemini via GEMINI_API_KEY or GOOGLE_API_KEY
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key and gemini_key.strip() and gemini_key not in ("your-gemini-key-here", "your-gemini-api-key-here"):
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=gemini_key.strip())
            model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            response = client.models.generate_content(
                model=model,
                contents=f"Here is the evidence package:\n{json.dumps(ev)}",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM,
                    response_mime_type="application/json",
                ),
            )
            text = (response.text or "").strip()
            text = re.sub(r"^```(?:json)?", "", text)
            text = re.sub(r"```$", "", text).strip()
            return {**json.loads(text), "source": f"gemini ({model})"}
        except Exception as e:
            print("Gemini LLM error:", e)
            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            if not (anthropic_key and anthropic_key.strip() and anthropic_key not in ("your-anthropic-key-here", "your-key-here")):
                return {**fallback_report(ev), "error": str(e)}

    # Fallback to Anthropic if configured
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key and anthropic_key.strip() and anthropic_key not in ("your-anthropic-key-here", "your-key-here"):
        try:
            import anthropic
            model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
            msg = anthropic.Anthropic(api_key=anthropic_key.strip()).messages.create(
                model=model, max_tokens=2500, system=SYSTEM,
                messages=[{"role": "user", "content": json.dumps(ev)}])
            text = re.sub(r"```(?:json)?", "", msg.content[0].text).strip()
            return {**json.loads(text), "source": f"anthropic ({model})"}
        except Exception as e:
            print("Anthropic LLM error:", e)
            return {**fallback_report(ev), "error": str(e)}

    return fallback_report(ev)
