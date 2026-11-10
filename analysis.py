"""Numbers quoted in the report: summary table, DNF predictions (and their
smaller-scale check), M1/M5/M6 theory-vs-measurement.  python analysis.py"""
import json, math
import pandas as pd
import config

R = pd.read_csv(config.RESULTS)
C = R[R.part == "C"].copy(); C["n"] = C.n.astype(int)
M = json.load(open("out/math.json"))
ALGOS = ["Insertion Sort", "Merge Sort", "Naive Quick Sort", "Hardened Quick Sort", "Heap Sort"]
OUT = {}


def get(cond, algo, n, col="median_s"):
    d = C[(C.condition == cond) & (C.algo == algo) & (C.n == n)]
    if not len(d) or d.status.iloc[0] != "ok":
        return None
    return float(d[col].iloc[0])


# ---- summary table (n = 10,000 counts; time at every n)
rows = []
for c in config.CONDITIONS:
    for a in ALGOS:
        r = {"cond": c, "algo": a}
        for n in config.SIZES:
            r[f"t{n}"] = get(c, a, n)
        r["comps"] = get(c, a, 10_000, "comps"); r["moves"] = get(c, a, 10_000, "moves")
        r["extra_full"] = get(c, a, 284_807, "extra") or get(c, a, 10_000, "extra")
        rows.append(r)
pd.DataFrame(rows).to_csv("out/summary_table.csv", index=False)
OUT["summary"] = rows

# ---- DNF predictions: quadratic model t = c n^2 from largest completed n,
#      plus a check of the same model one scale lower (1k -> 10k) against measurement
dnf = []
for c in config.CONDITIONS:
    for a in ALGOS:
        d = C[(C.condition == c) & (C.algo == a)].sort_values("n")
        bad = d[d.status == "DNF"]
        if not len(bad):
            continue
        ok = d[d.status == "ok"]
        n0, t0 = int(ok.n.iloc[-1]), float(ok.median_s.iloc[-1])
        preds = {int(n): t0 * (n / n0) ** 2 for n in bad.n}
        check = None
        if len(ok) >= 2:
            n1, t1 = int(ok.n.iloc[-2]), float(ok.median_s.iloc[-2])
            check = {"from_n": n1, "to_n": n0, "pred": t1 * (n0 / n1) ** 2, "meas": t0}
        dnf.append({"cond": c, "algo": a, "largest_ok": n0, "t_largest": t0, "pred": preds, "check": check})
OUT["dnf"] = dnf

# ---- M1: insertion on C5, exact identity
m1 = {}
for n in config.SIZES:
    meas = get("C5", "Insertion Sort", n, "comps")
    m1[n] = {"I": M["C5"][str(n)]["I"], "pred_comps": M["C5"][str(n)]["pred_comps"], "meas_comps": meas,
             "model_I": 0.01 * n * n / 3}
OUT["M1"] = m1

# ---- M2: merge comparisons vs n lg n - 1.25 n on C2
OUT["M2"] = {n: {"meas": get("C2", "Merge Sort", n, "comps"), "model": n * math.log2(n) - 1.25 * n}
             for n in config.SIZES}
# ---- M3a: naive quick on C3 = n(n-1)/2
OUT["M3"] = {n: {"meas": get("C3", "Naive Quick Sort", n, "comps"), "model": n * (n - 1) / 2}
             for n in config.SIZES}
# ---- M4: heap comparisons vs 2 n lg n
OUT["M4"] = {n: {"meas": get("C2", "Heap Sort", n, "comps"), "model": 2 * n * math.log2(n)}
             for n in config.SIZES}

# ---- M6
m6 = {}
for n in config.SIZES:
    meas = get("C6", "Naive Quick Sort", n, "comps") or M["C6"][str(n)].get("measured")
    m6[n] = {"groups": M["C6"][str(n)]["groups"], "pred": M["C6"][str(n)]["sum_m2"], "meas": meas}
OUT["M6"] = m6

# ---- D: best method per (n, cond, K) + M5 comparison model
D = R[R.part == "D"].copy()
if len(D):
    D["K"] = D.K.astype(int); D["n"] = D.n.astype(int)
    best = []
    for (n, cond, K), g in D.groupby(["n", "condition", "K"]):
        g = g[g.status == "ok"]
        w = g.loc[g.median_s.idxmin()]
        best.append({"n": n, "cond": cond, "K": K, "best": w.algo,
                     **{a: float(t) for a, t in zip(g.algo, g.median_s)},
                     **{a + " comps": int(x) for a, x in zip(g.algo, g.comps)}})
    OUT["D_best"] = best
    pd.DataFrame(best).to_csv("out/D_table.csv", index=False)

E = R[R.part == "E"]
if len(E):
    OUT["E"] = E[["algo", "window_s", "median_s", "extra", "correct", "note"]].to_dict("records")

json.dump(OUT, open("out/numbers.json", "w"), indent=1, default=str)
print(json.dumps({k: OUT[k] for k in ("dnf", "M1", "M2", "M3", "M4", "M6")}, indent=1, default=str))
