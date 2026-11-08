# rulekiln

A deterministic **forward-chaining rule engine** (production / inference engine)
in pure Python. Condition → action rules fire against a working memory of facts
using the classic **match / resolve / act** cycle, with pluggable conflict-set
resolution (priority, specificity, recency, and lexical combinations),
instance-based refraction, and cycle detection.

The engine's correctness is checked *differentially* against an independent
brute-force reference implementation, and the value of principled conflict
resolution is **measured** on seeded synthetic rule bases with bootstrap
confidence intervals and a permutation test.

No network. No API keys. No required third-party runtime dependencies. Every
number below comes from a real run of the code in this repository.

## What it is (and is not)

`rulekiln` is a **rules / inference** engine. A rule is a logical implication:
when its condition patterns match facts in working memory, firing it asserts or
retracts facts. Chaining those firings derives new facts until the system
reaches quiescence (or a goal, a cycle, or a firing cap).

It is **not** a task scheduler. There are no tasks, no dependency DAG, no
workers, no async execution, no critical path. The unit of work is a *logical
rule firing* that transforms a set of facts; the interesting problem is **which
eligible rule to fire next**, i.e. conflict-set resolution.

## How this differs from the reference it was inspired by

This project was written after reading the README of a separate developer's
`AutomataCore-AI`, a high-level SaaS "AI workflow automation" engine (event
brokers, multi-tenant pipelines, LLM decisions, Kubernetes). That project is an
*orchestration platform* described at the architecture level. `rulekiln` shares
only the broad theme of "automation by rules" and is deliberately different:

- **Inference, not orchestration.** Forward chaining over facts with formal
  conflict resolution and refraction, versus multi-tenant workflow routing.
- **Deterministic and offline.** A run is a pure function of
  `(rule base, strategy, seed)`; no services, models or network.
- **Verified, not asserted.** Correctness is established by differential testing
  against an independent reference; quality claims come with CIs and a p-value,
  not adjectives.
- **Tiny and dependency-free** rather than a large distributed stack.

## Install

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"      # dev extras: pytest, hypothesis, ruff
```

## Use

### As a library

```python
from rulekiln import Engine, Fact, Pattern, Rule, RuleBase, Assert, eq, default_strategy

rb = RuleBase()
rb.add_fact(Fact.of("temp", room="lab", celsius=31))
rb.add_rule(Rule(
    name="too_hot",
    condition=(Pattern("temp", (eq("room", "lab"),)),),   # match a temp fact
    effects=(Assert.of("alert", room="lab", level="high"),),
    salience=10,
))

