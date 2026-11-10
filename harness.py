"""Shared timing helpers: fresh copy per run, perf_counter, median of REPS, DNF rule."""
import csv, json, os, statistics
from time import perf_counter

import config
from algos import (DNF, insertion_sort, merge_sort, naive_quick_sort,
                   hardened_quick_sort, heap_sort)

# Contender name -> callable(a, deadline) -> (sorted, Stats)
SORTS = {
    "Insertion Sort":      lambda a, d: insertion_sort(a, deadline=d),
    "Merge Sort":          lambda a, d: merge_sort(a, deadline=d),
    "Naive Quick Sort":    lambda a, d: naive_quick_sort(a, deadline=d),
    "Hardened Quick Sort": lambda a, d: hardened_quick_sort(a, seed=config.S, deadline=d),
    "Heap Sort":           lambda a, d: heap_sort(a, deadline=d),
}
STABLE = {"Insertion Sort": "yes", "Merge Sort": "yes", "Naive Quick Sort": "no",
          "Hardened Quick Sort": "no", "Heap Sort": "no"}

FIELDS = ["part", "condition", "n", "algo", "K", "window_s", "status", "median_s",
          "times_s", "comps", "moves", "extra", "correct", "note"]


def timed(fn, base, reps=None, check=None):
    """Run fn on a fresh copy of `base` up to `reps` times.
    Returns dict(status, median_s, times, stats, out). Stops at the first DNF."""
    reps = reps or config.REPS
    times, stats, out = [], None, None
    for r in range(reps):
        inp = list(base)                       # fresh copy of identical input
        t0 = perf_counter()
        try:
            out, stats = fn(inp, t0 + config.DNF_SECONDS)
        except DNF:
            return {"status": "DNF", "median_s": None, "times": times + [f">{config.DNF_SECONDS}"],
                    "stats": None, "out": None, "correct": ""}
        times.append(perf_counter() - t0)
    ok = check(out) if check else ""
    return {"status": "ok", "median_s": statistics.median(times), "times": times,
            "stats": stats, "out": out, "correct": ok}


def write_row(row, path=None):
    path = path or config.RESULTS
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        r = {k: row.get(k, "") for k in FIELDS}
        if isinstance(r["times_s"], list):
            r["times_s"] = json.dumps([round(t, 6) if isinstance(t, float) else t for t in r["times_s"]])
        w.writerow(r)
        f.flush()
