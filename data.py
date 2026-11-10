"""Loading, risk score, triage key and the six input conditions (Section 3).

NumPy/pandas are used ONLY here (loading + risk score), as the brief allows.
Nothing in this file sorts with a library: the triage key is an exact integer
packing, and C3/C4 are built with our own Merge Sort.
"""
import random
import numpy as np
import pandas as pd

import config
from algos import merge_sort


def load(path=config.CSV):
    df = pd.read_csv(path)
    df.insert(0, "txn_id", np.arange(1, len(df) + 1))          # row number from 1
    V = df[[f"V{i}" for i in range(1, 29)]].to_numpy()
    z = (V - V.mean(axis=0)) / V.std(axis=0)                    # population std over the full file
    df["risk"] = (z ** 2).sum(axis=1)
    df["band"] = np.clip(np.floor(np.log2(df["risk"])), 0, 9).astype(int)
    df["cents"] = np.round(df["Amount"] * 100).astype(np.int64)  # Amount has <= 2 decimals
    df["t"] = df["Time"].astype(np.int64)                         # Time is whole seconds
    df["key"] = triage_key(df)
    df["bkey"] = 9 - df["band"]                                   # C6: band only (desc)
    return df


def triage_key(df):
    """One int whose natural order IS the triage order:
    band desc, Amount desc, Time asc, txn_id asc  (mixed-radix packing).
    Max value ~1.3e18 < 2^63, so it is also a valid 64-bit int."""
    A = int(df["cents"].max()) + 1
    T = int(df["t"].max()) + 1
    N = int(df["txn_id"].max()) + 1
    k = (9 - df["band"].astype(object)) * A + (A - 1 - df["cents"].astype(object))
    k = k * T + df["t"].astype(object)
    k = k * N + df["txn_id"].astype(object)
    return k.astype(object)                                       # plain Python ints


def sample_rows(df, n, seed=config.S):
    """n rows uniformly without replacement, restored to Time (file) order."""
    if n >= len(df):
        return df
    chosen = np.zeros(len(df), dtype=bool)
    chosen[random.Random(seed).sample(range(len(df)), n)] = True
    return df[chosen]             # boolean mask keeps file (Time) order, no sorting needed


def build(df_n, cond, seed=config.S):
    """Return the list of int keys for one condition."""
    base = [int(x) for x in df_n["key"]]            # C1: file order = Time ascending
    if cond == "C1":
        return base
    if cond == "C2":
        a = base[:]
        random.Random(seed).shuffle(a)
        return a
    ranked, _ = merge_sort(base)                     # our own sort builds C3
    if cond == "C3":
        return ranked
    if cond == "C4":
        return ranked[::-1]
    if cond == "C5":
        a = ranked[:]
        rng = random.Random(seed)
        m = max(1, int(round(config.DISPLACE_FRAC * len(a))))
        picked = rng.sample(range(len(a)), m)
        moved = [a[i] for i in picked]
        keep = set(picked)
        a = [x for i, x in enumerate(a) if i not in keep]
        for x in moved:                              # re-insert each at a random position
            a.insert(rng.randint(0, len(a)), x)
        return a
    if cond == "C6":
        return [int(x) for x in df_n["bkey"]]        # C1 order, key = band only
    raise ValueError(cond)
