# Pipeline stage 03 — Task generation

**Purpose:** plan task quotas, construct valid task definitions, and expand the
program data when the plan has deficits.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

## Sub-steps

| Sub-step | Responsibility | Doc |
|---|---|---|
| `03a` | Allocate task quotas and quota targets to families; assign splits and construction attempt budgets. | [`03a-allocate-task-quotas/README.md`](03-task-generation/03a-allocate-task-quotas/README.md) |
| `03b` | Construct and validate task definitions into the plan. | [`03b-construct-task-definitions/README.md`](03-task-generation/03b-construct-task-definitions/README.md) |
| `03c` | Resolve deficits by replanning or expanding program data. | [`03c-resolve-deficits.md`](03-task-generation/03c-resolve-deficits.md) |

## Sub-step contracts

| Sub-step | Input model | Output model | Persisted artifact |
|---|---|---|---|
| `03a` | `CadGraph`, `ProgramMetadata`, `ProgramSelection`, dataset release targets, `DeficitLedger`, `ProgramReassignmentRequest` | `TaskQuotaPlan` | Task quota plan Parquet and the support table Parquet. |
| `03b` | `CadGraph`, `TaskQuotaPlan`, `DeficitLedger` | `TaskDefinition`, `DeficitLedger` | Task definitions Parquet and failure records. |
| `03c` | `DeficitLedger`, `TaskQuotaPlan`, family profiles, `ProgramMetadata`, `SelectionPolicy` | `ProgramReassignmentRequest`, `ProgramRequest`, or `AcceptedMiss` | Control records. |

The sub-step docs own the fields and algorithms. This table owns which model and
artifact crosses each sub-step boundary.

## Flow

```text
03a allocate or residual replan
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
- `03b` task-definition construction is parallel per shard. A pass processes the
  programs of its shard one at a time in stable `program_sha256` order; the
  pass loads each program's graph and census once and fills every quota target
  assigned to that program. Accepted definitions are merged with deterministic
  ordering.
- `03c` is a serial controller. Its delegated `01b`/`01c`/`01d`/`02` work is
  parallel inside those stages.

## No full enumeration

The valid-task set is not materialized. `03` samples task definitions into a
task quota plan, with deterministic ordering, deduplication, and backfill. A quota
quota target that cannot be filled is a deficit, not a reason to enumerate the whole
space.

## Task definition

The persisted `TaskDefinition` record, target binding, clue predicates, answer
resolution, validity, and canonical identity are defined in
[`03b-construct-task-definitions/README.md`](03-task-generation/03b-construct-task-definitions/README.md).

## Not here

Prompt rendering, choice rendering, release validation, and export.
