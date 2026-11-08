# ADR 0002: Nested-loop join instead of a Rete network

## Status
Accepted.

## Context
The canonical fast matcher for production systems is the Rete algorithm, which
caches partial matches in a dataflow network and incrementally updates them as
facts change. Rete is the right choice when throughput on large, slowly changing
fact bases dominates. It is also intricate: alpha/beta memories, join nodes,
token propagation and retraction bookkeeping are easy to get subtly wrong.

This project's goal is a *correct, inspectable* engine with pluggable conflict
resolution, verified against an independent reference and used to study
resolution quality -- not a high-throughput runtime.

## Decision
Match each rule with a straightforward deterministic nested-loop join over
working memory (`match_condition`): extend a frontier of binding environments
one pattern at a time, enumerating candidate facts in timestamp order.
Negation-as-failure patterns are checked against the current environment.

## Consequences
- The matcher is small, obviously correct, and easy to reason about.
- It recomputes matches each cycle, which is `O(rules x product of candidates)`.
  For the engine's intended scale (hundreds of rules, thousands of facts) this is
  fine; for very large fact bases it would be the first thing to optimise.
- Because the reference engine uses a *different* naive strategy (full Cartesian
  product), agreement between the two is a meaningful cross-check rather than two
  copies of the same code.
- A Rete backend could later be added behind the same `Engine` API without
  changing rule, strategy or benchmark code. Listed under Known gaps.
