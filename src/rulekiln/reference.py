"""An independent brute-force reference engine for differential testing.

This module re-implements forward-chaining semantics *from scratch*, with a
separate, deliberately naive code path: it enumerates the full Cartesian product
of candidate facts for each rule instead of the incremental join used by
:mod:`rulekiln.patterns`, and it re-derives conflict-resolution keys directly
from rule attributes rather than through the :mod:`rulekiln.strategies` objects.

Because the two implementations share no code but encode the same specification,
running both on the same seeded rule bases and checking that they fire the same
activations in the same order is a strong correctness (differential) test. Any
divergence points to a bug in exactly one of them.

The reference is intentionally slower and simpler; it is never used in the
benchmark's measured engine path.
"""

from __future__ import annotations

from collections.abc import Callable
from itertools import product

from .engine import DEFAULT_CAP, RunResult, Status
from .facts import Fact, Value, WorkingMemory
from .patterns import Pattern
from .rules import Assert, Rule, RuleBase

_OPS: dict[str, Callable[[Value, Value], bool]] = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


def _check(fact: Fact, pattern: Pattern, env: dict[str, Value]) -> dict[str, Value] | None:
    """Independent single-fact constraint check used by the reference matcher."""
    local = dict(env)
    for test in pattern.tests:
        actual = fact.get(test.attr)
        if actual is None:
            return None
        if test.op == "bind":
            assert test.var is not None
            if test.var in local and local[test.var] != actual:
                return None
            local[test.var] = actual
            continue
        if test.var is not None:
            if test.var not in local:
                raise ValueError(f"unbound variable {test.var!r}")
            target: Value = local[test.var]
        else:
            assert test.literal is not None
            target = test.literal
        if test.op in ("<", "<=", ">", ">=") and type(actual) is not type(target):
            return None
        if not _OPS[test.op](actual, target):
            return None
    return local


def _naive_matches(rule: Rule, wm: WorkingMemory) -> list[tuple[dict[str, Value], tuple[Fact, ...]]]:
    """Brute-force enumerate every binding for ``rule`` over the full product.

    Negated patterns are checked against the candidate environment after the
    positive patterns have bound their variables.
    """
    positive = [p for p in rule.condition if not p.negated]
    negative = [p for p in rule.condition if p.negated]

    candidate_lists = [wm.facts_of(p.kind) for p in positive]
    results: list[tuple[dict[str, Value], tuple[Fact, ...]]] = []

    for combo in product(*candidate_lists) if positive else [()]:
        env: dict[str, Value] = {}
        ok = True
        for pat, fact in zip(positive, combo, strict=True):
            extended = _check(fact, pat, env)
            if extended is None:
                ok = False
                break
            env = extended
        if not ok:
            continue
        # Negation as failure: fails if any fact matches the negated pattern.
        blocked = False
        for neg in negative:
            for fact in wm.facts_of(neg.kind):
                if _check(fact, neg, env) is not None:
                    blocked = True
                    break
            if blocked:
                break
        if not blocked:
            results.append((env, tuple(combo)))
    return results


def _rank(rule: Rule, recency: int, strategy: str) -> tuple:
    """Re-derive the ranking key for a strategy name, independently of
    :mod:`rulekiln.strategies`. Higher tuples fire first."""
    if strategy == "priority":
        return (rule.salience,)
    if strategy == "specificity":
        return (rule.specificity,)
    if strategy == "recency":
        return (recency,)
    if strategy == "priority+specificity+recency":
        return (rule.salience, rule.specificity, recency)
    if strategy == "unordered":
        return ()
    raise ValueError(f"reference does not support strategy {strategy!r}")


def run_reference(
    rb: RuleBase,
    strategy: str,
    goal: Fact | None = None,
    cap: int = DEFAULT_CAP,
) -> RunResult:
    """Run the brute-force reference for a named strategy.

    Supports the deterministic strategies (not ``random``) and returns a
    :class:`~rulekiln.engine.RunResult` with the same shape as the engine's, so
    the two can be compared activation-for-activation.
    """
    from .activation import Activation

    wm = WorkingMemory()
    for fact in rb.initial_facts:
        wm.assert_fact(fact)

    if goal is not None and wm.contains(goal):
        return RunResult(Status.GOAL, [], wm)

    fired: set = set()
    prev_fp = wm.fingerprint()
    seen = {prev_fp}
    history: list[Activation] = []

    while len(history) < cap:
        # Build conflict set via the naive matcher.
        conflict: list[Activation] = []
        seq = 0
        for rule in rb.rules:
            for env, facts in _naive_matches(rule, wm):
                stamps = tuple(wm.timestamp(f) for f in facts)
                recency = max(stamps) if stamps else 0
                act = Activation(
                    rule=rule,
                    facts=facts,
                    stamps=stamps,
                    bindings=tuple(sorted(env.items())),
                    recency=recency,
                    seq=seq,
                )
                seq += 1
                if act.token not in fired:
                    conflict.append(act)
        if not conflict:
            return RunResult(Status.QUIESCENT, history, wm)

        # Select: maximise rank, tie-break on smallest seq (independent logic).
        best = conflict[0]
        best_key = (_rank(best.rule, best.recency, strategy), -best.seq)
        for act in conflict[1:]:
            key = (_rank(act.rule, act.recency, strategy), -act.seq)
            if key > best_key:
                best, best_key = act, key

        fired.add(best.token)
        for effect in best.rule.effects:
            if isinstance(effect, Assert):
                from .rules import build_assert

                wm.assert_fact(build_assert(effect, best.binding_map()))
            elif 0 <= effect.slot < len(best.facts):
                wm.retract(best.facts[effect.slot])
        history.append(best)

        if goal is not None and wm.contains(goal):
            return RunResult(Status.GOAL, history, wm)

        fp = wm.fingerprint()
        if fp != prev_fp:
            if fp in seen:
                return RunResult(Status.CYCLE, history, wm)
            seen.add(fp)
        prev_fp = fp

    return RunResult(Status.CAP, history, wm)
