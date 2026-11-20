# Program capability census

**Parent:** [`../README.md`](../README.md).

**Status:** draft, 2026-11-20. Emitted by `02c`; consumed by `03a`, `03b`, and
`03c`.

## Purpose

The census is one summary per program of the task shapes its graph can support.
It lets `03a` send quota targets to programs that can fill them, and lets `03b`
skip clue operand forms this graph cannot build, before any construction attempt.

It is not a release artifact. The release feasibility tables
([`task-step-support.md`](../../../task-step-support.md)) answer what the task
grammar permits at a step count. The census answers what one graph offers.

## Contents

| Field | Meaning |
|---|---|
| `target_categories` | Entity kinds present in the state that a task can target. |
| `clue_constructors` | Relations and measurements that can become a clue. |
| `clue_operand_forms` | Per clue type, the forms the graph can resolve. |
| `measurements` | Measurement kinds present, per scope. |
| `answer_meanings` | Answer meanings the graph can resolve. |
| `max_task_reasoning_step_count` | Longest chain the graph can support, from the candidate set size. |
| `entity_counts` | Candidates per target category, used for the scarcity ranking. |

## Derivation

- Per-entity measurements are total over their scope, so a measurement capability
  is present when the entity kind is present.
- Pair elements exist only for the pairs the pair emission rule allows
  (`graph-content.md` section 4.1).
- Structural rules: the property clue type has no clue operand form; `selected` needs
  an earlier clue, so it is absent at step count 1; `aggregation` with an
  `aggregated` reference is degenerate; `cross_state` is P2.
- A capability is present only when the graph asserts the relation or
  measurement, and its evidence is present.

## Consumers

| Consumer | Use |
|---|---|
| `03a` | Sends quota targets to programs whose census can fill them; ranks by scarcity. |
| `03b` | Skips clue operand forms the graph cannot build, so a construction attempt is not wasted. |
| `03c` | Turns an underfilled target into a capability deficit when no active program has the capability. |

## Versioning

The census is versioned with the graph artifact. A mismatch between the census
version and the graph version is rejected, not reconciled.

## Failure

A missing capability is a deficit. A capability that is present but yields no
valid task is a construction failure in `03b`, not a census error. The census is
a filter, not an oracle.
