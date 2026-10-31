"""Separates the three things the brief asks to keep apart:
evidence strength (how solid the facts are), risk level (how bad if true), investigation confidence (how well supported the hypothesis is)."""
from knowledge import KB, GENERIC_STEPS, POINTS, strength_of

ORDER = {"strong": 3, "moderate": 2, "weak": 1}


def assess(case):
    items, best = [], {}
    for f in case["findings"]:
        st = strength_of(f)
        items.append({"signal": f["type"], "observation": f["description"], "strength": st, "records": f["entities"] + f["txns"][:6]})
        if f["type"] not in best or ORDER[st] > ORDER[best[f["type"]]]:
            best[f["type"]] = st
    items.sort(key=lambda i: -ORDER[i["strength"]])
    strong = sum(1 for s in best.values() if s == "strong")
    moderate = sum(1 for s in best.values() if s == "moderate")
    label = "Strong" if strong >= 3 else "Moderate" if strong >= 1 or moderate >= 3 else "Weak"
    conf = 10 + sum(POINTS[s] for s in best.values())
    if case["mitigating"]:
        conf -= 10
    conf = max(5, min(95, conf))
    alts = [{"signal": t, "explanation": KB[t][1], "verify": KB[t][2]} for t in best]
    steps = []
    for t in best:
        if KB[t][3] not in steps:
            steps.append(KB[t][3])
    return {
        "evidence_strength": label,
        "risk_level": case["level"], "risk_score": case["score"],
        "confidence": conf,
        "caveat": "Illustrative score, not a real-world probability of fraud.",
        "evidence_items": items, "alternative_explanations": alts, "next_investigation": steps + GENERIC_STEPS,
    }
