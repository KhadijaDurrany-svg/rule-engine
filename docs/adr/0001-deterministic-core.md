# ADR 0001: A deterministic, reproducible inference core

## Status
Accepted.

## Context
Production-rule engines must choose, on every cycle, which activation in the
conflict set to fire. The result of a whole run depends on that choice. For a
benchmarked, auditable engine we need runs to be a pure function of
`(rule base, strategy, seed)` -- otherwise measured numbers cannot be
reproduced and differential testing against a reference is impossible.

Two common sources of non-determinism had to be removed:

1. **Iteration order of sets/dicts.** Facts and activations must be enumerated
   in a defined order, not Python's hash order.
2. **Unbroken ties in conflict resolution.** If two activations rank equally
   under a strategy, the engine must still pick one deterministically.

## Decision
- Working memory assigns every asserted fact a monotonically increasing integer
  timestamp. Facts of a kind are always enumerated in ascending timestamp order,
  which makes activation enumeration (`seq`) deterministic.
- Every strategy breaks ties on the smallest `seq`. No strategy consults set or
  dict iteration order.
- The only randomness is the explicit `Random` baseline strategy, which draws
  from a seeded `random.Random` indexed into a sorted view of the conflict set.

## Consequences
- A run is fully reproducible; the benchmark manifest records the dataset
  checksum and configuration so numbers can be regenerated bit-for-bit.
- The independent brute-force reference can be compared activation-for-activation
  (see ADR 0003).
- Strategies are limited to total orders over the conflict set. That is exactly
  what classic conflict resolution needs, so this is not a real restriction.
