"""Deterministic fraud-pattern detectors. Code finds the facts; the LLM only explains them."""
from collections import defaultdict
from resolve import norm_addr
from datetime import datetime
import networkx as nx

WEIGHTS = {"shared_ip": 15, "same_entity": 20, "shared_device": 25, "fan_in": 25, "pass_through": 20, "circular_flow": 20, "rapid_movement": 15}


def build_graph(nodes, edges):
    G = nx.MultiDiGraph()
    for nd in nodes:
        G.add_node(nd["id"], **nd)
    for e in edges:
        G.add_edge(e["source"], e["target"], **e)
    return G


def _transfers(G):
    return [d for _, _, d in G.edges(data=True) if d["type"] in ("TRANSFER", "PAYS")]


def detect(G):
    findings = []

    def add(kind, entities, txns, text, weight=None, benign=False):
        findings.append({"id": f"F-{len(findings)+1:02d}", "type": kind, "weight": weight or WEIGHTS[kind], "benign": benign,
                         "entities": sorted(set(entities)), "txns": sorted(set(txns)), "description": text})

    # 1. Shared device / shared IP across customers (household sharing is treated as a benign explanation)
    for nid, d in G.nodes(data=True):
        if d["type"] not in ("device", "ip"):
            continue
        rel = "USES" if d["type"] == "device" else "LOGIN_FROM"
        users = [u for u, _, e in G.in_edges(nid, data=True) if e["type"] == rel]
        if len(users) >= 2:
            home = len({norm_addr(G.nodes[u].get("address", "")) for u in users}) == 1
            text = f"{len(users)} customers ({', '.join(users)}) share {d['type']} {nid}."
            add("shared_device" if d["type"] == "device" else "shared_ip", users + [nid], [],
                text + (" They share one home address, so this is likely a household." if home else ""),
                weight=5 if home else None, benign=home)

    # 1b. Same real person behind several customer records (entity resolution)
    for u, v, e in G.edges(data=True):
        if e["type"] == "SAME_AS":
            add("same_entity", [u, v], [], f"{u} and {v} look like the same person (confidence {e['confidence']:.0%}): {'; '.join(e['reasons'])}.")

    # 2. Fan-in: many distinct accounts paying one beneficiary
    senders, txs = defaultdict(set), defaultdict(list)
    for t in _transfers(G):
        if t["type"] == "TRANSFER":
            senders[t["target"]].add(t["source"]); txs[t["target"]].append(t["txn"])
    for acc, s in senders.items():
        if len(s) >= 3:
            add("fan_in", [acc, *s], txs[acc], f"{acc} receives money from {len(s)} different accounts ({', '.join(sorted(s))}).")

    # 3/5. Pass-through and rapid movement
    ins, outs = defaultdict(list), defaultdict(list)
    for t in _transfers(G):
        ts = datetime.fromisoformat(t["ts"])
        ins[t["target"]].append((ts, t["amount"], t["txn"]))
        if t["type"] == "TRANSFER":
            outs[t["source"]].append((ts, t["amount"], t["txn"]))
    for acc in outs:
        tot_in = sum(a for _, a, _ in ins[acc])
        tot_out = sum(a for _, a, _ in outs[acc])
        if tot_in < 1000 or not (0.85 <= tot_out / tot_in <= 1.05):
            continue
        delays, ids = [], []
        for ots, _, oid in outs[acc]:
            prior = [i for i in ins[acc] if i[0] <= ots]
            if prior:
                last = max(prior, key=lambda x: x[0])
                delays.append((ots - last[0]).total_seconds() / 60); ids += [oid, last[2]]
        if not delays:
            continue
        ids += [i[2] for i in ins[acc]]
        worst = max(delays)
        pct = round(100 * tot_out / tot_in)
        if worst <= 10:
            add("rapid_movement", [acc], ids, f"{acc} forwarded {pct}% of incoming funds within {worst:.0f} minutes.")
        if worst <= 240:
            add("pass_through", [acc], ids, f"{acc} passed on {pct}% of what it received (in {tot_in:,.0f}, out {tot_out:,.0f}) within {worst/60:.1f}h.")

    # 4. Circular flow
    D = nx.DiGraph()
    for t in _transfers(G):
        if t["type"] == "TRANSFER":
            D.add_edge(t["source"], t["target"])
    for cyc in nx.simple_cycles(D, length_bound=5):
        if len(cyc) >= 3:
            ids = [t["txn"] for t in _transfers(G) if t["type"] == "TRANSFER" and t["source"] in cyc and t["target"] in cyc]
            add("circular_flow", cyc, ids, f"Money circulates {' -> '.join(cyc)} -> {cyc[0]}.")
    return findings


