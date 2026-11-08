from rulekiln.benchmark import BenchmarkConfig, run_benchmark, run_correctness, run_quality


def _small() -> BenchmarkConfig:
    return BenchmarkConfig(
        correctness_bases=40,
        quality_bases=20,
        quality_random_trials=8,
        bootstrap_resamples=1000,
        permutation_resamples=1000,
    )


def test_correctness_full_agreement_on_small_run():
    res = run_correctness(_small())
    for name, r in res.items():
        assert r["agree"] == r["bases"], (name, r)


def test_quality_ordered_beats_baselines():
    q = run_quality(_small())
    # Priority-aware resolution reaches the goal with fewer firings on average.
    assert q["ordered_firings_mean"] < q["random_firings_mean"]
    assert q["ordered_firings_mean"] < q["unordered_firings_mean"]
    assert q["reduction_vs_random_mean"] > 0


def test_quality_ci_and_pvalue_sane():
    q = run_quality(_small())
    lo, hi = q["reduction_vs_random_ci95"]
    assert lo <= q["reduction_vs_random_mean"] <= hi
    assert lo > 0  # CI excludes zero -> significant improvement
    assert 0.0 <= q["reduction_vs_random_pvalue"] <= 1.0


def test_full_report_structure():
    report = run_benchmark(_small())
    assert report.dataset_checksum
    assert "quality" in report.__dict__
    assert set(report.correctness).issuperset({"unordered"})
    # dataset checksum is reproducible
    assert run_benchmark(_small()).dataset_checksum == report.dataset_checksum
