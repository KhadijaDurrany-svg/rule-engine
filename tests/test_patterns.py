import pytest

from rulekiln.facts import Fact, WorkingMemory
from rulekiln.patterns import Constraint, Pattern, bind, cmp, eq, match_condition, var_cmp


def _wm(*facts: Fact) -> WorkingMemory:
    wm = WorkingMemory()
    for f in facts:
        wm.assert_fact(f)
    return wm


def test_eq_matches_literal():
    wm = _wm(Fact.of("P", x=1), Fact.of("P", x=2))
    results = match_condition((Pattern("P", (eq("x", 1),)),), wm)
    assert len(results) == 1
    assert results[0][1][0].get("x") == 1


def test_cmp_comparisons():
    wm = _wm(Fact.of("P", x=1), Fact.of("P", x=5), Fact.of("P", x=9))
    results = match_condition((Pattern("P", (cmp("x", ">=", 5),)),), wm)
    assert sorted(r[1][0].get("x") for r in results) == [5, 9]


def test_bind_joins_two_patterns():
    wm = _wm(Fact.of("P", k=1), Fact.of("Q", k=1), Fact.of("Q", k=2))
    cond = (Pattern("P", (bind("k", "v"),)), Pattern("Q", (var_cmp("k", "==", "v"),)))
    results = match_condition(cond, wm)
    assert len(results) == 1
    assert results[0][0]["v"] == 1


def test_bind_consistency_within_pattern():
    # Same var bound twice must agree.
    wm = _wm(Fact.of("P", a=1, b=1), Fact.of("P", a=1, b=2))
    cond = (Pattern("P", (bind("a", "v"), bind("b", "v"))),)
    results = match_condition(cond, wm)
    assert len(results) == 1  # only a=1,b=1 is consistent


def test_negation_blocks_when_present():
    wm = _wm(Fact.of("P", x=1), Fact.of("Stop", x=1))
    cond = (Pattern("P", (bind("x", "v"),)), Pattern("Stop", (var_cmp("x", "==", "v"),), negated=True))
    assert match_condition(cond, wm) == []


def test_negation_allows_when_absent():
    wm = _wm(Fact.of("P", x=1))
    cond = (Pattern("P", (bind("x", "v"),)), Pattern("Stop", (var_cmp("x", "==", "v"),), negated=True))
    assert len(match_condition(cond, wm)) == 1


def test_unbound_variable_raises():
    wm = _wm(Fact.of("P", x=1))
    with pytest.raises(ValueError):
        match_condition((Pattern("P", (var_cmp("x", "==", "nope"),)),), wm)


def test_invalid_constraint_op():
    with pytest.raises(ValueError):
        Constraint("x", "~=")


def test_bind_requires_var():
    with pytest.raises(ValueError):
        Constraint("x", "bind")


def test_type_mismatch_comparison_is_safe():
    # Comparing int attr to str literal with < must not raise, just not match.
    wm = _wm(Fact.of("P", x=1))
    results = match_condition((Pattern("P", (cmp("x", "<", "a"),)),), wm)
    assert results == []
