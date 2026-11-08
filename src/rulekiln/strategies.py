"""Conflict-set resolution strategies.

When more than one activation is eligible to fire, the *conflict set* must be
narrowed to exactly one activation. Each strategy here imposes a **total,
deterministic** order on the conflict set and selects its maximum. Determinism
is guaranteed by always breaking ties on the activation enumeration sequence
(``seq``), so no strategy ever depends on dict or set iteration order.

Strategies provided:

* :class:`Priority` -- higher ``salience`` first (explicit control).
* :class:`Specificity` -- more specific rule first (more tests win).
* :class:`Recency` -- activation touching the most recently asserted fact first.
* :class:`Lexical` -- combine several strategies lexicographically; the default
  engine strategy is ``Lexical([Priority, Specificity, Recency])``.
* :class:`Unordered` -- definition/enumeration order (the naive baseline).
* :class:`Random` -- uniform random choice (the other naive baseline).
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from typing import Protocol

from .activation import Activation


class Strategy(Protocol):
    """A conflict-resolution strategy."""

    name: str

    def select(self, conflict_set: Sequence[Activation]) -> Activation:
        """Return the single activation to fire. ``conflict_set`` is non-empty."""
        ...


class _KeyStrategy:
    """Shared base for strategies defined by a numeric priority key.

    The selected activation maximises ``key`` with ties broken by the smallest
    ``seq`` (earliest enumerated), giving a stable total order.
    """

    name = "key"

    def key(self, act: Activation) -> float:  # pragma: no cover - overridden
        raise NotImplementedError

    def select(self, conflict_set: Sequence[Activation]) -> Activation:
        return max(conflict_set, key=lambda a: (self.key(a), -a.seq))


class Priority(_KeyStrategy):
    name = "priority"

    def key(self, act: Activation) -> float:
        return act.rule.salience


class Specificity(_KeyStrategy):
    name = "specificity"

    def key(self, act: Activation) -> float:
        return act.rule.specificity


class Recency(_KeyStrategy):
    name = "recency"

    def key(self, act: Activation) -> float:
        return act.recency


class Unordered:
    """Pick the earliest-enumerated activation (rule-definition / fact order).

    This models a naive engine that simply fires the first match it finds. It is
    deterministic but order-blind, serving as a baseline for benchmarking.
    """

    name = "unordered"

    def select(self, conflict_set: Sequence[Activation]) -> Activation:
        return min(conflict_set, key=lambda a: a.seq)


class Random:
    """Pick a uniformly random activation from the conflict set.

    Seeded for reproducibility. Used as the primary naive baseline: a rule
    engine with no principled conflict resolution.
    """

    name = "random"

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def select(self, conflict_set: Sequence[Activation]) -> Activation:
        # Index into a stable, sorted view so the only randomness is the choice.
        ordered = sorted(conflict_set, key=lambda a: a.seq)
        return ordered[self._rng.randrange(len(ordered))]


class Lexical:
    """Combine component strategies lexicographically (first is most significant).

    Each component contributes its ``key``; the composite key is the tuple of
    component keys, maximised, with ties broken by smallest ``seq``.
    """

    def __init__(self, components: Sequence[_KeyStrategy], name: str | None = None) -> None:
        if not components:
            raise ValueError("Lexical needs at least one component")
        self._components = tuple(components)
        self.name = name or "+".join(c.name for c in components)

    def select(self, conflict_set: Sequence[Activation]) -> Activation:
        def composite(a: Activation) -> tuple[float, ...]:
            return (*(c.key(a) for c in self._components), -a.seq)

        return max(conflict_set, key=composite)


def default_strategy() -> Lexical:
    """The recommended production strategy: priority, then specificity, then recency."""
    return Lexical([Priority(), Specificity(), Recency()], name="priority+specificity+recency")
