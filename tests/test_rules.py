from rulekiln.patterns import Pattern, bind, eq
from rulekiln.rules import Assert, Retract, Rule, RuleBase, build_assert


def test_assert_of_sorts_spec():
    e = Assert.of("P", y=2, x=1)
    assert e.spec == (("x", 1), ("y", 2))


def test_build_assert_substitutes_bound_variables():
    e = Assert.of("Out", val="v", tag="lit")
    fact = build_assert(e, {"v": 42})
    assert fact.get("val") == 42  # bound variable resolved
    assert fact.get("tag") == "lit"  # literal kept


def test_build_assert_keeps_literal_when_var_absent():
    e = Assert.of("Out", val="v")
    fact = build_assert(e, {})  # 'v' not bound -> treated as literal string
    assert fact.get("val") == "v"


def test_specificity_counts_patterns_and_tests():
    r = Rule(
        "r",
        (Pattern("P", (eq("x", 1), bind("y", "v"))), Pattern("Q", ())),
        (Assert.of("Z", a=1),),
    )
    # 2 patterns + 2 tests + 0 tests = 4
    assert r.specificity == 4


def test_positive_slots_excludes_negated():
    r = Rule(
        "r",
        (Pattern("P", ()), Pattern("Q", (), negated=True)),
        (Assert.of("Z", a=1),),
    )
    assert r.positive_slots() == 1


def test_retract_effect_dataclass():
    assert Retract(2).slot == 2


def test_checksum_is_stable_and_sensitive():
    rb1 = RuleBase()
    rb1.add_rule(Rule("r", (Pattern("P", (eq("x", 1),)),), (Assert.of("Q", a=1),), salience=3))
    rb2 = RuleBase()
    rb2.add_rule(Rule("r", (Pattern("P", (eq("x", 1),)),), (Assert.of("Q", a=1),), salience=3))
    rb3 = RuleBase()
    rb3.add_rule(Rule("r", (Pattern("P", (eq("x", 1),)),), (Assert.of("Q", a=1),), salience=4))
    assert rb1.checksum() == rb2.checksum()
    assert rb1.checksum() != rb3.checksum()
