"""Rules, effects and rule bases.

A :class:`Rule` is ``condition -> effects``. The condition is a tuple of
patterns (see :mod:`rulekiln.patterns`); the effects are a tuple of declarative
:class:`Effect` operations evaluated against the bindings produced by a match.

Effects are *data*, not Python callables, so that the independent brute-force
reference engine can replay them with identical semantics and so that a rule
base can be checksummed for a reproducible benchmark manifest.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .facts import Fact, Value
from .patterns import Bindings, Pattern


@dataclass(frozen=True)
class Assert:
    """Assert a new fact. Each ``spec`` value is either a literal or, if it is a
    string naming a bound variable, the value bound to that variable."""

    kind: str
    spec: tuple[tuple[str, Value], ...]

    @staticmethod
    def of(kind: str, **spec: Value) -> Assert:
        return Assert(kind, tuple(sorted(spec.items())))


@dataclass(frozen=True)
class Retract:
    """Retract the fact matched by positive pattern index ``slot``."""

    slot: int


Effect = Assert | Retract


def _resolve(value: Value, bindings: Bindings) -> Value:
    """Resolve a spec value: a string that names a bound variable becomes that
    variable's value; everything else is a literal."""
    if isinstance(value, str) and value in bindings:
        return bindings[value]
    return value


def build_assert(effect: Assert, bindings: Bindings) -> Fact:
    """Construct the concrete fact an :class:`Assert` effect produces."""
    attrs = {name: _resolve(val, bindings) for name, val in effect.spec}
    return Fact(effect.kind, tuple(sorted(attrs.items())))


@dataclass(frozen=True)
class Rule:
    """A production rule.

    ``salience`` is the explicit priority used by the *priority* strategy
    (higher fires first). ``condition`` patterns are matched in order; the
    positive ones populate the matched-fact tuple that :class:`Retract` slots
    refer to.
    """

    name: str
    condition: tuple[Pattern, ...]
    effects: tuple[Effect, ...]
    salience: int = 0

    @property
    def specificity(self) -> int:
        """Number of condition tests + patterns, a proxy for how specific the
        rule is. Used by the *specificity* strategy (more specific fires first)."""
        return len(self.condition) + sum(len(p.tests) for p in self.condition)

    def positive_slots(self) -> int:
        return sum(1 for p in self.condition if not p.negated)


@dataclass
class RuleBase:
    """An ordered collection of rules plus the initial facts."""

    rules: list[Rule] = field(default_factory=list)
    initial_facts: list[Fact] = field(default_factory=list)

    def add_rule(self, rule: Rule) -> RuleBase:
        self.rules.append(rule)
        return self

    def add_fact(self, fact: Fact) -> RuleBase:
        self.initial_facts.append(fact)
        return self

    def checksum(self) -> str:
        """Stable SHA-256 of the rule base, for the benchmark manifest.

        The digest covers rule names, salience, conditions and effects, plus the
        initial facts, in a canonical textual form.
        """
        import hashlib

        parts: list[str] = []
        for rule in self.rules:
            parts.append(f"R|{rule.name}|{rule.salience}")
            for pat in rule.condition:
                tests = ";".join(f"{t.attr}{t.op}{t.literal}:{t.var}" for t in pat.tests)
                parts.append(f"  P|{pat.kind}|neg={pat.negated}|{tests}")
            for eff in rule.effects:
                if isinstance(eff, Assert):
                    parts.append(f"  A|{eff.kind}|{eff.spec}")
                else:
                    parts.append(f"  X|{eff.slot}")
        for fact in self.initial_facts:
            parts.append(f"F|{fact.kind}|{fact.attrs}")
        blob = "\n".join(parts).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()
