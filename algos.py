"""Hand-written contenders for The Midnight Queue. No built-in sort inside.

Elements are integer keys (smaller key = earlier in the triage queue), so every
comparison is one `<` on two ints.

COUNTING DEFINITION (as stated in the report)
  comparison : one evaluation of a `<` / `<=` between two KEYS. Index/loop
               tests (i < n, lo < hi) are not counted.
  move       : one write of a key into a list slot (the array or any auxiliary
               list). A swap = 2 moves. Reading is free.

Every sort returns (sorted_list, Stats). `deadline` (a perf_counter value) makes
a run raise DNF so the harness can apply the 5-minute rule.
"""
import random
from time import perf_counter


class DNF(Exception):
    pass


class Stats:
    __slots__ = ("comps", "moves", "peak_extra")

    def __init__(self, comps=0, moves=0, peak_extra=0):
        self.comps, self.moves, self.peak_extra = comps, moves, peak_extra

    def __repr__(self):
        return f"Stats(comps={self.comps}, moves={self.moves}, extra={self.peak_extra})"


def _check(deadline):
    if deadline is not None and perf_counter() > deadline:
        raise DNF


# ----------------------------------------------------------------- insertion
def insertion_sort(a, deadline=None):
    a = list(a)
    c = m = 0
    for i in range(1, len(a)):
        if not i & 1023:
            _check(deadline)
        x = a[i]
        j = i - 1
        while j >= 0:
            c += 1
            if a[j] > x:
                a[j + 1] = a[j]; m += 1
                j -= 1
            else:
                break
        a[j + 1] = x; m += 1
    return a, Stats(c, m, 0)