result = Engine(default_strategy()).run(rb)
print(result.status)                       # Status.QUIESCENT
print(result.wm.contains(Fact.of("alert", room="lab", level="high")))  # True
print(result.fired_rule_names())           # ['too_hot']
```

Variables join patterns; `bind` / `var_cmp` express joins, `cmp` expresses
comparisons, and a `Pattern(..., negated=True)` is negation-as-failure.

### CLI

```bash
rulekiln bench                 # run benchmark, write benchmarks/results.json + manifest.json
rulekiln bench --no-write      # print only
rulekiln bench --quality-bases 40 --correctness-bases 100 --random-trials 8
```

The manifest records the git SHA (falling back to `n/a`), the Python version,
the platform, the dataset checksum and the full config, so a run can be
reproduced and audited.

## Benchmarks

Reproduce with `rulekiln bench`. The numbers below are from the committed
`benchmarks/results.json` (Python 3.13, git SHA `n/a` in this sandbox;
`dataset_checksum` `9d422ed9…`).

### 1. Correctness — differential vs an independent brute-force reference

For each of **300 seeded random rule bases**, the engine and a separately written
brute-force reference (full Cartesian-product matcher, independent selection
logic) are run under the same strategy. We check they fire the **same
activations in the same order** and end in the **same status**.

| Strategy                      | Rule bases | Agree | Agreement rate |
|-------------------------------|-----------:|------:|---------------:|
| priority+specificity+recency  | 300        | 300   | 1.0000         |
| specificity                   | 300        | 300   | 1.0000         |
| unordered                     | 300        | 300   | 1.0000         |

This is a **differential test**: two independent implementations of one
specification. Full agreement is the honest *expected* result and its value is
as a regression guard — a single mismatch localises a bug to one side. It is a
correctness check, not a performance score, and is reported as a raw count.

### 2. Conflict-resolution quality — firings-to-goal

On **80 seeded goal-reachability scenarios** (mean chain length 4.6), a short
high-salience *direct* chain is the only path to the goal fact, buried among
many low-salience dead-end *distractor* rules plus a few high-salience *decoy*
dead ends. We measure **firings until the goal fact is first derived** (lower is
better) for the priority-aware default strategy versus two naive baselines. The
random baseline is averaged over **24 seeded trials per scenario**.

| Strategy                                   | Mean firings-to-goal |
|--------------------------------------------|---------------------:|
| ordered (priority + specificity + recency) | 5.475                |
| unordered (definition order)               | 15.787               |
| random                                     | 18.078               |

Paired per-scenario reduction (baseline − ordered), with percentile bootstrap
95% CI (10,000 resamples) and a two-sided paired sign-flip permutation test
(10,000 permutations):

| Comparison            | Mean reduction | 95% CI             | p-value                    | Ordered wins |
|-----------------------|---------------:|--------------------|----------------------------|-------------:|
| ordered vs random     | 12.603 firings | [11.997, 13.201]   | < 1e-4 (permutation floor) | 80/80        |
| ordered vs unordered  | 10.312 firings | [9.550, 11.050]    | < 1e-4 (permutation floor) | 80/80        |

"Permutation floor" means 0 of the 10,000 sign-flipped rearrangements reached
the observed mean, so the reported p is `1/(N+1) ≈ 9.999e-5`: the effect is
larger than any rearrangement of the paired differences, not a rounded-off zero.

**Why the gap is real but not a trick.** The scenario rewards prioritisation, so
a priority-aware strategy should win — that is the hypothesis under test. To keep
it honest the generator injects high-salience *decoy* rules that tie the direct
rules, so the priority strategy is **not optimal**: it still fires 1–4 decoys
before reaching the goal in about **55% of scenarios** (its mean, 5.475, exceeds
the mean chain length of 4.6). The win *rate* over the baselines is 100% because
the baselines waste far more firings on average, not because the engine is
perfect.

## Project layout

```
src/rulekiln/
  facts.py        Fact and WorkingMemory (timestamps, retraction, fingerprint)
  patterns.py     Pattern / Constraint and the deterministic nested-loop matcher
  rules.py        Rule, Assert/Retract effects, RuleBase, stable checksum
  activation.py   Activation + instance-based refraction token
  strategies.py   Priority / Specificity / Recency / Lexical / Unordered / Random
  engine.py       match/resolve/act loop, refraction, cycle detection, cap
  reference.py    independent brute-force engine for differential testing
  generators.py   seeded synthetic rule-base generators
  stats.py        bootstrap CI and permutation tests (pure stdlib)
  benchmark.py    the measured experiments
  cli.py          argparse CLI (`rulekiln bench`)
tests/            75 tests (pytest + Hypothesis)
docs/adr/         architecture decision records
benchmarks/       results.json + manifest.json (regenerated by `rulekiln bench`)
```

## Design notes

See `docs/adr/` for the reasoning behind the deterministic core (0001), the
nested-loop matcher instead of Rete (0002), and instance-based refraction with
conservative cycle detection (0003).

## Known gaps

- **Matcher scale.** The matcher recomputes matches each cycle with a
  nested-loop join (`O(rules × product of candidate facts)`). It is built for
  clarity and correctness, not throughput; a Rete backend is future work (ADR
  0002). Large fact bases will be slow.
- **Cycle detection is conservative.** It halts on the first firing that returns
  the fact set to a previously seen configuration (ADR 0003). A pathological
  base that revisits a configuration yet would still terminate is reported as a
  cycle. The firing `cap` is the final backstop.
- **Confluence needs monotonicity.** Add-only chaining is order-independent only
  when there is **no negation**; negation-as-failure can let firing order change
  the final fact set. This is a property of the semantics, is tested explicitly
  (`tests/test_properties.py`), and is why the quality scenarios are purely
  additive.
- **Benchmark scope.** The quality result is specific to the goal-reachability
  generator; it shows that priority-aware resolution reaches goals in fewer
  firings on *that* family, not a universal speed claim. The correctness result
  covers the behaviours the random generator produces (joins, comparisons,
  negation, retraction, cycles) but is not an exhaustive proof.
- **Effects are declarative.** Rule actions assert/retract facts with literal or
  bound-variable values; there is no arithmetic or user callback in effects
  (which is also what guarantees add-only termination).

## License

MIT — see `LICENSE`.
