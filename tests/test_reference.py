from hypothesis import given, settings
from hypothesis import strategies as st

from rulekiln.engine import Engine
from rulekiln.generators import random_rule_base
from rulekiln.reference import run_reference
from rulekiln.strategies import Priority, Recency, Specificity, Unordered, default_strategy

_STRATS = {
    "priority": Priority(),
    "specificity": Specificity(),
    "recency": Recency(),
    "unordered": Unordered(),
    "priority+specificity+recency": default_strategy(),
}


def _agree(seed: int, name: str) -> bool:
    rb = random_rule_base(seed)
    eng = Engine(_STRATS[name]).run(rb)
    ref = run_reference(rb, name)
    return eng.status == ref.status and eng.fired_tokens() == ref.fired_tokens()


def test_reference_matches_default_strategy_fixed_seeds():
    for seed in range(50):
        assert _agree(seed, "priority+specificity+recency"), seed


def test_reference_matches_specificity_fixed_seeds():
    for seed in range(50):
        assert _agree(seed, "specificity"), seed


def test_reference_matches_unordered_fixed_seeds():
    for seed in range(50):
        assert _agree(seed, "unordered"), seed


@given(seed=st.integers(min_value=0, max_value=50_000), name=st.sampled_from(list(_STRATS)))
@settings(max_examples=250, deadline=None)
def test_reference_matches_engine_property(seed, name):
    assert _agree(seed, name)
