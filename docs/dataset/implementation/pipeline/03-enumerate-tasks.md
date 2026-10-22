# Pipeline stage 03 — Plan and enumerate tasks

**Purpose:** plan the release, construct valid task definitions, and expand the
program data when the plan has deficits.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

## Sub-steps

| Sub-step | Responsibility | Doc |
|---|---|---|
| `03a` | Allocate task quotas and quota cells to families; assign splits and sampling budgets. | [`03a-allocate-task-quotas.md`](03a-allocate-task-quotas.md) |
| `03b` | Construct and validate task definitions into the plan. | [`03b-construct-task-definitions.md`](03b-construct-task-definitions.md) |
| `03c` | Resolve deficits by replanning or expanding program data. | [`03c-resolve-deficits.md`](03c-resolve-deficits.md) |

## Sub-step contracts

| Sub-step | Input model | Output model | Persisted artifact |
|---|---|---|---|
| `03a` | `CadGraph`, `ProgramMetadata`, task reasoning step support tables, dataset release targets, `ProgramReassignmentRequest` | `ReleasePlan` | Release plan Parquet or JSON. |
| `03b` | `CadGraph`, `ReleasePlan` | `TaskDefinition`, `DeficitLedger` | Task definitions Parquet and failure records. |
| `03c` | `DeficitLedger`, `ReleasePlan`, family profiles, `ProgramMetadata` | `ProgramReassignmentRequest`, `ProgramRequest`, or `AcceptedMiss` | Control records. |

The sub-step docs own the fields and algorithms. This table owns which model and
artifact crosses each sub-step boundary.

## Flow

```text
03a allocate
  → 03b construct/sample
  → if deficits: 03c
      fast: ProgramReassignmentRequest → 03a → 03b
      slow: ProgramRequest → 01b → 01c/01d/02 → 03a → 03b
```

`03c` is a bounded loop back, not a terminal reconciliation step. It stops when
the deficit is filled, the expansion budget is exhausted, or the remaining miss
is accepted and recorded.

## Language and parallelism

- **Go:** `03a`, `03b`, `03c`; no Python is needed after graph construction.
- `03a` task-quota allocation is a global allocation and is not parallelizable.
  Family profile building may be parallel per family, with one merge step.
- `03b` task-definition construction is parallel per program, family, and quota
  cell. Each batch is independent; accepted definitions are merged with
  deterministic ordering.
- `03c` is a serial controller. Its delegated `01b`/`01c`/`02` work is parallel
  inside those stages.

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
