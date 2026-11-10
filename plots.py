"""All report figures, regenerated from results.csv + out/*.json.   python plots.py"""
import json, math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config

plt.rcParams.update({"font.size": 7.5, "axes.titlesize": 8, "legend.fontsize": 6.5,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.6,
                     "lines.linewidth": 1.6, "lines.markersize": 4.5, "savefig.dpi": 220})

ALGOS = ["Insertion Sort", "Merge Sort", "Naive Quick Sort", "Hardened Quick Sort", "Heap Sort"]
# fixed categorical order (validated palette slots 1-5) + markers/linestyles as secondary encoding
COL = dict(zip(ALGOS, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]))
MRK = dict(zip(ALGOS, ["o", "s", "^", "D", "v"]))
LS = dict(zip(ALGOS, ["-", "-", "--", "-", ":"]))
BASE = "#8a8984"
COND_NAME = {"C1": "C1 Arrival", "C2": "C2 Shuffled", "C3": "C3 Pre-ranked",
             "C4": "C4 Reverse", "C5": "C5 Nearly ranked", "C6": "C6 Band-only"}

R = pd.read_csv(config.RESULTS)
C = R[R.part == "C"].copy()
C["n"] = C["n"].astype(int)


def cell(cond, algo):
    d = C[(C.condition == cond) & (C.algo == algo)].sort_values("n")
    return d


def top_legend(fig, ax, ncol=6, extra=None):
    h, l = ax.get_legend_handles_labels()
    if extra:
        for a in extra:
            for hh, ll in zip(*a.get_legend_handles_labels()):
                if ll not in l: h.append(hh); l.append(ll)
    fig.legend(h, l, loc="upper center", ncol=ncol, frameon=False, fontsize=6.3,
               bbox_to_anchor=(0.5, 1.0), handlelength=2.6)
    fig.tight_layout(pad=0.4, rect=(0, 0, 1, 0.87))


def save(fig, name, legend=False):
    if not legend:
        fig.tight_layout(pad=0.4)
    fig.savefig(f"out/{name}.pdf")
    fig.savefig(f"out/{name}.png")
    plt.close(fig)


# ---------------------------------------------------------------- A: profile
def fig_profile():
    P = json.load(open("out/profile.json"))
    bands = list(range(10))
    cnt = [P["band_counts"].get(str(b), 0) for b in bands]
    fr = [P["fraud_by_band"].get(str(b), 0) for b in bands]
    fig, ax = plt.subplots(1, 2, figsize=(6.3, 1.75))
    ax[0].bar(bands, cnt, color=COL["Insertion Sort"], width=0.7, label="all transactions")
    ax[0].set_yscale("log"); ax[0].set_xticks(bands)
    ax[0].set_xlabel("risk band (0-9, dimensionless)"); ax[0].set_ylabel("transactions (count, log)")
    ax[0].set_title("(a) Risk-band histogram"); ax[0].legend(loc="upper right")
    for b, c in zip(bands, cnt):
        if c: ax[0].text(b, c * 1.15, f"{c:,}", ha="center", fontsize=5.5)
    ax[1].bar(bands, fr, color=COL["Merge Sort"], width=0.7, label="frauds (Class=1, evaluation only)")
    ax[1].set_xticks(bands); ax[1].set_xlabel("risk band (0-9, dimensionless)")
    ax[1].set_ylabel("frauds (count)"); ax[1].set_title("(b) Frauds per band"); ax[1].legend(loc="upper left")
    for b, c in zip(bands, fr):
        if c: ax[1].text(b, c + 3, str(c), ha="center", fontsize=5.5)
    save(fig, "fig_A")


