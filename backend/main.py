from collections import Counter
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from data_gen import generate
from resolve import resolve
from detectors import build_graph, detect, build_cases, case_evidence
from llm import generate_report

app = FastAPI(title="Financial Crime Network Investigator")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Pipeline: 1 collect -> 2 resolve -> 3 graph -> 4 anomalies -> (5 AI investigation, 6 report on demand)
NODES, EDGES = generate()
ER = resolve(NODES)
for m in ER["matches"]:
    EDGES.append({"source": m["a"], "target": m["b"], "type": "SAME_AS", "confidence": m["confidence"], "reasons": m["reasons"]})
G = build_graph(NODES, EDGES)
FINDINGS = detect(G)
CASES = build_cases(G, FINDINGS)
REPORTS = {}


def _get(case_id):
    c = next((c for c in CASES if c["id"] == case_id), None)
    if not c:
        raise HTTPException(404, "Case not found")
    return c


def _evidence(case):
    ev = case_evidence(G, case)
    ents = set(case["entities"])
    ev["rejected_identity_matches"] = [r for r in ER["rejected"] if r["a"] in ents or r["b"] in ents]
    return ev


@app.get("/api/health")
def health():
    return {"ok": True, "cases": len(CASES), "findings": len(FINDINGS)}


@app.get("/api/pipeline")
def pipeline():
    t = Counter(n["type"] for n in NODES)
    ftypes = Counter(f["type"] for f in FINDINGS)
    top = CASES[0] if CASES else None
    return {
        "stages": [
            {"name": "Data collection", "stat": f"{t['customer']} customers, {t['account']} accounts, {t['device']} devices, {t['ip']} IPs, {t['merchant']} merchants, {sum(1 for e in EDGES if e.get('txn'))} transactions"},
            {"name": "Entity resolution", "stat": f"{ER['compared']} pairs compared, {len(ER['matches'])} duplicate identities, {len(ER['rejected'])} look-alikes rejected"},
            {"name": "Graph", "stat": f"{len(NODES)} nodes, {len(EDGES)} relationships"},
            {"name": "Anomalies", "stat": f"{len(FINDINGS)} findings: " + ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in ftypes.items())},
            {"name": "AI investigation", "stat": f"{len(CASES)} cases, {len(REPORTS)} investigated"},
            {"name": "Report", "stat": f"Top risk {top['score']}/100 ({top['id']})" if top else "No cases"},
        ],
        "resolution": ER,
    }


@app.get("/api/graph")
def graph():
    case_of = {e: c["id"] for c in CASES for e in c["entities"]}
    flagged = {e for f in FINDINGS for e in f["entities"]}
    return {"nodes": [{**n, "flagged": n["id"] in flagged, "case": case_of.get(n["id"])} for n in NODES], "links": EDGES}


@app.get("/api/cases")
def cases():
    return [{k: c[k] for k in ("id", "score", "level", "signals")} | {"entities": len(c["entities"])} for c in CASES]


@app.get("/api/cases/{case_id}")
def case(case_id: str):
    return _evidence(_get(case_id))


@app.post("/api/cases/{case_id}/report")
def report(case_id: str, refresh: bool = False):
    if refresh or case_id not in REPORTS:
        REPORTS[case_id] = generate_report(_evidence(_get(case_id)))
    return REPORTS[case_id]
