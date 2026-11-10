"""Problem A: know your data. Writes out/profile.json and prints a summary."""
import json, os
from collections import Counter
import numpy as np

import config, data
from algos import count_inversions, merge_sort


def runs_ascending(a):
    r = 1
    for i in range(1, len(a)):
        if a[i] < a[i - 1]:
            r += 1
    return r


def main():
    os.makedirs("out", exist_ok=True)
    df = data.load()
    n = len(df)
    P = {"n": n, "K": config.K}
    P["band_counts"] = {int(b): int(c) for b, c in Counter(df["band"]).items()}
    P["risk_min"], P["risk_median"], P["risk_max"] = (float(df.risk.min()), float(df.risk.median()), float(df.risk.max()))
    amt = Counter(df["cents"])
    P["distinct_amounts"] = len(amt)
    top10 = amt.most_common(10)
    P["top10_amounts"] = [(c / 100, k) for c, k in top10]
    P["top10_share"] = sum(k for _, k in top10) / n
    P["zero_amount"] = int(amt.get(0, 0))
    P["frauds"] = int(df.Class.sum())
    P["fraud_by_band"] = {int(b): int(c) for b, c in Counter(df.loc[df.Class == 1, "band"]).items()}
    P["fraud_rate_by_band"] = {b: P["fraud_by_band"].get(b, 0) / c for b, c in P["band_counts"].items()}

    keys = [int(x) for x in df["key"]]
    t = list(df["t"])
    P["time_nondecreasing"] = all(t[i] <= t[i + 1] for i in range(n - 1))
    P["distinct_times"] = len(set(t))
    P["inv_file_vs_triage"] = count_inversions(keys)
    P["inv_max"] = n * (n - 1) // 2
    P["asc_runs_triage"] = runs_ascending(keys)
    bk = [int(x) for x in df["bkey"]]
    P["inv_band_only"] = count_inversions(bk)
    cnt = Counter(bk)
    P["inv_band_random_expect"] = (n * n - sum(c * c for c in cnt.values())) / 4   # random order with ties
    P["ties_full_key"] = n - len(set(keys))   # 0 => total order
    # composite (band, Amount) ties, i.e. how often Time/txn_id is needed as a tie-break
    ba = Counter(zip(df["band"], df["cents"]))
    P["band_amount_tied_records"] = int(sum(c for c in ba.values() if c > 1))
    json.dump(P, open("out/profile.json", "w"), indent=1)
    for k, v in P.items():
        print(k, v)


if __name__ == "__main__":
    main()
