"""Property-based tests (Hypothesis) for engine invariants."""

from hypothesis import given, settings
from hypothesis import strategies as st

from rulekiln.engine import Engine, Status
from rulekiln.generators import random_rule_base
from rulekiln.rules import Assert, Rule, RuleBase
from rulekiln.strategies import Priority, Recency, Specificity, Unordered, default_strategy

_DET_STRATS = [Priority(), Specificity(), Recency(), Unordered(), default_strategy()]


def _to_monotonic(rb: RuleBase) -> RuleBase:
    """Return a monotonic copy: keep only Assert effects and drop negated
    patterns.

    Both restrictions are required for confluence. Retraction obviously breaks
    monotonicity; negation-as-failure does too, because a rule that fires only
    while some fact is *absent* can be permanently blocked if another rule
    asserts that fact first -- so with negation the final fact set can depend on
    firing order. Positive, add-only forward chaining computes the least fixed
    point, which is order-independent.
    """
    out = RuleBase(initial_facts=list(rb.initial_facts))
    for r in rb.rules:
        asserts = tuple(e for e in r.effects if isinstance(e, Assert))
        positive = tuple(p for p in r.condition if not p.negated)
        if asserts and positive:
            out.add_rule(Rule(r.name, positive, asserts, r.salience))
    return out


@given(seed=st.integers(min_value=0, max_value=50_000))
@settings(max_examples=200, deadline=None)
def test_monotonic_is_confluent_across_strategies(seed):
    """Positive, add-only chaining reaches the same fact set regardless of the
    conflict-resolution strategy -- order affects *when*, not *what*."""
    rb = _to_monotonic(random_rule_base(seed))
    results = [Engine(s).run(rb) for s in _DET_STRATS]
    for r in results:
        assert r.status == Status.QUIESCENT
    fingerprints = {frozenset(r.wm.fingerprint()) for r in results}
    assert len(fingerprints) == 1


@given(seed=st.integers(min_value=0, max_value=50_000))
@settings(max_examples=200, deadline=None)
def test_run_is_deterministic(seed):
    """The same rule base + strategy always yields the identical firing trace."""
    rb = random_rule_base(seed)
    a = Engine(default_strategy()).run(rb)
    b = Engine(default_strategy()).run(rb)
    assert a.status == b.status
    assert a.fired_tokens() == b.fired_tokens()


@given(seed=st.integers(min_value=0, max_value=50_000))
@settings(max_examples=200, deadline=None)
def test_refraction_bounds_add_only_firings(seed):
    """With no retraction, total firings never exceed the number of distinct
    possible activation instances, so a run always terminates (never CAP)."""
    rb = _to_monotonic(random_rule_base(seed))
    res = Engine(default_strategy()).run(rb)
    assert res.status == Status.QUIESCENT
