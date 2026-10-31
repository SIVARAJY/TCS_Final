"""Stage 2 - Entity resolution: find customer records that may be the same real person."""
import re
from difflib import SequenceMatcher
from itertools import combinations


def norm_name(s):
    return " ".join(t for t in re.sub(r"[^a-z ]", " ", s.lower()).split() if len(t) > 1)  # drops initials


def norm_phone(s):
    return re.sub(r"\D", "", s)[-10:]


def norm_addr(s):
    s = s.lower().replace("road", "rd").replace("street", "st")
    return re.sub(r"[^a-z0-9]", "", s)


def sim(a, b):
    return SequenceMatcher(None, a, b).ratio()


def resolve(nodes, threshold=0.7):
    custs = [n for n in nodes if n["type"] == "customer"]
    matches, rejected, compared = [], [], 0
    for a, b in combinations(custs, 2):
        compared += 1
        ns = sim(norm_name(a["name"]), norm_name(b["name"]))
        score, reasons = 0.35 * ns, []
        if ns >= 0.9:
            reasons.append(f"names match ({a['name']} / {b['name']})")
        if a["dob"] == b["dob"]:
            score += 0.25; reasons.append("same date of birth")
        if norm_phone(a["phone"]) == norm_phone(b["phone"]):
            score += 0.20; reasons.append("same phone number")
        if sim(norm_addr(a["address"]), norm_addr(b["address"])) >= 0.9:
            score += 0.15; reasons.append("same address")
        score = round(score, 2)
        differs = [k for k, ok in (("date of birth", a["dob"] == b["dob"]), ("phone", norm_phone(a["phone"]) == norm_phone(b["phone"])),
                                   ("address", sim(norm_addr(a["address"]), norm_addr(b["address"])) >= 0.9)) if not ok]
        if score >= threshold:
            matches.append({"a": a["id"], "b": b["id"], "confidence": score, "reasons": reasons})
        elif ns >= 0.9:  # looks alike but evidence says different people -> kept as an alternative explanation
            rejected.append({"a": a["id"], "b": b["id"], "score": score,
                             "why": f"Names look alike but {', '.join(differs)} differ - treated as different people."})
    return {"matches": matches, "rejected": rejected, "compared": compared}
