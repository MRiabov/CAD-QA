# Program capability census

**Parent:** [`../README.md`](../README.md).

**Status:** draft, 2026-11-20. Derived on demand from the graph by `03a` and
`03b`; never stored as an artifact.

## Purpose

The census is one summary per program of the task shapes its graph can support.
It lets `03a` send quota targets to programs that can fill them, and lets `03b`
skip clue operand forms this graph cannot build, before any construction attempt.

It is not a release artifact and not a pipeline artifact. The release
feasibility tables ([`task-step-support.md`](../../../task-step-support.md))
answer what the task grammar permits at a step count. The census answers what one
graph offers.

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
| `states_with_point_probe` | Solid states with at least one surviving point probe, so a membership task can bind them. |

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
| `03a` | Derives it for every active program to assign quota targets and rank by scarcity, then stores the union per family in `family_profiles`. |
| `03b` | Derives it for the program it is constructing and skips clue operand forms the graph cannot build. |
| `03c` | Reads `family_profiles` in the plan; it does not derive the census. |

## Ownership

The census is a function of the graph, not an artifact. It is derived on demand
and never written as a Parquet table.

- One implementation serves both callers. A second derivation would be a second
  definition of what a graph can support.
- `03a` derives it for all active programs in one pass and stores the union per
  family in `TaskQuotaPlan.family_profiles`. That projection is what `03c` reads.
- `03b` derives it for one program from the graph it is already reading.
- Nothing is versioned separately. The census is a function of the graph, so a
  changed graph produces a changed census by construction; there is no copy that
  can go stale.

A full pass over the graph costs a few seconds, and `03a` re-enters once per plan
revision. That is not enough to justify a separate artifact, schema, and
staleness rule.

## Failure

A missing capability is a deficit. A capability that is present but yields no
valid task is a construction failure in `03b`, not a census error. The census is
a filter, not an oracle.
