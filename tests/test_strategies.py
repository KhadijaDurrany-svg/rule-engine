import random

from rulekiln.activation import Activation
from rulekiln.facts import Fact
from rulekiln.patterns import Pattern, eq
from rulekiln.rules import Assert, Rule
from rulekiln.strategies import (
    Lexical,
    Priority,
    Random,
    Recency,
    Specificity,
    Unordered,
    default_strategy,
)


def _rule(name, salience=0, ntests=0):
    tests = tuple(eq("x", i) for i in range(ntests))
    return Rule(name, (Pattern("P", tests),), (Assert.of("Z", a=1),), salience=salience)


def _act(rule, recency=0, seq=0):
    return Activation(rule=rule, facts=(Fact.of("P", x=1),), stamps=(recency,), bindings=(), recency=recency, seq=seq)


def test_priority_picks_highest_salience():
    cs = [_act(_rule("a", salience=1), seq=0), _act(_rule("b", salience=5), seq=1)]
    assert Priority().select(cs).rule.name == "b"


def test_specificity_picks_most_specific():
    cs = [_act(_rule("a", ntests=1), seq=0), _act(_rule("b", ntests=3), seq=1)]
    assert Specificity().select(cs).rule.name == "b"


def test_recency_picks_most_recent():
    cs = [_act(_rule("a"), recency=1, seq=0), _act(_rule("b"), recency=9, seq=1)]
    assert Recency().select(cs).rule.name == "b"


def test_unordered_picks_smallest_seq():
    cs = [_act(_rule("a"), seq=3), _act(_rule("b"), seq=1)]
    assert Unordered().select(cs).rule.name == "b"


def test_tie_broken_by_seq():
    # Equal salience -> earliest seq wins deterministically.
    cs = [_act(_rule("a", salience=5), seq=2), _act(_rule("b", salience=5), seq=1)]
    assert Priority().select(cs).rule.name == "b"


def test_lexical_orders_components():
    # Same salience; specificity breaks the tie.
    cs = [
        _act(_rule("a", salience=5, ntests=1), seq=0),
        _act(_rule("b", salience=5, ntests=3), seq=1),
    ]
    strat = Lexical([Priority(), Specificity(), Recency()])
    assert strat.select(cs).rule.name == "b"


def test_default_strategy_name():
    assert default_strategy().name == "priority+specificity+recency"


def test_random_is_seed_reproducible():
    cs = [_act(_rule(f"r{i}"), seq=i) for i in range(5)]
    a = Random(random.Random(123)).select(cs).rule.name
    b = Random(random.Random(123)).select(cs).rule.name
    assert a == b


def test_random_only_chooses_members():
    cs = [_act(_rule(f"r{i}"), seq=i) for i in range(5)]
    names = {a.rule.name for a in cs}
    chosen = Random(random.Random(7)).select(cs)
    assert chosen.rule.name in names


def test_lexical_requires_components():
    import pytest

    with pytest.raises(ValueError):
        Lexical([])