# ---------------------------------------------------------------- C
def fig_C_time():
    fig, ax = plt.subplots(1, 2, figsize=(6.3, 2.35))
    for a in ALGOS:
        d = cell("C2", a)
        ok = d[d.status == "ok"]
        ax[0].plot(ok.n, ok.median_s, marker=MRK[a], ls=LS[a], color=COL[a], label=a)
        dnf = d[d.status == "DNF"]
        if len(dnf):
            ax[0].scatter(dnf.n, [config.DNF_SECONDS] * len(dnf), marker="x", color=COL[a], s=22, zorder=5)
    b = cell("C2", "sorted() baseline")
    ax[0].plot(b.n, b.median_s, ls="--", color=BASE, lw=1, label="sorted() baseline (built-in)")
    ax[0].axhline(config.DNF_SECONDS, color="#52514e", lw=0.8, ls=":")
    ax[0].text(1100, config.DNF_SECONDS * 1.25, "DNF limit 300 s (x = DNF)", fontsize=5.5)
    ax[0].set_xscale("log"); ax[0].set_yscale("log")
    ax[0].set_xlabel("input size n (records, log)"); ax[0].set_ylabel("median time (s, log)")
    ax[0].set_title("(a) Time vs n on C2 Shuffled")
    # grouped bars n=10,000
    conds = config.CONDITIONS
    x = np.arange(len(conds)); w = 0.16
    for i, a in enumerate(ALGOS):
        vals = []
        for c in conds:
            d = C[(C.condition == c) & (C.algo == a) & (C.n == 10_000)]
            vals.append(float(d.median_s.iloc[0]) if len(d) and d.status.iloc[0] == "ok" else np.nan)
        ax[1].bar(x + (i - 2) * w, vals, w * 0.92, color=COL[a], label=a)
    ax[1].set_yscale("log"); ax[1].set_xticks(x); ax[1].set_xticklabels([COND_NAME[c].replace(" ", "\n", 1) for c in conds], fontsize=6)
    ax[1].set_ylabel("median time (s, log)"); ax[1].set_xlabel("input condition (n = 10,000)")
    ax[1].set_title("(b) Time at n = 10,000, all conditions")
    top_legend(fig, ax[0], ncol=6)
    save(fig, "fig_C_time", legend=True)


def fig_C_counts():
    fig, ax = plt.subplots(1, 4, figsize=(6.3, 2.1))
    for a in ALGOS:
        ok = cell("C2", a); ok = ok[ok.status == "ok"]
        ax[0].plot(ok.n, ok.comps.astype(float), marker=MRK[a], ls=LS[a], color=COL[a], label=a)
        ax[1].plot(ok.n, ok.moves.astype(float), marker=MRK[a], ls=LS[a], color=COL[a], label=a)
        nl = ok.n * np.log2(ok.n); n2 = ok.n.astype(float) ** 2
        ax[2].plot(ok.n, ok.median_s / nl * 1e9, marker=MRK[a], ls=LS[a], color=COL[a], label=a)
        ax[3].plot(ok.n, ok.median_s / n2 * 1e9, marker=MRK[a], ls=LS[a], color=COL[a], label=a)
    for i, (t, yl) in enumerate([("(a) Comparisons, C2", "key comparisons (count, log)"),
                                 ("(b) Moves, C2", "element moves (count, log)"),
                                 ("(c) Time / (n log2 n), C2", "ns per n·log2 n (log)"),
                                 ("(d) Time / n^2, C2", "ns per n^2 (log)")]):
        ax[i].set_xscale("log"); ax[i].set_yscale("log"); ax[i].set_title(t)
        ax[i].set_xlabel("n (records, log)"); ax[i].set_ylabel(yl)
    top_legend(fig, ax[0], ncol=5)
    save(fig, "fig_C_counts", legend=True)


def fig_C_norm_all():
    """Time/(n lg n) for every contender and every condition (small multiples)."""
    fig, ax = plt.subplots(1, 6, figsize=(6.3, 1.7), sharey=True)
    for j, c in enumerate(config.CONDITIONS):
        for a in ALGOS:
            ok = cell(c, a); ok = ok[ok.status == "ok"]
            ax[j].plot(ok.n, ok.median_s / (ok.n * np.log2(ok.n)) * 1e9, marker=MRK[a], ls=LS[a],
                       color=COL[a], label=a, lw=1.2, ms=3.5)
        ax[j].set_xscale("log"); ax[j].set_yscale("log"); ax[j].set_title(COND_NAME[c], fontsize=7)
        ax[j].set_xlabel("n (log)")
    ax[0].set_ylabel("ns per n·log2 n (log)")
    h, l = ax[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=5, fontsize=6, bbox_to_anchor=(0.5, 1.06), frameon=False)
    fig.tight_layout(pad=0.3, rect=(0, 0, 1, 0.9))
    fig.savefig("out/fig_C_norm_all.pdf"); fig.savefig("out/fig_C_norm_all.png"); plt.close(fig)


