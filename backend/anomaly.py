"""Stage 4b - Statistical + ML anomaly identification on per-account behaviour."""
from collections import defaultdict
from datetime import datetime
import numpy as np


def account_features(G):
    f = defaultdict(lambda: {"in": 0.0, "out": 0.0, "n_in": 0, "n_out": 0, "max": 0.0, "peers": set(), "txns": []})
    for _, _, d in G.edges(data=True):
        if d["type"] not in ("TRANSFER", "PAYS"):
            continue
        for acc, key, nk, other in ((d["target"], "in", "n_in", d["source"]), (d["source"], "out", "n_out", d["target"])):
            if acc.startswith("ACC-"):
                r = f[acc]; r[key] += d["amount"]; r[nk] += 1; r["max"] = max(r["max"], d["amount"]); r["peers"].add(other); r["txns"].append(d["txn"])
    return f


def detect_anomalies(G):
    """Returns [(account, description, txns)] for accounts that are outliers vs the population."""
    feats = account_features(G)
    accs = sorted(feats)
    if len(accs) < 8:
        return []
    X = np.array([[feats[a]["in"], feats[a]["out"], feats[a]["n_in"], feats[a]["n_out"], feats[a]["max"], len(feats[a]["peers"])] for a in accs])
    # robust z-score on the largest single transaction (median / MAD)
    m = X[:, 4]; med = np.median(m); mad = np.median(np.abs(m - med)) or 1.0
    z = 0.6745 * (m - med) / mad
    iso_flag = np.zeros(len(accs), dtype=bool)
    try:  # Isolation Forest if scikit-learn is installed
        from sklearn.ensemble import IsolationForest
        iso_flag = IsolationForest(n_estimators=200, contamination=0.08, random_state=0).fit_predict(np.log1p(X)) == -1
    except Exception:
        pass
    out = []
    for i, a in enumerate(accs):
        if z[i] >= 3.5 and iso_flag[i] or z[i] >= 8:
            r = feats[a]
            out.append((a, f"{a} is an outlier vs other accounts: largest transaction {r['max']:,.0f} is {z[i]:.0f} robust deviations above the median"
                           f"{' and Isolation Forest also isolates it' if iso_flag[i] else ''} (in {r['in']:,.0f}, out {r['out']:,.0f}).", r["txns"][:6]))
    return out
