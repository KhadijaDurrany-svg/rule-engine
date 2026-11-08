"""Condition patterns and the binding-based matcher.

A :class:`Pattern` matches facts of a given ``kind`` subject to a tuple of
:class:`Constraint` tests. Constraints can pin an attribute to a literal,
compare it, bind it to a logic variable, or compare it to a previously bound
variable. Variable bindings join patterns together (the same variable appearing
in two patterns forces the matched facts to agree on that value).

The matcher is a straightforward deterministic nested-loop join. It is not a
Rete network: the project's goal is *correct, inspectable* forward chaining with
pluggable conflict resolution, benchmarked against an independent reference, not
raw match throughput. See ``docs/adr/0002-nested-loop-join.md``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .facts import Fact, Value, WorkingMemory

Bindings = Mapping[str, Value]
"""An immutable view of variable name -> value."""

_COMPARATORS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


@dataclass(frozen=True)
class Constraint:
    """A single test applied to one attribute of a candidate fact.

    Exactly one of ``literal`` or ``var`` carries meaning depending on ``op``:

    * ``op == "bind"`` binds attribute ``attr`` to variable ``var``.
    * ``op`` in the comparator set with ``var is None`` compares ``attr`` to
      ``literal``.
    * ``op`` in the comparator set with ``var`` set compares ``attr`` to the
      current value bound to ``var`` (which must already be bound).
    """

    attr: str
    op: str
    literal: Value | None = None
    var: str | None = None

    def __post_init__(self) -> None:
        if self.op == "bind":
            if self.var is None:
                raise ValueError("bind constraint requires a variable name")
        elif self.op not in _COMPARATORS:
            raise ValueError(f"unknown constraint op: {self.op!r}")


def eq(attr: str, value: Value) -> Constraint:
    """Attribute equals a literal."""
    return Constraint(attr, "==", literal=value)


def cmp(attr: str, op: str, value: Value) -> Constraint:
    """Attribute compares to a literal via ``op`` (``<``, ``>=`` ...)."""
    return Constraint(attr, op, literal=value)


def bind(attr: str, var: str) -> Constraint:
    """Bind attribute to variable ``var`` (joining it across patterns)."""
    return Constraint(attr, "bind", var=var)


def var_cmp(attr: str, op: str, var: str) -> Constraint:
    """Compare attribute to a previously bound variable."""
    return Constraint(attr, op, var=var)


@dataclass(frozen=True)
class Pattern:
    """A condition element.

    When ``negated`` is true the pattern is *negation as failure*: the condition
    element succeeds for a binding environment only when **no** fact matches it
    under that environment. Variables used by a negated pattern's literal/var
    comparisons must be bound by earlier positive patterns.
    """

    kind: str
    tests: tuple[Constraint, ...] = ()
    negated: bool = False


def _fact_satisfies(fact: Fact, tests: tuple[Constraint, ...], env: dict[str, Value]) -> dict[str, Value] | None:
    """Return an extended binding environment if ``fact`` satisfies ``tests``.

    ``env`` is not mutated; a new dict is returned on success, ``None`` on
    failure. Binds are applied in order so later tests can reference them.
    """
    out = dict(env)
    for test in tests:
        actual = fact.get(test.attr)
        if actual is None:
            return None
        if test.op == "bind":
            assert test.var is not None
            if test.var in out:
                if out[test.var] != actual:
                    return None
            else:
                out[test.var] = actual
            continue
        if test.var is not None:
            if test.var not in out:
                raise ValueError(f"variable {test.var!r} used before it was bound")
            target: Value = out[test.var]
        else:
            assert test.literal is not None
            target = test.literal
        # Guard against comparing incompatible types deterministically.
        if test.op in ("<", "<=", ">", ">=") and type(actual) is not type(target):
            return None
        if not _COMPARATORS[test.op](actual, target):
            return None
    return out


def match_pattern(
    pattern: Pattern,
    wm: WorkingMemory,
    env: dict[str, Value],
) -> list[tuple[dict[str, Value], Fact | None]]:
    """Match a single pattern against working memory under ``env``.

    For a positive pattern, returns one ``(new_env, fact)`` per matching fact,
    in ascending fact-timestamp order. For a negated pattern, returns a single
    ``(env, None)`` if nothing matches, else the empty list.
    """
    if pattern.negated:
        for fact in wm.facts_of(pattern.kind):
            if _fact_satisfies(fact, pattern.tests, env) is not None:
                return []
        return [(env, None)]

    results: list[tuple[dict[str, Value], Fact | None]] = []
    for fact in wm.facts_of(pattern.kind):
        extended = _fact_satisfies(fact, pattern.tests, env)
        if extended is not None:
            results.append((extended, fact))
    return results


def match_condition(
    patterns: tuple[Pattern, ...],
    wm: WorkingMemory,
) -> list[tuple[dict[str, Value], tuple[Fact, ...]]]:
    """Join all patterns, returning one result per consistent binding set.

    Each result is ``(bindings, matched_facts)`` where ``matched_facts`` holds
    the facts bound by the *positive* patterns in declaration order. The
    enumeration order is deterministic (driven by fact timestamps), which is
    what makes activation order reproducible.
    """
    frontier: list[tuple[dict[str, Value], tuple[Fact, ...]]] = [({}, ())]
    for pattern in patterns:
        nxt: list[tuple[dict[str, Value], tuple[Fact, ...]]] = []
        for env, matched in frontier:
            for new_env, fact in match_pattern(pattern, wm, env):
                if fact is None:
                    nxt.append((new_env, matched))
                else:
                    nxt.append((new_env, (*matched, fact)))
        frontier = nxt
        if not frontier:
            break
    return frontier