def build_cases(G, findings):
    """Group findings that share any entity into cases (union-find), then score each case."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x

    def linked(f):  # a finding's entities plus the owners of its accounts, so device + money findings merge
        ents = set(f["entities"])
        for a in f["entities"]:
            ents.update(o for o, _, d in G.in_edges(a, data=True) if d["type"] == "OWNS")
        return sorted(ents)

    for f in findings:
        ents = linked(f)
        for e in ents[1:]:
            parent[find(e)] = find(ents[0])
        find(ents[0])
    groups = defaultdict(list)
    for f in findings:
        groups[find(linked(f)[0])].append(f)

    cases = []
    for fs in groups.values():
        ents = {e for f in fs for e in f["entities"]}
        for a in [e for e in ents if G.nodes[e]["type"] == "account"]:  # add owners + their devices for context
            for o, _, d in G.in_edges(a, data=True):
                if d["type"] == "OWNS":
                    ents.add(o)
                    ents.update(v for _, v, e in G.out_edges(o, data=True) if e["type"] in ("USES", "LOGIN_FROM"))
        grouped = defaultdict(list)
        for f in fs:
            grouped[f["type"]].append(f["weight"])
        # each signal counts once; repeats add up to +50%
        by_type = {k: round(max(w) * min(1.5, 1 + 0.25 * (len(w) - 1))) for k, w in grouped.items()}
        score = min(100, sum(by_type.values()))
        cases.append({"findings": fs, "entities": sorted(ents), "score": score, "signals": by_type,
                      "mitigating": [f["id"] for f in fs if f["benign"]]})
    cases.sort(key=lambda c: -c["score"])
    for i, c in enumerate(cases, 1):
        c["id"] = f"CASE-{i}"
        c["level"] = "high" if c["score"] >= 60 else "medium" if c["score"] >= 35 else "low"
    return cases


def case_evidence(G, case):
    """Subgraph + evidence package sent to the LLM (and shown in the UI)."""
    ents = set(case["entities"])
    txns = [d for _, _, d in G.edges(data=True) if d["type"] in ("TRANSFER", "PAYS") and d["source"] in ents and d["target"] in ents]
    txns.sort(key=lambda t: t["ts"])
    rels = []
    for u, v, d in G.edges(data=True):
        if d["type"] in ("OWNS", "USES", "LOGIN_FROM", "SAME_AS") and u in ents and v in ents:
            r = {"from": u, "to": v, "type": d["type"]}
            if d["type"] == "SAME_AS":
                r["confidence"] = d["confidence"]; r["reasons"] = d["reasons"]
            rels.append(r)
    return {
        "case_id": case["id"], "risk_score": case["score"], "signal_points": case["signals"],
        "mitigating_findings": case["mitigating"],
        "entities": [{"id": e, "type": G.nodes[e]["type"]} for e in case["entities"]],
        "customer_profiles": [{k: G.nodes[e].get(k) for k in ("id", "name", "dob", "address")} for e in case["entities"] if G.nodes[e]["type"] == "customer"],
        "relationships": rels,
        "transactions": [{k: t[k] for k in ("txn", "source", "target", "amount", "ts", "type")} for t in txns],
        "findings": case["findings"],
    }
