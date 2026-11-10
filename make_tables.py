"""LaTeX tables for the report, generated from results.csv.  python make_tables.py"""
import json
import pandas as pd
import config

R = pd.read_csv(config.RESULTS)
C = R[R.part == "C"].copy(); C["n"] = C.n.astype(int)
ALGOS = ["Insertion Sort", "Merge Sort", "Naive Quick Sort", "Hardened Quick Sort", "Heap Sort"]
STAB = {"Insertion Sort": "yes", "Merge Sort": "yes"}


def t(x):
    if x is None:
        return "DNF"
    if x < 0.01:
        return f"{x*1000:.2f}ms"
    if x < 10:
        return f"{x:.3f}"
    return f"{x:.1f}"


def big(x):
    if x is None or x != x:
        return "--"
    x = float(x)
    if x >= 1e6:
        return f"{x/1e6:.2f}M"
    if x >= 1e3:
        return f"{x/1e3:.1f}k"
    return f"{int(x)}"


def row(cond, a):
    out = []
    for n in config.SIZES[1:]:
        d = C[(C.condition == cond) & (C.algo == a) & (C.n == n)]
        out.append(t(float(d.median_s.iloc[0])) if len(d) and d.status.iloc[0] == "ok" else "\\textbf{DNF}")
    d10 = C[(C.condition == cond) & (C.algo == a) & (C.n == 10_000)].iloc[0]
    ok = C[(C.condition == cond) & (C.algo == a) & (C.status == "ok")].sort_values("n").iloc[-1]
    return out + [big(d10.comps), big(d10.moves), big(ok.extra), STAB.get(a, "no")]


def tab_C():
    def half(conds):
        L = ["\\begin{tabular}{@{}l@{\\,}lrrrrrrl@{}}", "\\toprule",
             " & Contender & $t_{10k}$ & $t_{100k}$ & $t_{285k}$ & comp$_{10k}$ & mov$_{10k}$ & extra & st.\\\\", "\\midrule"]
        for c in conds:
            # bold the fastest at full n (or largest n that someone finished)
            for i, a in enumerate(ALGOS):
                r = row(c, a)
                L.append((f"\\multirow{{5}}{{*}}{{{c}}}" if i == 0 else "") + f" & {a.replace(' Sort','')} & " + " & ".join(r) + "\\\\")
            L.append("\\midrule" if c != conds[-1] else "\\bottomrule")
        L.append("\\end{tabular}")
        return "\n".join(L)
    s = "{\\fontsize{7.6}{8.8}\\selectfont\\setlength{\\tabcolsep}{2.2pt}\n" + half(["C1", "C2", "C3"]) + "\\hfill\n" + half(["C4", "C5", "C6"]) + "}\n"
    open("out/tab_C.tex", "w").write(s)


def tab_D():
    D = R[R.part == "D"].copy(); D["K"] = D.K.astype(int); D["n"] = D.n.astype(int)
    names = ["Full sort (Merge Sort) + first K", "size-K heap", "bounded insertion buffer"]
    L = ["{\\fontsize{7.8}{9}\\selectfont\\setlength{\\tabcolsep}{3pt}",
         "\\begin{tabular}{@{}rr|rrr|rrr@{}}", "\\toprule",
         "& & \\multicolumn{3}{c|}{median time (s), C2 Shuffled} & \\multicolumn{3}{c}{comparisons, C2}\\\\",
         "$n$ & $K$ & full sort & size-K heap & buffer & full sort & size-K heap & buffer\\\\", "\\midrule"]
    for n in config.D_SIZES:
        for K in sorted(D[(D.n == n)].K.unique()):
            g = D[(D.n == n) & (D.K == K) & (D.condition == "C2")]
            if len(g) < 3:
                continue
            ts, cs = [], []
            for m in names:
                x = g[g.algo == m].iloc[0]
                ts.append(float(x.median_s) if x.status == "ok" else None)
                cs.append(x.comps)
            best = min(v for v in ts if v is not None)
            tt = [("\\textbf{%s}" % t(v)) if v == best else (t(v) if v is not None else "DNF") for v in ts]
            L.append(f"{n:,} & {K:,} & " + " & ".join(tt) + " & " + " & ".join(big(c) for c in cs) + "\\\\")
        L.append("\\midrule" if n != config.D_SIZES[-1] else "\\bottomrule")
    L += ["\\end{tabular}}"]
    open("out/tab_D.tex", "w").write("\n".join(L))


if __name__ == "__main__":
    tab_C()
    try:
        tab_D()
    except Exception as e:
        print("skip D", e)
