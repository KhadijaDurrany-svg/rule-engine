import pytest

from rulekiln.stats import (
    bootstrap_ci,
    mean,
    paired_permutation_pvalue,
    two_sample_permutation_pvalue,
)


def test_mean_basic():
    assert mean([1.0, 2.0, 3.0]) == 2.0


def test_mean_empty_raises():
    with pytest.raises(ValueError):
        mean([])


def test_bootstrap_ci_brackets_mean():
    data = [10.0] * 50
    lo, hi = bootstrap_ci(data, n_resamples=500, seed=1)
    assert lo == hi == 10.0  # zero-variance data


def test_bootstrap_ci_ordered_and_contains_sample_mean():
    data = [float(i) for i in range(100)]
    lo, hi = bootstrap_ci(data, n_resamples=2000, seed=3)
    m = mean(data)
    assert lo <= m <= hi
    assert lo < hi


def test_bootstrap_requires_two_points():
    with pytest.raises(ValueError):
        bootstrap_ci([1.0], n_resamples=10)


def test_paired_permutation_detects_real_difference():
    diffs = [5.0, 6.0, 4.5, 5.5, 6.2, 4.8, 5.1, 5.9]  # clearly positive
    p = paired_permutation_pvalue(diffs, n_perm=2000, seed=0)
    assert p < 0.05


def test_paired_permutation_null_is_large():
    diffs = [1.0, -1.0, 1.0, -1.0, 1.0, -1.0]  # symmetric, no effect
    p = paired_permutation_pvalue(diffs, n_perm=2000, seed=0)
    assert p > 0.2


def test_paired_permutation_in_unit_interval():
    p = paired_permutation_pvalue([0.3, -0.1, 0.2], n_perm=500, seed=5)
    assert 0.0 <= p <= 1.0


def test_two_sample_permutation_detects_difference():
    a = [1.0, 1.1, 0.9, 1.0]
    b = [5.0, 5.1, 4.9, 5.0]
    assert two_sample_permutation_pvalue(a, b, n_perm=2000, seed=0) < 0.05


def test_two_sample_permutation_null():
    a = [1.0, 2.0, 3.0, 4.0]
    b = [1.0, 2.0, 3.0, 4.0]
    assert two_sample_permutation_pvalue(a, b, n_perm=1000, seed=0) > 0.2


def test_bootstrap_is_seed_reproducible():
    data = [float(i % 7) for i in range(40)]
    assert bootstrap_ci(data, 1000, seed=11) == bootstrap_ci(data, 1000, seed=11)
