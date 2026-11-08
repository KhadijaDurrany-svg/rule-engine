"""rulekiln -- a deterministic forward-chaining rule engine.

A compact, dependency-free production-rule (inference) engine: condition->action
rules fire against a working memory of facts using the classic match / resolve /
act cycle, with pluggable conflict-set resolution (priority, specificity,
recency and lexical combinations), refraction, and cycle detection.

It is *not* a task scheduler: there are no tasks, dependencies, workers or
async execution. The unit of work is a logical rule firing that transforms a set
of facts, and the engine's correctness is verified differentially against an
independent brute-force reference.
"""

from __future__ import annotations

from .activation import Activation
from .engine import Engine, RunResult, Status
from .facts import Fact, WorkingMemory
from .patterns import Pattern, bind, cmp, eq, var_cmp
from .reference import run_reference
from .rules import Assert, Retract, Rule, RuleBase
from .strategies import (
    Lexical,
    Priority,
    Random,
    Recency,
    Specificity,
    Strategy,
    Unordered,
    default_strategy,
)

__version__ = "0.1.0"

__all__ = [
    "Activation",
    "Assert",
    "Engine",
    "Fact",
    "Lexical",
    "Pattern",
    "Priority",
    "Random",
    "Recency",
    "Retract",
    "Rule",
    "RuleBase",
    "RunResult",
    "Specificity",
    "Status",
    "Strategy",
    "Unordered",
    "WorkingMemory",
    "bind",
    "cmp",
    "default_strategy",
    "eq",
    "run_reference",
    "var_cmp",
    "__version__",
]
