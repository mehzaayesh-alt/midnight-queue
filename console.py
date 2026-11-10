"""Bonus: The Analyst Console.   python console.py   then open http://localhost:8000

A tiny local web page (standard library only) that runs MY contenders from
algos.py on the real data. Choose the algorithm that builds the queue, set K,
the input condition and n; see the top K (risk band, Amount, Time) plus the
running time, comparisons and moves of every run in a history table.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from time import perf_counter
from urllib.parse import urlparse, parse_qs

import config, data
from algos import (DNF, insertion_sort, merge_sort, naive_quick_sort, hardened_quick_sort,
                   heap_sort, topk_heap, topk_buffer)

LIMIT_S = 30          # interactive DNF limit (the experiments use 300 s)

METHODS = {
    "size-K heap":              lambda a, K, d: topk_heap(a, K, deadline=d),
    "bounded insertion buffer": lambda a, K, d: topk_buffer(a, K, deadline=d),
    "Merge Sort (full) + first K":          lambda a, K, d: _full(merge_sort(a, deadline=d), K),
    "Heap Sort (full) + first K":           lambda a, K, d: _full(heap_sort(a, deadline=d), K),
    "Hardened Quick Sort (full) + first K": lambda a, K, d: _full(hardened_quick_sort(a, seed=config.S, deadline=d), K),
    "Naive Quick Sort (full) + first K":    lambda a, K, d: _full(naive_quick_sort(a, deadline=d), K),
    "Insertion Sort (full) + first K":      lambda a, K, d: _full(insertion_sort(a, deadline=d), K),
}


def _full(res, K):
    out, st = res
    return out[:K], st


print("loading data ...", flush=True)
DF = data.load()
REC = {int(k): (int(t), int(b), float(am), int(tm), float(r))
       for k, t, b, am, tm, r in zip(DF["key"], DF["txn_id"], DF["band"], DF["Amount"], DF["t"], DF["risk"])}
CACHE = {}


def inputs(cond, n):
    if (cond, n) not in CACHE:
        CACHE[(cond, n)] = data.build(data.sample_rows(DF, n), cond)
    return CACHE[(cond, n)]


def run(method, K, cond, n):
    base = inputs(cond, n)
    a = list(base)                                   # fresh copy
    t0 = perf_counter()
    try:
        top, st = METHODS[method](a, K, t0 + LIMIT_S)
    except DNF:
        return {"status": f"DNF (> {LIMIT_S} s)", "method": method, "K": K, "cond": cond, "n": n}
    ms = (perf_counter() - t0) * 1000
    ok = top == sorted(base)[:K]                     # reference check only
    rows = [dict(zip(["txn_id", "band", "amount", "time", "risk"], REC[k])) for k in top]
    return {"status": "ok", "method": method, "K": K, "cond": cond, "n": n, "ms": round(ms, 2),
            "comps": st.comps, "moves": st.moves, "extra": st.peak_extra, "correct": ok, "rows": rows}


PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><title>Analyst Console</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--bg:#fcfcfb;--ink:#0b0b0b;--mut:#52514e;--line:#e4e3df;--acc:#2a78d6;--bad:#e34948;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#1a1a19;--ink:#f0efec;--mut:#c3c2b7;--line:#33332f;--acc:#3987e5;--bad:#e66767;--card:#222220}}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,sans-serif}
main{max-width:1100px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:0 0 2px}.sub{color:var(--mut);margin:0 0 14px}
form{display:flex;flex-wrap:wrap;gap:10px;align-items:end;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}
label{display:flex;flex-direction:column;font-size:12px;color:var(--mut);gap:3px}
select,input{font:inherit;padding:5px 7px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink)}
button{font:inherit;padding:6px 14px;border:0;border-radius:6px;background:var(--acc);color:#fff;cursor:pointer}
button.sec{background:transparent;color:var(--acc);border:1px solid var(--acc)}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 12px;min-width:120px}
.stat b{display:block;font-size:20px}.stat span{font-size:12px;color:var(--mut)}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{padding:4px 8px;border-bottom:1px solid var(--line);text-align:right}th{color:var(--mut);font-weight:600;font-size:12px}
td.l,th.l{text-align:left;white-space:nowrap}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media (max-width:800px){.grid{grid-template-columns:1fr}}
.box{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px;overflow:auto;max-height:560px}
h2{font-size:15px;margin:0 0 6px}.dnf{color:var(--bad);font-weight:600}
</style></head><body><main>
<h1>Analyst Console: The Midnight Queue</h1>
<p class="sub">24i-2573 · runs my own contenders from <code>algos.py</code> on creditcard.csv · K defaults to my shift capacity (100) · DNF limit 30 s</p>
<form id="f">
<label>Algorithm that builds the queue<select name="method" id="method"></select></label>
<label>K (cases)<input name="K" type="number" min="1" value="100" style="width:90px"></label>
<label>Input condition<select name="cond">
<option value="C2">C2 Shuffled</option><option value="C1">C1 Arrival</option><option value="C3">C3 Pre-ranked</option>
<option value="C4">C4 Reverse-ranked</option><option value="C5">C5 Nearly ranked</option></select></label>
<label>n (records)<select name="n"><option>1000</option><option>10000</option><option selected>100000</option><option>284807</option></select></label>
<button>Build queue</button><button type="button" class="sec" id="all">Run all algorithms</button>
</form>
<div class="stats" id="stats"></div>
<div class="grid">
<div class="box"><h2>Top K queue</h2><table id="q"><thead><tr><th>#</th><th>txn_id</th><th>band</th><th>Amount</th><th>Time (s)</th><th>risk</th></tr></thead><tbody></tbody></table></div>
<div class="box"><h2>Run history (compare algorithms)</h2><table id="h"><thead><tr><th class="l">algorithm</th><th>K</th><th>cond</th><th>n</th><th>time (ms)</th><th>comparisons</th><th>moves</th><th>extra</th></tr></thead><tbody></tbody></table></div>
</div></main>
<script>
const M = __METHODS__;
const sel = document.getElementById('method');
M.forEach(m => sel.add(new Option(m, m)));
const fmt = x => x.toLocaleString();
async function go(params){
  const r = await fetch('/run?' + new URLSearchParams(params)); const d = await r.json();
  const h = document.querySelector('#h tbody'); const tr = h.insertRow(0);
  if (d.status !== 'ok'){
    tr.innerHTML = `<td class="l">${d.method}</td><td>${d.K}</td><td>${d.cond}</td><td>${fmt(d.n)}</td><td class="dnf" colspan="4">${d.status}</td>`;
    return d;
  }
  tr.innerHTML = `<td class="l">${d.method}</td><td>${d.K}</td><td>${d.cond}</td><td>${fmt(d.n)}</td><td>${d.ms}</td><td>${fmt(d.comps)}</td><td>${fmt(d.moves)}</td><td>${fmt(d.extra)}</td>`;
  return d;
}
function show(d){
  const s = document.getElementById('stats');
  if (d.status !== 'ok'){ s.innerHTML = `<div class="stat"><b class="dnf">${d.status}</b><span>${d.method}</span></div>`; return; }
  s.innerHTML = [['Running time', d.ms + ' ms'], ['Comparisons', fmt(d.comps)], ['Moves', fmt(d.moves)],
                 ['Peak extra slots', fmt(d.extra)], ['Matches reference', d.correct ? 'yes' : 'NO']]
     .map(([k, v]) => `<div class="stat"><b>${v}</b><span>${k}</span></div>`).join('');
  document.querySelector('#q tbody').innerHTML = d.rows.map((r, i) =>
     `<tr><td>${i + 1}</td><td>${r.txn_id}</td><td>${r.band}</td><td>${r.amount.toFixed(2)}</td><td>${fmt(r.time)}</td><td>${r.risk.toFixed(1)}</td></tr>`).join('');
}
document.getElementById('f').onsubmit = async e => { e.preventDefault(); show(await go(Object.fromEntries(new FormData(e.target)))); };
document.getElementById('all').onclick = async () => {
  const p = Object.fromEntries(new FormData(document.getElementById('f')));
  let last; for (const m of M){ last = await go({...p, method: m}); if (last.status === 'ok') show(last); }
};
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/run":
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            n = min(int(q.get("n", 100000)), len(DF))
            res = run(q.get("method", "size-K heap"), max(1, int(q.get("K", config.K))), q.get("cond", "C2"), n)
            body, ctype = json.dumps(res).encode(), "application/json"
        else:
            body, ctype = PAGE.replace("__METHODS__", json.dumps(list(METHODS))).encode(), "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("Analyst Console on http://localhost:8000  (Ctrl+C to stop)")
    HTTPServer(("127.0.0.1", 8000), H).serve_forever()
