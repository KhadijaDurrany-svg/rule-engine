# ADR 0003: Instance-based refraction and conservative cycle detection

## Status
Accepted.

## Context
Forward chaining can fire forever. Two mechanisms keep it bounded:

- **Refraction**: an activation should not re-fire on the same data.
- **Termination guarantee**: even with retraction (non-monotonic rules), the
  engine must stop rather than loop.

How refraction is keyed matters. If keyed on fact *content*, retracting a fact
and re-asserting an equal one would never re-fire dependent rules, which is
surprising and diverges from established engines. If keyed on the fact
*instance*, re-assertion is a fresh instance and can re-fire -- which is the
CLIPS behaviour, but reopens the door to infinite oscillation.

## Decision
- Refraction is keyed on the matched facts' assertion **timestamps** (the
  working-memory instances), via `Activation.token = (rule_name, stamps)`. An
  add-only rule base has a finite set of instances, each token fires once, so it
  always terminates.
- A separate **cycle detector** guards non-monotonic bases: the engine
  fingerprints the fact set after each firing and halts with `Status.CYCLE` the
  first time a firing *changes* the fact set to a configuration already seen.
  No-op firings (asserting an already-present fact) do not trigger it, since
  refraction already bounds them.
- A hard firing `cap` (default 10,000) is the final backstop, surfaced as
  `Status.CAP`.

## Consequences
- Every run terminates with an explicit status: `quiescent`, `goal`, `cycle`,
  or `cap`.
- The cycle detector is *conservative*: it halts on the first revisited
  configuration. A pathological base that revisits a configuration yet would
  still eventually terminate is reported as a cycle. This trades a little
  completeness for a hard termination guarantee, and is documented under
  Known gaps.
