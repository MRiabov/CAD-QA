# Program capability census

**Parent:** [`../README.md`](../README.md).

**Status:** draft, 2026-11-20. Derived on demand from the graph by `03a` and
`03b`; never stored as an artifact.

## Purpose

The census is one summary per program of the task shapes its graph can support.
It lets `03a` send quota targets to programs that can fill them, and lets `03b`
skip clue reduction forms this graph cannot build, before any construction attempt.

It is not a release artifact and not a pipeline artifact. The release
feasibility tables ([`task-step-support.md`](../../../task-step-support.md))
answer what the task grammar permits at a step count. The census answers what one
graph offers.

## Contents

| Field | Meaning |
|---|---|
| `target_categories` | Entity kinds present in the state that a task can target. |
| `clue_constructors` | Relations and measurements that can become a clue. |
| `clue_reduction_forms` | Per clue type, the forms the graph can resolve. |
| `measurements` | Measurement kinds present, per scope. |
| `answer_meanings` | Answer meanings the graph can resolve. |
| `max_task_reasoning_step_count` | Per target category and answer meaning, the longest chain the graph can support. An identity answer uses the candidate count; a value answer uses the number of distinct answers under `same_answer`; both cap at 10. |
| `entity_counts` | Candidates per target category, used for the scarcity ranking. |
| `states_with_point_probe` | Solid states with at least one surviving point probe, so a membership task can bind them. |

## Derivation

- Per-entity measurements are total over their scope, so a measurement capability
  is present when the entity kind is present.
- `max_task_reasoning_step_count[target_category][answer_meaning]` follows the
  necessary-clue bound in `task-structure.md` section 2.2. A value answer with
  `m` distinct answers supports at most `m` task reasoning steps; an identity
  answer supports at most its candidate count. Both cap at the release maximum
  of 10.
- Pair elements exist only for the pairs the pair emission rule allows
  (`graph-content.md` section 4.1).
- Structural rules: the property clue type has no clue reduction form; `selected_in_earlier_clue` needs
  an earlier clue, so it is absent at step count 1; `aggregation` with an
  `aggregated` reference is degenerate; `cross_state` is P2.
- A capability is present only when the graph asserts the relation or
  measurement, and its evidence is present.

## Consumers

| Consumer | Use |
|---|---|
| `03a` | Derives it for every active program to assign quota targets and rank by scarcity, then stores the per-program census in `program_census` and the union per family in `family_profiles`. It never assigns a quota target above the program's `max_task_reasoning_step_count` for that target category and answer meaning. |
| `03b` | Reads its program's census from the plan and skips clue reduction forms the graph cannot build; it re-derives only when the entry is absent or its `graph_identity_sha256` differs. |
| `03c` | Reads `family_profiles` in the plan; it does not derive the census. |

## Ownership

The census is a function of the graph, not an artifact. It is derived on demand
and never written as a Parquet table.

- One implementation serves both callers. A second derivation would be a second
  definition of what a graph can support.
- `03a` derives it for all active programs in one pass and stores two
  projections in the plan: the per-program census in `program_census`, keyed by
  `program_sha256` and `graph_identity_sha256`, and the union per family — capabilities
  and summed entity counts — in `TaskQuotaPlan.family_profiles`. That family
  projection is what `03c` reads.
- `03b` reads its program's entry from `program_census` instead of deriving it a
  second time. It re-derives only when the entry is absent or its `graph_identity_sha256` does
  not match the graph it is reading.
- Nothing is versioned separately. The census is a function of the graph, so a
  changed graph produces a changed census by construction; the plan entry is
  keyed by `graph_identity_sha256`, so a stale copy cannot be used.

Derivation is bounded by the graph, not by the plan:

| Event | Graph changed | Census work |
|---|---|---|
| First plan | — | One pass over the pool. |
| Fast-loop replan | No | None. `03a` and `03b` read `program_census` and `family_profiles`. |
| Slow-loop round | At most 20% more programs | One pass over the added programs. |

A replan does not derive the census again, because the graph batch has not
changed and the family projection is already in the plan. That keeps the cost
independent of how many replans a run needs.

## Failure

A missing capability is a deficit. A capability that is present but yields no
valid task is a construction failure in `03b`, not a census error. The census is
a filter, not an oracle.
