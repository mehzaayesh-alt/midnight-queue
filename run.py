"""Experiment driver.

    python run.py C            # Problem C tournament (all conditions x sizes x contenders)
    python run.py D            # Problem D shift queue
    python run.py E            # Problem E live feed
    python run.py M            # Problem F measurements (inversions on C5, band groups for M6)
    python run.py C --sizes 1000 10000 --conds C2 C6 --algos "Heap Sort"   # any subset
    python run.py C --workers 2  # run independent chains on 2 cores

Every row goes to results.csv (config.RESULTS). Output of every completed run is
checked against Python's sorted() (reference only, never inside a contender).
"""
import argparse, json, os, sys
from multiprocessing import Pool
from time import perf_counter

import config, data
from harness import SORTS, STABLE, timed, write_row
from algos import (merge_sort, topk_heap, topk_buffer, merge_topk, LiveHeap,
                   count_inversions, naive_quick_sort)

_DF = None
_CACHE = {}


def df():
    global _DF
    if _DF is None:
        _DF = data.load()
    return _DF


def inputs(cond, n):
    if (cond, n) not in _CACHE:
        _CACHE[(cond, n)] = data.build(data.sample_rows(df(), n), cond)
    return _CACHE[(cond, n)]


# ------------------------------------------------------------------ Problem C
def c_chain(job):
    """One (condition, contender) over ascending sizes. Once a size DNFs, every
    larger size is recorded as DNF without running (cost only grows with n)."""
    cond, algo, sizes = job
    dead = False
    for n in sizes:
        if dead:
            write_row({"part": "C", "condition": cond, "n": n, "algo": algo, "status": "DNF",
                       "note": "not run: smaller n already DNF", "times_s": []})
            continue
        base = inputs(cond, n)
        ref = sorted(base)                                   # trusted reference
        res = timed(SORTS[algo], base, check=lambda out: out == ref)
        st = res["stats"]
        write_row({"part": "C", "condition": cond, "n": n, "algo": algo, "status": res["status"],
                   "median_s": res["median_s"], "times_s": res["times"],
                   "comps": st.comps if st else "", "moves": st.moves if st else "",
                   "extra": st.peak_extra if st else "", "correct": res["correct"],
                   "note": "stable=" + STABLE[algo]})
        print(f"C {cond} n={n} {algo}: {res['status']} {res['median_s']}", flush=True)
        dead = res["status"] == "DNF"
    # labelled baseline: Python's built-in sorted() (Timsort in C), NOT a contender
    return job


def c_baseline(cond, sizes):
    for n in sizes:
        base = inputs(cond, n)
        res = timed(lambda a, d: (sorted(a), None), base)
        write_row({"part": "C", "condition": cond, "n": n, "algo": "sorted() baseline",
                   "status": "ok", "median_s": res["median_s"], "times_s": res["times"],
                   "note": "built-in Timsort, reference only"})


def run_C(args):
    jobs = [(c, a, args.sizes) for a in args.algos for c in args.conds]
    # heaviest chains first so the 2 workers finish together
    weight = {"Insertion Sort": 3, "Naive Quick Sort": 2}
    jobs.sort(key=lambda j: -weight.get(j[1], 1))
    if args.workers > 1:
        with Pool(args.workers) as p:
            list(p.imap_unordered(c_chain, jobs))
    else:
        for j in jobs:
            c_chain(j)
    for c in args.conds:
        c_baseline(c, args.sizes)


# ------------------------------------------------------------------ Problem D
def d_job(job):
    n, cond, K = job
    base = inputs(cond, n)
    ref = sorted(base)[:K]
    methods = {
        "Full sort (Merge Sort) + first K": lambda a, d: (lambda r: (r[0][:K], r[1]))(merge_sort(a, deadline=d)),
        "size-K heap": lambda a, d: topk_heap(a, K, deadline=d),
        "bounded insertion buffer": lambda a, d: topk_buffer(a, K, deadline=d),
    }
    for name, fn in methods.items():
        res = timed(fn, base, check=lambda out: out == ref)
        st = res["stats"]
        write_row({"part": "D", "condition": cond, "n": n, "algo": name, "K": K,
                   "status": res["status"], "median_s": res["median_s"], "times_s": res["times"],
                   "comps": st.comps if st else "", "moves": st.moves if st else "",
                   "extra": st.peak_extra if st else "", "correct": res["correct"]})
        print(f"D n={n} {cond} K={K} {name}: {res['status']} {res['median_s']}", flush=True)
    return job


