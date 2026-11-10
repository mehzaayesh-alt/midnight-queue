# The Midnight Queue: Ranking Suspicious Transactions at Scale

An empirical and theoretical comparison of hand-written sorting and top-K algorithms on **284,807 real credit-card transactions**, built for a Design & Analysis of Algorithms course (Assignment 2).

A fraud team can only review **K = 100** cases per night. Every transaction gets a risk score, and the question is which algorithm should build that queue:
1. **overnight**, ranking a whole day;
2. **per shift**, when only the top K are needed;
3. **live**, refreshing the top K as new transactions arrive.

Everything is implemented from scratch in Python, with no built-in sort inside any contender. Each algorithm is measured on time, comparisons, moves and extra memory, and the measurements are checked against the theory.

---

## Highlights

| Question | Answer from the data |
|---|---|
| Best overnight sort | **Merge Sort**: fastest or tied-fastest on 4 of 6 input orders, never slower than 1.31 s at n = 284,807, stable |
| Best for the top 100 | **Size-K heap**: 0.03 s vs 1.05 s for a full sort (**35× faster**) |
| Best live strategy | **Persistent size-K heap**: 0.03 s for 48 h of data vs 29 s to re-rank, using 200 memory slots vs 712k |
| Where theory meets measurement | Merge Sort comparisons: **4,804,255 measured** vs 4,804,587 predicted (n log₂n − 1.25n). Naive Quick Sort on tie-heavy input: **1,593,506,374 measured** vs 1,593,315,772 predicted (Σ m(m−1)/2) |
| Surprise finding | The top 100 by this ranking rule contain **0 of the 492 frauds**: big legitimate payments outrank small frauds. Catching half the frauds needs K = 2,068 |

## What's compared

**Five full sorts:** Insertion Sort, Merge Sort, Naive Quick Sort (last pivot, Lomuto), Hardened Quick Sort (random pivot + three-way partition) and Heap Sort.

**Top-K:** full sort then slice, a size-K heap, and a bounded insertion buffer.

**Live feed** (1-hour and 10-minute windows): re-rank everything, a persistent size-K heap, or sort each window and merge.

**Six input orders**, each at n = 1k, 10k, 100k and 284,807:

| | Input order | Winner | Fails (5-min limit) |
|---|---|---|---|
| C1 | Arrival (by time) | Merge Sort | Insertion |
| C2 | Shuffled | Merge ≈ Naive Quick | Insertion |
| C3 | Already ranked | **Insertion** (n−1 comparisons) | Naive Quick |
| C4 | Reverse ranked | Merge Sort | Insertion, Naive Quick |
| C5 | Nearly ranked (1% moved) | Merge Sort | – (Insertion takes 68 s) |
| C6 | Band-only key (8 values, heavy ties) | **Hardened Quick** | Insertion, Naive Quick |

## Figures

| | |
|---|---|
| ![Time vs n](figures/time_vs_n.png) | ![Counts](figures/counts_and_normalised.png) |
| ![Top-K and fraud capture](figures/top_k_and_fraud_capture.png) | ![Live feed](figures/live_feed.png) |

More in [`figures/`](figures/), and the full write-up (with derivations) in [`report/report.pdf`](report/report.pdf).

## Run it

**Easiest: the notebook.** Open [`notebook/midnight_queue.ipynb`](notebook/midnight_queue.ipynb) in Google Colab and choose **Runtime → Run all**. It downloads the dataset itself through `kagglehub`. `QUICK = True` runs every experiment at small sizes in a few minutes; `QUICK = False` runs the full study, which takes hours.

**Scripts:**
```bash
pip install -r requirements.txt
# download creditcard.csv from https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud into src/
cd src
python -m unittest tests -v     # correctness: every sort vs Python's sorted(), edge cases, stability
python profile_data.py          # data profile
python run.py C                 # sorting tournament  (also: D = top-K, E = live feed, M = math checks)
python plots.py                 # figures -> src/out/
```
Every setting (sizes, K, repetitions, time limit, windows) is in `src/config.py`.

**Interactive console:** open [`console/console.html`](console/console.html) in a browser. It's self-contained, with no server or install. Pick an algorithm, K, input order and n, then compare running time, comparisons and moves side by side.

## Repository layout

```
src/        algorithms (algos.py), data pipeline, timing harness, tests, plots
notebook/   single self-contained Colab notebook (code + results + figures)
console/    interactive browser console (bonus)
figures/    result figures
data/       results.csv: every measurement (median of 5 runs)
report/     5-page written report with derivations
```

## Method notes

- **Risk score:** sum of squared z-scores of the 28 PCA features. **Band** = ⌊log₂ risk⌋, clipped to 0–9.
- **Triage order:** band ↓, Amount ↓, Time ↑, id ↑, packed into one exact 64-bit integer, so every comparison is a single `<`.
- **Counting:** a comparison is one key-vs-key test; a move is one write into a list slot (a swap = 2).
- **Timing:** `perf_counter`, a fresh copy of the input per run, median of 5 runs. A single run over 5 minutes is recorded as DNF.
- The fraud label (`Class`) is used **only for evaluation**, never for ranking.

## Data

[Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud), Machine Learning Group, ULB. It isn't included in this repo (150 MB); the notebook downloads it automatically.

## Acknowledgements

Built for a Design & Analysis of Algorithms course. The sorting algorithms are my own implementations. Claude (Anthropic) helped with the measurement harness, plotting, the notebook, the console and drafting the report.