# --------------------------------------------------------------------- merge
def merge_sort(a, deadline=None):
    a = list(a)
    n = len(a)
    st = Stats(0, 0, n // 2 + 1 if n > 1 else 0)   # one aux buffer, copy of left half
    aux = [0] * (n // 2 + 1)

    def rec(lo, hi):                                # sorts a[lo:hi]
        if hi - lo < 2:
            return
        mid = (lo + hi) // 2
        rec(lo, mid); rec(mid, hi)
        _check(deadline)
        L = mid - lo
        aux[:L] = a[lo:mid]; st.moves += L          # copy left run out
        i, j, k = 0, mid, lo
        c = 0
        while i < L and j < hi:
            c += 1
            if a[j] < aux[i]:                       # strict: left wins ties -> stable
                a[k] = a[j]; j += 1
            else:
                a[k] = aux[i]; i += 1
            k += 1
        st.comps += c
        st.moves += k - lo                          # writes made in the loop
        while i < L:
            a[k] = aux[i]; i += 1; k += 1; st.moves += 1
        # leftover right run is already in place

    rec(0, n)
    return a, st


# --------------------------------------------------------------------- quick
def quick_sort(a, pivot="last", partition="lomuto", seed=None, deadline=None):
    """One routine, three knobs.

      naive     : pivot='last',    partition='lomuto'
      hardened  : pivot='random' | 'median3',  partition='lomuto' | 'three_way'

    Iterative (explicit stack) so Python's recursion limit cannot kill it on
    sorted / reversed / tie-heavy input. Stack growth is recorded as peak_extra.
    """
    a = list(a)
    rng = random.Random(seed)
    st = Stats()
    stack = [(0, len(a) - 1)]
    peak = 1
    while stack:
        lo, hi = stack.pop()
        if lo >= hi:
            continue
        _check(deadline)
        # ---- choose pivot, put it where the partition expects it
        if pivot == "last":
            pass
        elif pivot == "random":
            p = rng.randint(lo, hi)
            a[p], a[hi] = a[hi], a[p]; st.moves += 2
        elif pivot == "median3":
            mid = (lo + hi) // 2
            x, y, z = a[lo], a[mid], a[hi]
            st.comps += 3
            if x < y:
                p = mid if y < z else (hi if x < z else lo)
            else:
                p = lo if x < z else (hi if y < z else mid)
            a[p], a[hi] = a[hi], a[p]; st.moves += 2
        else:
            raise ValueError(pivot)
        x = a[hi]
        # ---- partition
        if partition == "lomuto":
            i = lo - 1
            c = 0
            for j in range(lo, hi):
                c += 1
                if a[j] <= x:
                    i += 1
                    a[i], a[j] = a[j], a[i]; st.moves += 2
            st.comps += c
            a[i + 1], a[hi] = a[hi], a[i + 1]; st.moves += 2
            q = i + 1
            parts = ((lo, q - 1), (q + 1, hi))
        elif partition == "three_way":              # Dijkstra: < x | == x | > x
            lt, i, gt = lo, lo, hi
            while i <= gt:
                v = a[i]
                st.comps += 1
                if v < x:
                    a[lt], a[i] = a[i], a[lt]; st.moves += 2
                    lt += 1; i += 1
                else:
                    st.comps += 1
                    if x < v:
                        a[i], a[gt] = a[gt], a[i]; st.moves += 2
                        gt -= 1
                    else:
                        i += 1
            parts = ((lo, lt - 1), (gt + 1, hi))
        else:
            raise ValueError(partition)
        # push the larger side first so the smaller is handled next (O(log n) stack)
        (l1, h1), (l2, h2) = parts
        if (h1 - l1) < (h2 - l2):
            stack.append((l2, h2)); stack.append((l1, h1))
        else:
            stack.append((l1, h1)); stack.append((l2, h2))
        peak = max(peak, len(stack))
    st.peak_extra = peak
    return a, st


def naive_quick_sort(a, deadline=None):
    return quick_sort(a, "last", "lomuto", None, deadline)


def hardened_quick_sort(a, seed=None, deadline=None):
    """Hardened variant: random pivot + three-way (Dijkstra) partition."""
    return quick_sort(a, "random", "three_way", seed, deadline)


# ---------------------------------------------------------------------- heap
def _sift_down(a, i, n, st):
    """Max-heap sift-down on a[0:n]; the slide's MAX-HEAPIFY, made iterative."""
    x = a[i]
    c = m = 0
    while True:
        l = 2 * i + 1
        if l >= n:
            break
        r = l + 1
        if r < n:
            c += 1
            big = r if a[l] < a[r] else l
        else:
            big = l
        c += 1
        if x < a[big]:
            a[i] = a[big]; m += 1
            i = big
        else:
            break
    a[i] = x; m += 1
    st.comps += c; st.moves += m


def heap_sort(a, deadline=None):
    a = list(a)
    n = len(a)
    st = Stats()
    for i in range(n // 2 - 1, -1, -1):             # BUILD-MAX-HEAP, O(n)
        _sift_down(a, i, n, st)
    for end in range(n - 1, 0, -1):
        if not end & 1023:
            _check(deadline)
        a[0], a[end] = a[end], a[0]; st.moves += 2
        _sift_down(a, 0, end, st)
    return a, st


# --------------------------------------------------------------------- top-K
def topk_heap(a, k, deadline=None):
    """Best K (smallest keys) using a size-K heap whose root is the WORST kept key.

    In 'priority' terms (bigger = more urgent) this is the size-K MIN-heap the
    brief asks for; with our keys (smaller = more urgent) the same structure is
    stored as a max-heap on key. Returns the K keys in triage order.
    """
    st = Stats()
    n = len(a)
    k = min(k, n)
    if k <= 0:
        return [], st
    h = list(a[:k]); st.moves += k
    for i in range(k // 2 - 1, -1, -1):
        _sift_down(h, i, k, st)
    for idx in range(k, n):
        if not idx & 4095:
            _check(deadline)
        st.comps += 1
        if a[idx] < h[0]:                           # beats the weakest kept case
            h[0] = a[idx]; st.moves += 1
            _sift_down(h, 0, k, st)
    out, s2 = heap_sort(h)                          # order just the K survivors
    st.comps += s2.comps; st.moves += s2.moves
    st.peak_extra = k
    return out, st


def topk_buffer(a, k, deadline=None):
    """Best K using a sorted buffer of size K (insertion into the buffer)."""
    st = Stats()
    n = len(a)
    k = min(k, n)
    if k <= 0:
        return [], st
    buf = []
    c = m = 0
    for idx in range(n):
        if not idx & 4095:
            _check(deadline)
        x = a[idx]
        if len(buf) == k:
            c += 1
            if not x < buf[-1]:                     # not better than the worst kept
                continue
            buf.pop()
        buf.append(x)                               # make room at the tail
        j = len(buf) - 1
        while j > 0:
            c += 1
            if buf[j - 1] > x:
                buf[j] = buf[j - 1]; m += 1
                j -= 1
            else:
                break
        buf[j] = x; m += 1
    st.comps, st.moves, st.peak_extra = c, m, k
    return buf, st


# ------------------------------------------------------------- live-feed helpers
def merge_topk(a, b, k):
    """Merge two sorted lists, keep only the first k. Returns (list, Stats)."""
    st = Stats()
    out, i, j, c = [], 0, 0, 0
    la, lb = len(a), len(b)
    while len(out) < k and i < la and j < lb:
        c += 1
        if b[j] < a[i]:
            out.append(b[j]); j += 1
        else:
            out.append(a[i]); i += 1
    while len(out) < k and i < la:
        out.append(a[i]); i += 1
    while len(out) < k and j < lb:
        out.append(b[j]); j += 1
    st.comps, st.moves, st.peak_extra = c, len(out), len(out)
    return out, st


class LiveHeap:
    """Persistent size-K heap (root = worst kept key) for the live feed."""

    def __init__(self, k):
        self.k, self.h, self.st = k, [], Stats()

    def feed(self, keys):
        h, st, k = self.h, self.st, self.k
        if k <= 0:
            return
        for x in keys:
            if len(h) < k:
                h.append(x); st.moves += 1
                i = len(h) - 1
                while i > 0:
                    p = (i - 1) // 2
                    st.comps += 1
                    if h[p] < x:
                        h[i] = h[p]; st.moves += 1; i = p
                    else:
                        break
                h[i] = x; st.moves += 1
            else:
                st.comps += 1
                if x < h[0]:
                    h[0] = x; st.moves += 1
                    _sift_down(h, 0, k, st)

    def publish(self):
        out, s2 = heap_sort(self.h)
        self.st.comps += s2.comps; self.st.moves += s2.moves
        return out


# ------------------------------------------------------------ inversion counting
def count_inversions(a):
    """Number of pairs i<j with a[i] > a[j], by merge counting (O(n log n))."""
    a = list(a)
    n = len(a)
    aux = [0] * (n // 2 + 1)
    inv = 0

    def rec(lo, hi):
        nonlocal inv
        if hi - lo < 2:
            return
        mid = (lo + hi) // 2
        rec(lo, mid); rec(mid, hi)
        L = mid - lo
        aux[:L] = a[lo:mid]
        i, j, k = 0, mid, lo
        while i < L and j < hi:
            if a[j] < aux[i]:
                a[k] = a[j]; j += 1; inv += L - i
            else:
                a[k] = aux[i]; i += 1
            k += 1
        while i < L:
            a[k] = aux[i]; i += 1; k += 1

    rec(0, n)
    return inv