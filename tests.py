"""Problem B correctness tests.  Run:  python -m unittest tests -v

Reference = Python's sorted() (allowed for verification only). Because the
triage order is total, outputs must be IDENTICAL to the reference.
The full-size check on every condition x size happens inside run.py (column
`correct` in results.csv); here we cover every condition at n = 1,000 and the
edge cases the brief lists.
"""
import random
import unittest

import config
from algos import (insertion_sort, merge_sort, naive_quick_sort, hardened_quick_sort,
                   heap_sort, topk_heap, topk_buffer, merge_topk, LiveHeap, count_inversions)

SORTS = {
    "Insertion Sort": insertion_sort,
    "Merge Sort": merge_sort,
    "Naive Quick Sort": naive_quick_sort,
    "Hardened Quick Sort": lambda a: hardened_quick_sort(a, seed=config.S),
    "Heap Sort": heap_sort,
}
TOPK = {"size-K heap": topk_heap, "bounded insertion buffer": topk_buffer}

rng = random.Random(config.S)
EDGE = {
    "empty": [],
    "single record": [42],
    "two reversed": [2, 1],
    "all-equal keys": [7] * 500,
    "duplicate-heavy": [rng.randint(0, 4) for _ in range(2000)],
    "sorted": list(range(1000)),
    "reversed": list(range(1000, 0, -1)),
    "random distinct": rng.sample(range(10 ** 9), 1500),
    "big 64-bit keys": [rng.randint(0, 2 ** 62) for _ in range(1000)],
}


class Tagged:
    """Key + original position; compares on key only -> lets us observe stability."""
    __slots__ = ("k", "pos")

    def __init__(self, k, pos): self.k, self.pos = k, pos
    def __lt__(self, o): return self.k < o.k
    def __gt__(self, o): return self.k > o.k
    def __le__(self, o): return self.k <= o.k


class TestSorts(unittest.TestCase):
    def test_edge_cases(self):
        for name, f in SORTS.items():
            for case, a in EDGE.items():
                with self.subTest(algo=name, case=case):
                    before = list(a)
                    out, st = f(a)
                    self.assertEqual(out, sorted(a))
                    self.assertEqual(a, before, "input must not be modified")

    def test_every_condition_n1000(self):
        import data
        df = data.load()
        sub = data.sample_rows(df, 1000)
        for cond in config.CONDITIONS:
            a = data.build(sub, cond)
            ref = sorted(a)
            for name, f in SORTS.items():
                with self.subTest(algo=name, cond=cond):
                    self.assertEqual(f(a)[0], ref)

    def test_stability(self):
        """Merge and Insertion must keep equal keys in input order; we record what the others do."""
        a = [Tagged(rng.randint(0, 9), i) for i in range(3000)]
        expected = [(t.k, t.pos) for t in sorted(a, key=lambda t: t.k)]   # sorted() is stable
        result = {}
        for name, f in SORTS.items():
            out, _ = f(a)
            result[name] = [(t.k, t.pos) for t in out] == expected
        self.assertTrue(result["Merge Sort"])
        self.assertTrue(result["Insertion Sort"])
        self.assertFalse(result["Naive Quick Sort"])
        self.assertFalse(result["Hardened Quick Sort"])
        self.assertFalse(result["Heap Sort"])

    def test_counts_insertion_exact(self):
        """moves = I + (n-1) exactly (M1)."""
        a = EDGE["random distinct"]
        _, st = insertion_sort(a)
        self.assertEqual(st.moves, count_inversions(a) + len(a) - 1)

    def test_inversions(self):
        a = [rng.randint(0, 50) for _ in range(400)]
        brute = sum(1 for i in range(len(a)) for j in range(i + 1, len(a)) if a[i] > a[j])
        self.assertEqual(count_inversions(a), brute)


class TestTopK(unittest.TestCase):
    def test_topk_all_k(self):
        for name, f in TOPK.items():
            for case, a in EDGE.items():
                for k in (0, 1, 10, config.K, 500, len(a), len(a) + 5):
                    with self.subTest(m=name, case=case, k=k):
                        self.assertEqual(f(a, k)[0], sorted(a)[:max(k, 0)])

    def test_merge_topk(self):
        a, b = sorted(rng.sample(range(10 ** 6), 300)), sorted(rng.sample(range(10 ** 6), 50))
        for k in (0, 1, 100, 400):
            self.assertEqual(merge_topk(a, b, k)[0], sorted(a + b)[:k])

    def test_live_heap(self):
        h, seen = LiveHeap(config.K), []
        for _ in range(20):
            w = [rng.randint(0, 10 ** 6) for _ in range(rng.randint(0, 300))]
            h.feed(w); seen += w
            self.assertEqual(h.publish(), sorted(seen)[:config.K])


if __name__ == "__main__":
    unittest.main()
