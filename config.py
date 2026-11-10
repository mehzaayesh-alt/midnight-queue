"""All experiment settings (seed, K, sizes, conditions, reps, DNF limit, windows)."""
ROLL = "24i-2573"
S = 242573                      # roll number, digits only -> the seed for EVERYTHING
K = 25 + (S % 226)              # personal shift capacity  (= 100)

CSV = "creditcard.csv"          # put the Kaggle file next to the code

SIZES = [1_000, 10_000, 100_000, 284_807]
CONDITIONS = ["C1", "C2", "C3", "C4", "C5", "C6"]
DISPLACE_FRAC = 0.01            # C5: share of records moved to random positions

REPS = 5                        # timed runs per cell, report the median
DNF_SECONDS = 300               # 5-minute rule for a single run

# Problem D
D_SIZES = [100_000, 284_807]
D_CONDITIONS = ["C1", "C2"]
D_KS = [10, 50, K, 500, 5_000, "n/10"]

# Problem E (window length in seconds of the Time column)
E_WINDOWS = [3600, 600]
E_REPS = 3                      # live feed: median of 3 runs (10-minute re-ranking is slow)

RESULTS = "results.csv"