# ---------------------------------------------------------------- D
DCOL = {"Full sort (Merge Sort) + first K": COL["Merge Sort"], "size-K heap": COL["Heap Sort"],
        "bounded insertion buffer": COL["Insertion Sort"]}
DMRK = {"Full sort (Merge Sort) + first K": "s", "size-K heap": "v", "bounded insertion buffer": "o"}


def fig_D():
    D = R[R.part == "D"].copy(); D["K"] = D.K.astype(int); D["n"] = D.n.astype(int)
    F = json.load(open("out/fraud_curve.json"))
    fig, ax = plt.subplots(1, 3, figsize=(6.3, 2.0))
    for i, n in enumerate(config.D_SIZES):
        for m in DCOL:
            for cond, ls in (("C2", "-"), ("C1", ":")):
                d = D[(D.n == n) & (D.algo == m) & (D.condition == cond)].sort_values("K")
                d = d[d.K.isin([10, 50, config.K, 500, 5000, n // 10])]
                ok = d[d.status == "ok"]
                ax[i].plot(ok.K, ok.median_s, marker=DMRK[m], ls=ls, color=DCOL[m],
                           label=f"{m} ({cond})", lw=1.3, ms=3.5)
        ax[i].set_xscale("log"); ax[i].set_yscale("log")
        ax[i].set_xlabel("K (cases kept, log)"); ax[i].set_ylabel("median time (s, log)")
        ax[i].set_title(f"({'ab'[i]}) Top-K cost, n = {n:,}")
    ax[0].legend(loc="upper left", fontsize=5.0)
    cur = np.array(F["curve"]) / F["total"]
    ks = np.arange(1, len(cur) + 1)
    ax[2].plot(ks, cur, color=COL["Insertion Sort"], label="triage order (risk band, Amount)")
    ax[2].axhline(0.5, color=BASE, lw=0.8, ls="--", label="half of all frauds")
    ax[2].axvline(F["half_K"], color=COL["Merge Sort"], lw=0.8, ls=":", label=f"K = {F['half_K']:,}")
    ax[2].axvline(config.K, color=COL["Heap Sort"], lw=0.8, ls="-.", label=f"my K = {config.K}")
    ax[2].set_xscale("log"); ax[2].set_xlabel("K (top of queue, log)")
    ax[2].set_ylabel("fraction of 492 frauds captured"); ax[2].set_title("(c) Fraud capture vs K")
    ax[2].legend(loc="upper left", fontsize=5.3)
    save(fig, "fig_D")


# ---------------------------------------------------------------- E
ECOL = {"(a) re-rank everything": COL["Merge Sort"], "(b) size-K heap": COL["Heap Sort"],
        "(c) merge sort window + merge": COL["Insertion Sort"]}


def fig_E():
    E = json.load(open("out/E_curves.json"))
    fig, ax = plt.subplots(1, 2, figsize=(6.3, 1.9))
    for i, w in enumerate(config.E_WINDOWS):
        for e in E:
            if e["window_s"] != w:
                continue
            x = np.arange(1, len(e["cum"]) + 1)
            ax[i].plot(x, e["cum"], color=ECOL[e["algo"]], label=f"{e['algo']}  (peak {e['peak']:,} slots)")
        ax[i].set_yscale("log"); ax[i].set_xlabel("window number")
        ax[i].set_ylabel("cumulative time (s, log)")
        ax[i].set_title(f"({'ab'[i]}) {'1-hour' if w == 3600 else '10-minute'} windows")
        ax[i].legend(loc="lower right", fontsize=5.5)
    save(fig, "fig_E")


if __name__ == "__main__":
    import sys
    fig_profile()
    for f in (fig_C_time, fig_C_counts, fig_C_norm_all, fig_D, fig_E):
        try:
            f()
        except Exception as ex:          # partial results while experiments still run
            print("skip", f.__name__, ex)
