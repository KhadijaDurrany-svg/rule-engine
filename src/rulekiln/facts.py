"""Facts and working memory.

A :class:`Fact` is an immutable, hashable record identified by its ``kind`` and
its sorted attribute mapping. The :class:`WorkingMemory` holds facts, assigns a
monotonically increasing assertion timestamp to each (used for the *recency*
conflict-resolution strategy), and supports retraction.

Re-asserting a fact that is already present is a no-op: a fact's identity is its
``(kind, attrs)`` content, so working memory is a *set* of facts in the logical
sense. This keeps forward chaining confluent for add-only rule bases.
"""

from __future__ import annotations

from dataclasses import dataclass

Value = str | int | bool
"""Allowed attribute value types. Kept deliberately small so facts stay hashable
and JSON-serialisable for reproducible benchmark manifests."""


@dataclass(frozen=True)
class Fact:
    """An immutable working-memory datum.

    ``attrs`` is stored as a sorted tuple of ``(name, value)`` pairs so that two
    facts with the same content compare equal and hash equal regardless of the
    insertion order of their attributes.
    """

    kind: str
    attrs: tuple[tuple[str, Value], ...]

    @staticmethod
    def of(kind: str, **attrs: Value) -> Fact:
        """Construct a fact from keyword attributes."""
        return Fact(kind, tuple(sorted(attrs.items())))

    def get(self, name: str) -> Value | None:
        """Return the value of attribute ``name`` or ``None`` if absent."""
        for key, value in self.attrs:
            if key == name:
                return value
        return None

    def as_dict(self) -> dict[str, Value]:
        """Return the attributes as an ordinary dict."""
        return dict(self.attrs)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        body = ", ".join(f"{k}={v!r}" for k, v in self.attrs)
        return f"{self.kind}({body})"


class WorkingMemory:
    """A mutable set of facts with per-fact assertion timestamps.

    Timestamps are a global counter incremented on every *successful* assertion
    (a genuinely new fact). They give a total, deterministic recency order.
    """

    def __init__(self) -> None:
        self._facts: dict[Fact, int] = {}
        self._clock: int = 0

    def assert_fact(self, fact: Fact) -> bool:
        """Add ``fact``. Return ``True`` if it was new, ``False`` if already present."""
        if fact in self._facts:
            return False
        self._clock += 1
        self._facts[fact] = self._clock
        return True

    def retract(self, fact: Fact) -> bool:
        """Remove ``fact``. Return ``True`` if it was present."""
        return self._facts.pop(fact, None) is not None

    def timestamp(self, fact: Fact) -> int:
        """Return the assertion timestamp of ``fact`` (raises if absent)."""
        return self._facts[fact]

    def contains(self, fact: Fact) -> bool:
        return fact in self._facts

    def facts_of(self, kind: str) -> list[Fact]:
        """Return facts of ``kind`` ordered by ascending assertion timestamp."""
        selected = [f for f in self._facts if f.kind == kind]
        selected.sort(key=lambda f: self._facts[f])
        return selected

    def all_facts(self) -> list[Fact]:
        """Return every fact ordered by ascending assertion timestamp."""
        return sorted(self._facts, key=lambda f: self._facts[f])

    def fingerprint(self) -> frozenset[Fact]:
        """A content fingerprint of the current fact set (ignores timestamps).

        Used by the engine's cycle detector to recognise revisited states.
        """
        return frozenset(self._facts)

    def __len__(self) -> int:
        return len(self._facts)

    def copy(self) -> WorkingMemory:
        clone = WorkingMemory()
        clone._facts = dict(self._facts)
        clone._clock = self._clock
        return clone
