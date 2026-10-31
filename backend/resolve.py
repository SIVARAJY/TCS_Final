"""Stage 2 - Entity resolution: do two customer records describe the same real person?
Three outcomes: match (>=0.65), needs verification (similar name, thin evidence), rejected look-alike."""
import re
from difflib import SequenceMatcher
from itertools import combinations


def norm_name(s):
    return " ".join(t for t in re.sub(r"[^a-z ]", " ", s.lower()).split() if len(t) > 1)  # drops initials


def compact_name(s):
    return re.sub(r"[^a-z]", "", s.lower())  # keeps initials: "S. Kumar" -> "skumar"


def norm_phone(s):
    return re.sub(r"\D", "", s)[-10:]


def norm_addr(s):
    s = s.lower().replace("road", "rd").replace("street", "st")
    return re.sub(r"[^a-z0-9]", "", s)


def sim(a, b):
    return SequenceMatcher(None, a, b).ratio()


def name_sim(a, b):
    return max(sim(norm_name(a), norm_name(b)), sim(compact_name(a), compact_name(b)))


def resolve(nodes, edges, threshold=0.65):
    custs = [n for n in nodes if n["type"] == "customer"]
    accts = {}
    for e in edges:
        if e["type"] == "OWNS":
            accts.setdefault(e["source"], set()).add(e["target"])
    matches, review, rejected, compared = [], [], [], 0
    for a, b in combinations(custs, 2):
        compared += 1
        ns = name_sim(a["name"], b["name"])
        score, hit, miss = 0.30 * ns, [], []
        if ns >= 0.75:
            hit.append(f"names similar ({a['name']} / {b['name']})")
        for label, w, ok in (
            ("date of birth", 0.15, a["dob"] == b["dob"]),
            ("phone number", 0.20, norm_phone(a["phone"]) == norm_phone(b["phone"])),
            ("email", 0.15, a["email"].lower() == b["email"].lower()),
            ("address", 0.10, sim(norm_addr(a["address"]), norm_addr(b["address"])) >= 0.9),
            ("account identifier", 0.25, bool(accts.get(a["id"], set()) & accts.get(b["id"], set()))),
        ):
            if ok:
                score += w; hit.append(f"same {label}")
            else:
                miss.append(label)
        score = round(min(score, 1.0), 2)
        pair = {"a": a["id"], "b": b["id"]}
        if score >= threshold:
            matches.append({**pair, "confidence": score, "reasons": hit})
        elif ns >= 0.8 and len(hit) >= 2:  # similar name plus at least one other shared attribute, but not enough to link
            review.append({**pair, "score": score, "why": f"Names similar and {', '.join(h for h in hit[1:])}, but {', '.join(miss)} do not match - verify before linking."})
        elif ns >= 0.9:
            rejected.append({**pair, "score": score, "why": f"Names look alike but {', '.join(miss)} differ - treated as different people."})
    return {"matches": matches, "review": review, "rejected": rejected, "compared": compared}
