from rulekiln.engine import Engine, Status
from rulekiln.generators import goal_scenario, random_rule_base
from rulekiln.strategies import default_strategy


def test_random_rule_base_is_deterministic():
    assert random_rule_base(42).checksum() == random_rule_base(42).checksum()


def test_random_rule_base_differs_by_seed():
    assert random_rule_base(1).checksum() != random_rule_base(2).checksum()


def test_goal_scenario_is_deterministic():
    rb1, g1 = goal_scenario(100)
    rb2, g2 = goal_scenario(100)
    assert rb1.checksum() == rb2.checksum()
    assert g1 == g2


def test_goal_scenario_goal_is_reachable():
    for seed in range(30):
        rb, goal = goal_scenario(10_000 + seed)
        res = Engine(default_strategy()).run(rb, goal=goal)
        assert res.status == Status.GOAL


def test_goal_scenario_has_distractors_and_direct_chain():
    rb, goal = goal_scenario(10_000)
    names = {r.name for r in rb.rules}
    assert any(n.startswith("direct_") for n in names)
    assert any(n.startswith("distractor_") for n in names)
    # Goal id equals the number of direct rules (chain length).
    assert goal.get("id") == sum(1 for n in names if n.startswith("direct_"))
