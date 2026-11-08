from rulekiln.facts import Fact, WorkingMemory


def test_fact_of_is_order_insensitive():
    a = Fact.of("P", x=1, y=2)
    b = Fact.of("P", y=2, x=1)
    assert a == b
    assert hash(a) == hash(b)


def test_fact_get_and_as_dict():
    f = Fact.of("P", x=1, y="z")
    assert f.get("x") == 1
    assert f.get("y") == "z"
    assert f.get("missing") is None
    assert f.as_dict() == {"x": 1, "y": "z"}


def test_assert_is_idempotent_by_content():
    wm = WorkingMemory()
    assert wm.assert_fact(Fact.of("P", x=1)) is True
    assert wm.assert_fact(Fact.of("P", x=1)) is False
    assert len(wm) == 1


def test_timestamps_increase_with_new_facts():
    wm = WorkingMemory()
    wm.assert_fact(Fact.of("P", x=1))
    wm.assert_fact(Fact.of("P", x=2))
    assert wm.timestamp(Fact.of("P", x=1)) < wm.timestamp(Fact.of("P", x=2))


def test_retract_removes_fact():
    wm = WorkingMemory()
    f = Fact.of("P", x=1)
    wm.assert_fact(f)
    assert wm.retract(f) is True
    assert wm.retract(f) is False
    assert not wm.contains(f)


def test_facts_of_is_timestamp_ordered():
    wm = WorkingMemory()
    wm.assert_fact(Fact.of("P", x=3))
    wm.assert_fact(Fact.of("P", x=1))
    wm.assert_fact(Fact.of("Q", x=9))
    ps = wm.facts_of("P")
    assert [p.get("x") for p in ps] == [3, 1]
    assert len(wm.facts_of("Q")) == 1


def test_fingerprint_ignores_timestamps():
    wm1 = WorkingMemory()
    wm1.assert_fact(Fact.of("P", x=1))
    wm1.assert_fact(Fact.of("P", x=2))
    wm2 = WorkingMemory()
    wm2.assert_fact(Fact.of("P", x=2))
    wm2.assert_fact(Fact.of("P", x=1))
    assert wm1.fingerprint() == wm2.fingerprint()


def test_copy_is_independent():
    wm = WorkingMemory()
    wm.assert_fact(Fact.of("P", x=1))
    clone = wm.copy()
    clone.assert_fact(Fact.of("P", x=2))
    assert len(wm) == 1
    assert len(clone) == 2
