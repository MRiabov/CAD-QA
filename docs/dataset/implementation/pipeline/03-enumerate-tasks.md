# Pipeline stage 03 — Plan and enumerate tasks

**Purpose:** plan the release, construct valid task definitions, and expand the
program data when the plan has deficits.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

## Sub-steps

| Sub-step | Responsibility | Doc |
|---|---|---|
| `03a` | Plan quotas, family assignment, splits, and attempt budgets. | [`03a-plan-release.md`](03a-plan-release.md) |
| `03b` | Construct and validate task definitions into the plan. | [`03b-construct-task-definitions.md`](03b-construct-task-definitions.md) |
| `03c` | Resolve deficits by replanning or expanding program data. | [`03c-resolve-deficits.md`](03c-resolve-deficits.md) |

## Flow

```text
03a plan
  → 03b construct/sample
  → if deficits: 03c
      fast: ReplanRequest → 03a → 03b
      slow: ProgramRequest → 01b → 01c/01d/02 → 03a → 03b
```

`03c` is a bounded loop back, not a terminal reconciliation step. It stops when
the deficit is filled, the expansion budget is exhausted, or the remaining miss
is accepted and recorded.

## No full enumeration

The valid-task set is not materialized. `03` samples task definitions into a
quota plan, with deterministic ordering, deduplication, and backfill. A quota
cell that cannot be filled is a deficit, not a reason to enumerate the whole
space.

## Task definition

The persisted `TaskDefinition` record, target binding, clue predicates, answer
resolution, validity, and canonical identity are defined in
[`03b-construct-task-definitions.md`](03b-construct-task-definitions.md).

## Not here

Prompt rendering, choice rendering, release validation, and export.
