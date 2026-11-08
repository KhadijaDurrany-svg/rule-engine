"""Seeded synthetic rule-base generators.

Two families are produced, both fully determined by an integer seed (no network,
no external data):

* :func:`random_rule_base` -- small, varied rule bases (binds, joins, negation,
  comparisons, asserts and retracts) used for *differential* correctness testing
  of the engine against the brute-force reference.

* :func:`goal_scenario` -- a goal-reachability race used to measure
  conflict-resolution quality. A short, high-salience *direct* chain derives the
  goal fact, buried among many low-salience *distractor* rules that fire once and
  lead nowhere. A priority-aware strategy reaches the goal in a number of firings
  equal to the chain length; an order-blind strategy wastes firings on
  distractors first. Rule order is shuffled per seed so the naive baselines get
  no definition-order advantage and the engine's order-independence is exercised.
"""

from __future__ import annotations

import random

from .facts import Fact
from .patterns import Pattern, bind, eq, var_cmp
from .rules import Assert, Retract, Rule, RuleBase

_KINDS = ("A", "B", "C")
_ATTRS = ("x", "y")
_DOMAIN = (0, 1, 2, 3)


def random_rule_base(seed: int) -> RuleBase:
    """Generate a small, valid, varied rule base for differential testing.

    Value domains are finite so runs terminate (or trip the engine's cycle
    detector) rather than diverging. All variable references are guaranteed
    bound before use, so matching never raises.
    """
    rng = random.Random(seed)
    rb = RuleBase()

    for _ in range(rng.randint(2, 5)):
        kind = rng.choice(_KINDS)
        attrs = {a: rng.choice(_DOMAIN) for a in _ATTRS}
        rb.add_fact(Fact.of(kind, **attrs))

    n_rules = rng.randint(2, 6)
    for r in range(n_rules):
        patterns: list[Pattern] = []
        bound: dict[str, str] = {}  # var -> (unused) marker

        # First positive pattern, possibly binding a variable.
        k0 = rng.choice(_KINDS)
        tests0 = []
        if rng.random() < 0.6:
            tests0.append(eq(rng.choice(_ATTRS), rng.choice(_DOMAIN)))
        if rng.random() < 0.5:
            v = f"v{r}"
            tests0.append(bind(rng.choice(_ATTRS), v))
            bound[v] = v
        patterns.append(Pattern(k0, tuple(tests0)))

        # Optional join pattern referencing a bound variable.
        if bound and rng.random() < 0.5:
            v = next(iter(bound))
            patterns.append(Pattern(rng.choice(_KINDS), (var_cmp(rng.choice(_ATTRS), "==", v),)))

        # Optional negated pattern (literal-only, always safe).
        if rng.random() < 0.4:
            patterns.append(Pattern(rng.choice(_KINDS), (eq(rng.choice(_ATTRS), rng.choice(_DOMAIN)),), negated=True))

        # Effects: an assert (literals) and sometimes a retract of a matched slot.
        effects: list = [Assert.of(rng.choice(_KINDS), x=rng.choice(_DOMAIN), y=rng.choice(_DOMAIN))]
        n_positive = sum(1 for p in patterns if not p.negated)
        if rng.random() < 0.35 and n_positive:
            effects.append(Retract(rng.randrange(n_positive)))

        rb.add_rule(Rule(f"r{seed}_{r}", tuple(patterns), tuple(effects), salience=rng.randint(0, 5)))

    return rb


def goal_scenario(
    seed: int,
    chain_min: int = 3,
    chain_max: int = 6,
    distractor_min: int = 8,
    distractor_max: int = 16,
    decoy_min: int = 0,
    decoy_max: int = 4,
) -> tuple[RuleBase, Fact]:
    """Build a goal-reachability scenario and return ``(rule_base, goal_fact)``.

    The goal is ``F(id=chain_len)``. ``chain_len`` direct rules (high salience)
    form the only path to it; ``n_distractors`` low-salience rules each fire once
    and lead nowhere.

    To keep the benchmark honest, a few *decoy* rules also carry the direct
    rules' high salience but are dead ends. They make priority an imperfect
    heuristic: when a decoy ties a direct rule it may be fired first, so the
    priority strategy does not always reach the goal in exactly ``chain_len``
    firings. This injects real per-scenario variance rather than a constant.
    Rule order is shuffled with the seed.
    """
    rng = random.Random(seed)
    chain_len = rng.randint(chain_min, chain_max)
    n_distractors = rng.randint(distractor_min, distractor_max)
    n_decoys = rng.randint(decoy_min, decoy_max)

    rb = RuleBase()
    rb.add_fact(Fact.of("F", id=0))

    rules: list[Rule] = []
    # Direct chain: F(id=i) -> F(id=i+1), high salience.
    for i in range(chain_len):
        rules.append(
            Rule(
                name=f"direct_{i}",
                condition=(Pattern("F", (eq("id", i),)),),
                effects=(Assert.of("F", id=i + 1),),
                salience=10,
            )
        )
    # Low-salience distractors: match the ever-present seed fact, dead end.
    for j in range(n_distractors):
        rules.append(
            Rule(
                name=f"distractor_{j}",
                condition=(Pattern("F", (eq("id", 0),)),),
                effects=(Assert.of("G", id=1000 + j),),
                salience=1,
            )
        )
    # High-salience decoys: same priority as direct rules but dead ends, so the
    # priority heuristic is not guaranteed optimal.
    for d in range(n_decoys):
        rules.append(
            Rule(
                name=f"decoy_{d}",
                condition=(Pattern("F", (eq("id", 0),)),),
                effects=(Assert.of("H", id=2000 + d),),
                salience=10,
            )
        )

    rng.shuffle(rules)
    rb.rules = rules
    goal = Fact.of("F", id=chain_len)
    return rb, goal
