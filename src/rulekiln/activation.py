"""Rule activations.

An :class:`Activation` pairs a rule with a specific tuple of matched facts, the
assertion timestamps of those facts, and the bindings that produced them.

The refraction ``token`` is keyed on the matched facts' *timestamps*, i.e. the
working-memory instances, not merely their content. This mirrors CLIPS-style
refraction: an activation fires once per WME instance, but if a fact is
retracted and an equal fact re-asserted (a fresh instance with a new timestamp)
the activation is eligible again. Add-only rule bases therefore terminate (a
finite set of instances, each token firing once), while genuinely oscillating
non-monotonic bases are left for the engine's cycle detector to halt.
"""

from __future__ import annotations

from dataclasses import dataclass

from .facts import Fact, Value
from .rules import Rule


@dataclass(frozen=True)
class Activation:
    """A fully matched, fireable rule instance."""

    rule: Rule
    facts: tuple[Fact, ...]
    stamps: tuple[int, ...]
    bindings: tuple[tuple[str, Value], ...]
    recency: int
    seq: int

    @property
    def token(self) -> tuple[str, tuple[int, ...]]:
        """Refraction key: rule name plus the matched WME instance timestamps."""
        return (self.rule.name, self.stamps)

    def binding_map(self) -> dict[str, Value]:
        return dict(self.bindings)