def run_D(args):
    jobs = []
    for n in config.D_SIZES:
        for cond in config.D_CONDITIONS:
            for K in config.D_KS:
                jobs.append((n, cond, n // 10 if K == "n/10" else K))
    jobs.sort(key=lambda j: -j[2])                  # big K (slow buffer) first
    with Pool(args.workers) as p:
        list(p.imap_unordered(d_job, jobs))
    fraud_curve()


def fraud_curve():
    """Class used for EVALUATION ONLY: share of frauds inside the top K of the triage order."""
    d = df()
    order, _ = merge_sort([int(x) for x in d["key"]])
    cls = dict(zip((int(x) for x in d["key"]), d["Class"]))
    total = int(d["Class"].sum())
    caught, curve, half_k = 0, [], None
    for i, k in enumerate(order, 1):
        caught += cls[k]
        curve.append(caught)
        if half_k is None and caught * 2 >= total:
            half_k = i
    os.makedirs("out", exist_ok=True)
    json.dump({"total": total, "half_K": half_k, "curve": curve}, open("out/fraud_curve.json", "w"))
    print("smallest K capturing half the frauds:", half_k)
    # cost of producing that queue by each method (full file, C1 and C2)
    for cond in config.D_CONDITIONS:
        d_job((len(d), cond, half_k))


# ------------------------------------------------------------------ Problem E
def windows(win_s):
    d = df()
    keys = [int(x) for x in d["key"]]
    t = list(d["t"])
    out, cur, edge = [], [], win_s
    for k, ti in zip(keys, t):                     # file is in Time order
        while ti >= edge:
            out.append(cur); cur = []; edge += win_s
        cur.append(k)
    out.append(cur)
    return out


def e_strategy(name, wins, K):
    """Returns (per-window elapsed seconds, published lists, peak extra slots)."""
    per, pubs, peak = [], [], 0
    if name == "(a) re-rank everything":
        seen = []
        for w in wins:
            t0 = perf_counter()
            seen.extend(w)
            r, st = merge_sort(seen)
            top = r[:K]
            per.append(perf_counter() - t0)
            pubs.append(top)
            peak = max(peak, len(seen) + st.peak_extra + len(r))   # kept list + aux + sorted copy
    elif name == "(b) size-K heap":
        h = LiveHeap(K)
        for w in wins:
            t0 = perf_counter()
            h.feed(w)
            top = h.publish()
            per.append(perf_counter() - t0)
            pubs.append(top)
            peak = max(peak, K + len(top))                          # heap + published copy
    elif name == "(c) merge sort window + merge":
        top = []
        for w in wins:
            t0 = perf_counter()
            ws, st = merge_sort(w)
            top, _ = merge_topk(top, ws, K)
            per.append(perf_counter() - t0)
            pubs.append(top)
            peak = max(peak, len(ws) + st.peak_extra + 2 * K)       # sorted window + aux + old/new top
    return per, pubs, peak


def e_job(job):
    win_s, name = job
    K = config.K
    wins = windows(win_s)
    runs = []
    for r in range(config.E_REPS):
        per, pubs, peak = e_strategy(name, wins, K)
        runs.append(per)
        if r == 0:                                  # verify every published list once
            seen, ok = [], True
            for w, p in zip(wins, pubs):
                seen.extend(w)
                ok &= (p == sorted(seen)[:K])
    totals = [sum(p) for p in runs]
    import statistics
    med = statistics.median(totals)
    # median cumulative curve across reps (per window index)
    cum = []
    for i in range(len(wins)):
        cum.append(statistics.median(sum(p[:i + 1]) for p in runs))
    write_row({"part": "E", "n": len(df()), "algo": name, "K": K, "window_s": win_s,
               "status": "ok", "median_s": med, "times_s": totals, "extra": peak,
               "correct": ok, "note": f"windows={len(wins)}"})
    print(f"E win={win_s} {name}: {med:.2f}s peak={peak} ok={ok}", flush=True)
    return (win_s, name, cum, peak, len(wins))


def run_E(args):
    jobs = [(w, s) for w in config.E_WINDOWS
            for s in ["(a) re-rank everything", "(b) size-K heap", "(c) merge sort window + merge"]]
    with Pool(args.workers) as p:
        res = p.map(e_job, jobs)
    os.makedirs("out", exist_ok=True)
    json.dump([{"window_s": w, "algo": s, "cum": c, "peak": pk, "windows": nw} for w, s, c, pk, nw in res],
              open("out/E_curves.json", "w"))


# ------------------------------------------------------------------ Problem F measurements
def run_M(args):
    out = {"C5": {}, "C6": {}}
    for n in config.SIZES:
        a = inputs("C5", n)
        inv = count_inversions(a)
        # z = number of prefix minima after position 0 (insertion loop that runs off the left end)
        z, mn = 0, a[0]
        for x in a[1:]:
            if x < mn:
                z += 1; mn = x
        out["C5"][n] = {"I": inv, "pred_comps": inv + (n - 1) - z, "pred_moves": inv + (n - 1), "z": z}
        b = inputs("C6", n)
        groups = {}
        for x in b:
            groups[x] = groups.get(x, 0) + 1
        m = list(groups.values())
        out["C6"][n] = {"groups": {9 - k: v for k, v in groups.items()},
                        "sum_m2": sum(v * (v - 1) // 2 for v in m)}
        if n <= 10_000:   # exact naive-quick count is cheap here; larger n come from Problem C rows
            _, st = naive_quick_sort(b)
            out["C6"][n]["measured"] = st.comps
        print(n, out["C5"][n], out["C6"][n], flush=True)
    json.dump(out, open("out/math.json", "w"), indent=1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("part", choices=["C", "D", "E", "M", "fraud"])
    ap.add_argument("--sizes", nargs="*", type=int, default=config.SIZES)
    ap.add_argument("--conds", nargs="*", default=config.CONDITIONS)
    ap.add_argument("--algos", nargs="*", default=list(SORTS))
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    t = perf_counter()
    {"C": run_C, "D": run_D, "E": run_E, "M": run_M, "fraud": lambda _: fraud_curve()}[a.part](a)
    print(f"done in {perf_counter() - t:.0f}s")
