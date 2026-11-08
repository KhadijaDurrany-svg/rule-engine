from rulekiln.engine import Engine, Status
from rulekiln.facts import Fact, WorkingMemory
from rulekiln.patterns import Pattern, bind, eq, var_cmp
from rulekiln.rules import Assert, Retract, Rule, RuleBase
from rulekiln.strategies import Priority, default_strategy


def _chain_base(n: int) -> RuleBase:
    rb = RuleBase()
    rb.add_fact(Fact.of("F", id=0))
    for i in range(n):
        rb.add_rule(Rule(f"d{i}", (Pattern("F", (eq("id", i),)),), (Assert.of("F", id=i + 1),)))
    return rb


def test_forward_chaining_derives_all():
    rb = _chain_base(4)
    res = Engine().run(rb)
    assert res.status == Status.QUIESCENT
    assert res.wm.contains(Fact.of("F", id=4))
    assert res.fired == 4


def test_refraction_terminates_add_only():
    # A rule whose action re-asserts an existing fact must not loop.
    rb = RuleBase()
    rb.add_fact(Fact.of("P", x=1))
    rb.add_rule(Rule("noop", (Pattern("P", (eq("x", 1),)),), (Assert.of("P", x=1),)))
    res = Engine().run(rb)
    assert res.status == Status.QUIESCENT
    assert res.fired == 1


def test_goal_stops_early():
    rb = _chain_base(10)
    res = Engine().run(rb, goal=Fact.of("F", id=3))
    assert res.status == Status.GOAL
    assert res.fired == 3


def test_goal_already_present():
    rb = _chain_base(3)
    rb.add_fact(Fact.of("G", y=1))
    res = Engine().run(rb, goal=Fact.of("G", y=1))
    assert res.status == Status.GOAL
    assert res.fired == 0


def test_cycle_detected():
    rb = RuleBase()
    rb.add_fact(Fact.of("S", v=0))
    rb.add_rule(Rule("on", (Pattern("S", (eq("v", 0),)),), (Retract(0), Assert.of("S", v=1))))
    rb.add_rule(Rule("off", (Pattern("S", (eq("v", 1),)),), (Retract(0), Assert.of("S", v=0))))
    res = Engine().run(rb)
    assert res.status == Status.CYCLE


def test_cap_backstop():
    # Two toggling facts could oscillate; a tiny cap forces CAP before CYCLE
    # when the cap is hit first.
    rb = RuleBase()
    rb.add_fact(Fact.of("S", v=0))
    rb.add_rule(Rule("on", (Pattern("S", (eq("v", 0),)),), (Retract(0), Assert.of("S", v=1))))
    res = Engine(cap=1).run(rb)
    assert res.status == Status.CAP
    assert res.fired == 1


def test_run_accepts_external_wm():
    rb = RuleBase()
    rb.add_rule(Rule("d", (Pattern("F", (eq("id", 0),)),), (Assert.of("F", id=1),)))
    wm = WorkingMemory()
    wm.assert_fact(Fact.of("F", id=0))
    res = Engine().run(rb, wm=wm)
    assert res.wm.contains(Fact.of("F", id=1))


def test_join_rule_fires_with_bindings():
    rb = RuleBase()
    rb.add_fact(Fact.of("Parent", p="a", c="b"))
    rb.add_fact(Fact.of("Parent", p="b", c="c"))
    # grandparent(X,Z) :- Parent(X,Y), Parent(Y,Z)
    rb.add_rule(
        Rule(
            "gp",
            (
                Pattern("Parent", (bind("p", "x"), bind("c", "y"))),
                Pattern("Parent", (var_cmp("p", "==", "y"), bind("c", "z"))),
            ),
            (Assert.of("Grand", gp="x", gc="z"),),
        )
    )
    res = Engine().run(rb)
    assert res.wm.contains(Fact.of("Grand", gp="a", gc="c"))


def test_history_records_rule_names():
    rb = _chain_base(3)
    res = Engine(Priority()).run(rb)
    assert res.fired_rule_names() == ["d0", "d1", "d2"]


def test_default_strategy_used_when_none():
    eng = Engine()
    assert eng.strategy.name == default_strategy().name
