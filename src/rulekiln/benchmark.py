"""The benchmark harness.

Two measured experiments, both fully offline and seeded:

**Correctness (differential).** For many seeded random rule bases, run the
engine and the independent brute-force reference under the same strategy and
check they fire the *same activations in the same order* and end with the same
status. This is a differential test between two independent implementations of
one specification: agreement is the signal, a mismatch is a bug. 100% agreement
is the honest expected outcome and is reported as a raw count, not dressed up as
a performance score.

**Conflict-resolution quality.** On seeded goal-reachability scenarios, measure
*firings-to-goal* for the priority-aware default strategy versus two naive
baselines (random and definition-order). The paired per-scenario reduction is
summarised with a bootstrap 95% CI and a paired permutation p-value.

Nothing here is fabricated: every number is computed from a real run of the code
in this package.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import asdict, dataclass, field
from typing import Any

from .engine import Engine, Status
from .generators import goal_scenario, random_rule_base
from .reference import run_reference
from .stats import bootstrap_ci, mean, paired_permutation_pvalue
from .strategies import Priority, Recency, Specificity, Strategy, Unordered, default_strategy
from .strategies import Random as RandomStrategy

_NAMED: dict[str, Strategy] = {
    "priority": Priority(),
    "specificity": Specificity(),
    "recency": Recency(),
    "unordered": Unordered(),
    "priority+specificity+recency": default_strategy(),
}


@dataclass
class BenchmarkConfig:
    """All knobs for a reproducible benchmark run."""

    correctness_bases: int = 300
    correctness_seed: int = 1
    correctness_strategies: tuple[str, ...] = (
        "priority+specificity+recency",
        "specificity",
        "unordered",
    )
    quality_bases: int = 80
    quality_seed: int = 10_000
    quality_random_trials: int = 24
    bootstrap_resamples: int = 10_000
    permutation_resamples: int = 10_000


def run_correctness(cfg: BenchmarkConfig) -> dict[str, Any]:
    """Differential engine-vs-reference agreement across strategies."""
    per_strategy: dict[str, Any] = {}
    for sname in cfg.correctness_strategies:
        strat = _NAMED[sname]
        agree = 0
        mismatches: list[int] = []
        for i in range(cfg.correctness_bases):
            seed = cfg.correctness_seed + i
            rb = random_rule_base(seed)
            eng_res = Engine(strat).run(rb)
            ref_res = run_reference(rb, sname)
            same = (
                eng_res.status == ref_res.status
                and eng_res.fired_tokens() == ref_res.fired_tokens()
            )
            if same:
                agree += 1
            else:
                mismatches.append(seed)
        per_strategy[sname] = {
            "bases": cfg.correctness_bases,
            "agree": agree,
            "agreement_rate": agree / cfg.correctness_bases,
            "mismatch_seeds": mismatches[:10],
        }
    return per_strategy


def run_quality(cfg: BenchmarkConfig) -> dict[str, Any]:
    """Firings-to-goal: priority-aware default vs random and unordered baselines."""
    ordered: list[float] = []
    unordered: list[float] = []
    random_mean: list[float] = []
    chain_lens: list[int] = []

    for i in range(cfg.quality_bases):
        seed = cfg.quality_seed + i
        rb, goal = goal_scenario(seed)
        chain_lens.append(int(goal.get("id")))  # goal id == chain length

        o = Engine(default_strategy()).run(rb, goal=goal)
        u = Engine(Unordered()).run(rb, goal=goal)
        assert o.status == Status.GOAL and u.status == Status.GOAL
        ordered.append(o.fired)
        unordered.append(u.fired)

        trials: list[float] = []
        for t in range(cfg.quality_random_trials):
            rng = random.Random((seed << 8) ^ t)
            r = Engine(RandomStrategy(rng)).run(rb, goal=goal)
            assert r.status == Status.GOAL
            trials.append(r.fired)
        random_mean.append(mean(trials))

    diff_rand = [rm - o for rm, o in zip(random_mean, ordered, strict=True)]
    diff_unord = [u - o for u, o in zip(unordered, ordered, strict=True)]

    rand_wins = sum(1 for rm, o in zip(random_mean, ordered, strict=True) if o < rm)
    unord_wins = sum(1 for u, o in zip(unordered, ordered, strict=True) if o < u)

    return {
        "bases": cfg.quality_bases,
        "random_trials_per_base": cfg.quality_random_trials,
        "chain_len_mean": mean(chain_lens),
        "ordered_firings_mean": mean(ordered),
        "unordered_firings_mean": mean(unordered),
        "random_firings_mean": mean(random_mean),
        "reduction_vs_random_mean": mean(diff_rand),
        "reduction_vs_random_ci95": bootstrap_ci(
            diff_rand, cfg.bootstrap_resamples, 0.95, seed=cfg.quality_seed
        ),
        "reduction_vs_random_pvalue": paired_permutation_pvalue(
            diff_rand, cfg.permutation_resamples, seed=cfg.quality_seed
        ),
        "reduction_vs_unordered_mean": mean(diff_unord),
        "reduction_vs_unordered_ci95": bootstrap_ci(
            diff_unord, cfg.bootstrap_resamples, 0.95, seed=cfg.quality_seed + 1
        ),
        "reduction_vs_unordered_pvalue": paired_permutation_pvalue(
            diff_unord, cfg.permutation_resamples, seed=cfg.quality_seed + 1
        ),
        "ordered_beats_random_rate": rand_wins / cfg.quality_bases,
        "ordered_beats_unordered_rate": unord_wins / cfg.quality_bases,
    }


def _dataset_checksum(cfg: BenchmarkConfig) -> str:
    """Checksum of the exact rule bases the benchmark will consume."""
    h = hashlib.sha256()
    for i in range(cfg.correctness_bases):
        h.update(random_rule_base(cfg.correctness_seed + i).checksum().encode())
    for i in range(cfg.quality_bases):
        rb, goal = goal_scenario(cfg.quality_seed + i)
        h.update(rb.checksum().encode())
        h.update(repr(goal).encode())
    return h.hexdigest()


@dataclass
class BenchmarkReport:
    config: dict[str, Any]
    correctness: dict[str, Any]
    quality: dict[str, Any]
    dataset_checksum: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def run_benchmark(cfg: BenchmarkConfig | None = None) -> BenchmarkReport:
    """Run the full benchmark and return a structured, JSON-serialisable report."""
    cfg = cfg or BenchmarkConfig()
    return BenchmarkReport(
        config=asdict(cfg),
        correctness=run_correctness(cfg),
        quality=run_quality(cfg),
        dataset_checksum=_dataset_checksum(cfg),
    )
