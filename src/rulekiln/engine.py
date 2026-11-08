"""The forward-chaining inference engine.

The engine runs the classic match / resolve / act cycle:

1. **Match** every rule against working memory, producing the conflict set of
   eligible activations (those not already fired, by refraction).
2. **Resolve** the conflict set to a single activation via a pluggable
   :class:`~rulekiln.strategies.Strategy`.
3. **Act** by applying the activation's effects, mutating working memory.

The loop stops on *quiescence* (empty conflict set), when a goal fact appears,
when a cycle (a revisited working-memory state) is detected, or when a firing
cap is reached. Every tie is broken deterministically, so a run is a pure
function of (rule base, strategy, seed).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .activation import Activation
from .facts import Fact, WorkingMemory
from .patterns import match_condition
from .rules import Assert, RuleBase, build_assert
from .strategies import Strategy, default_strategy


class Status(str, Enum):
    """Why a run ended."""

    QUIESCENT = "quiescent"
    GOAL = "goal"
    CYCLE = "cycle"
    CAP = "cap"


@dataclass
class RunResult:
    """The outcome of an engine run."""

    status: Status
    history: list[Activation] = field(default_factory=list)
    wm: WorkingMemory | None = None

    @property
    def fired(self) -> int:
        return len(self.history)

    def fired_tokens(self) -> list[tuple[str, tuple[int, ...]]]:
        return [a.token for a in self.history]

    def fired_rule_names(self) -> list[str]:
        return [a.rule.name for a in self.history]


DEFAULT_CAP = 10_000


class Engine:
    """A forward-chaining production-rule engine."""

    def __init__(self, strategy: Strategy | None = None, cap: int = DEFAULT_CAP) -> None:
        self.strategy: Strategy = strategy or default_strategy()
        self.cap = cap

    def _conflict_set(self, rb: RuleBase, wm: WorkingMemory, fired: set) -> list[Activation]:
        """Match all rules and return eligible (non-refracted) activations.

        ``seq`` numbers activations in a stable, rule-then-match order so that
        strategies have a deterministic tiebreak.
        """
        activations: list[Activation] = []
        seq = 0
        for rule in rb.rules:
            for bindings, facts in match_condition(rule.condition, wm):
                stamps = tuple(wm.timestamp(f) for f in facts)
                recency = max(stamps) if stamps else 0
                act = Activation(
                    rule=rule,
                    facts=facts,
                    stamps=stamps,
                    bindings=tuple(sorted(bindings.items())),
                    recency=recency,
                    seq=seq,
                )
                seq += 1
                if act.token not in fired:
                    activations.append(act)
        return activations

    def _fire(self, act: Activation, wm: WorkingMemory) -> None:
        """Apply an activation's effects to working memory."""
        bindings = act.binding_map()
        for effect in act.rule.effects:
            if isinstance(effect, Assert):
                wm.assert_fact(build_assert(effect, bindings))
            else:  # Retract
                if 0 <= effect.slot < len(act.facts):
                    wm.retract(act.facts[effect.slot])

    def run(
        self,
        rb: RuleBase,
        wm: WorkingMemory | None = None,
        goal: Fact | None = None,
    ) -> RunResult:
        """Run to quiescence, goal, cycle or cap.

        If ``wm`` is omitted a fresh working memory is seeded from the rule
        base's initial facts. If ``goal`` is given the run stops as soon as that
        fact is present (checked before firing and after each firing).
        """
        if wm is None:
            wm = WorkingMemory()
            for fact in rb.initial_facts:
                wm.assert_fact(fact)

        if goal is not None and wm.contains(goal):
            return RunResult(Status.GOAL, [], wm)

        fired: set = set()
        prev_fp = wm.fingerprint()
        seen_states: set = {prev_fp}
        history: list[Activation] = []

        while len(history) < self.cap:
            conflict_set = self._conflict_set(rb, wm, fired)
            if not conflict_set:
                return RunResult(Status.QUIESCENT, history, wm)

            chosen = self.strategy.select(conflict_set)
            fired.add(chosen.token)
            self._fire(chosen, wm)
            history.append(chosen)

            if goal is not None and wm.contains(goal):
                return RunResult(Status.GOAL, history, wm)

            fp = wm.fingerprint()
            # Only a firing that *changed* the fact set can indicate an
            # oscillation. A no-op firing (asserting an already-present fact) is
            # harmless: refraction guarantees it is consumed, so it never loops.
            if fp != prev_fp:
                if fp in seen_states:
                    return RunResult(Status.CYCLE, history, wm)
                seen_states.add(fp)
            prev_fp = fp

        return RunResult(Status.CAP, history, wm)
