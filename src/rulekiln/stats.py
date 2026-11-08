"""Small, self-contained statistics: bootstrap CIs and permutation tests.

Everything here is implemented in pure Python with the standard library. The
package has no required third-party runtime dependency; NumPy is not needed and
is not imported here.
"""

from __future__ import annotations

import random
from collections.abc import Sequence


def mean(xs: Sequence[float]) -> float:
    if not xs:
        raise ValueError("mean of empty sequence")
    return sum(xs) / len(xs)


def bootstrap_ci(
    data: Sequence[float],
    n_resamples: int = 10_000,
    confidence: float = 0.95,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile bootstrap CI for the mean of ``data``.

    Returns ``(low, high)`` at the given two-sided confidence level. Resampling
    is seeded for reproducibility.
    """
    if len(data) < 2:
        raise ValueError("bootstrap needs at least 2 observations")
    alpha = (1.0 - confidence) / 2.0
    n = len(data)
    rng = random.Random(seed)
    means = [mean([data[rng.randrange(n)] for _ in range(n)]) for _ in range(n_resamples)]
    means.sort()
    lo = means[int(alpha * n_resamples)]
    hi = means[min(n_resamples - 1, int((1 - alpha) * n_resamples))]
    return lo, hi


def paired_permutation_pvalue(
    diffs: Sequence[float],
    n_perm: int = 10_000,
    seed: int = 0,
) -> float:
    """Two-sided paired permutation (sign-flip) test that mean(diffs) == 0.

    For paired data, the exchangeability under H0 is the sign of each paired
    difference. We randomly flip signs ``n_perm`` times and measure how often the
    permuted absolute mean is at least the observed absolute mean. The returned
    p-value uses the standard ``(hits + 1) / (n_perm + 1)`` correction so it is
    never exactly zero.
    """
    if not diffs:
        raise ValueError("need at least one paired difference")
    observed = abs(mean(diffs))
    rng = random.Random(seed)
    hits = 0
    for _ in range(n_perm):
        flipped = mean([d if rng.random() < 0.5 else -d for d in diffs])
        if abs(flipped) >= observed - 1e-12:
            hits += 1
    return (hits + 1) / (n_perm + 1)


def two_sample_permutation_pvalue(
    a: Sequence[float],
    b: Sequence[float],
    n_perm: int = 10_000,
    seed: int = 0,
) -> float:
    """Two-sided permutation test that mean(a) == mean(b) by label shuffling."""
    if not a or not b:
        raise ValueError("both samples must be non-empty")
    observed = abs(mean(a) - mean(b))
    pool = list(a) + list(b)
    na = len(a)
    rng = random.Random(seed)
    hits = 0
    for _ in range(n_perm):
        rng.shuffle(pool)
        diff = abs(mean(pool[:na]) - mean(pool[na:]))
        if diff >= observed - 1e-12:
            hits += 1
    return (hits + 1) / (n_perm + 1)
