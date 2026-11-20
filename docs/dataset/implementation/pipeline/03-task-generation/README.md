# Task generation module

**Status:** draft, 2026-11-20. Working contract for pipeline stage `03`.

This document is the entry point for the `03` task-generation module. It states
what the module consumes, what it produces, how the sub-steps divide the work,
and where each contract lives. The sub-step input/output table stays in
[`../03-task-generation.md`](../03-task-generation.md).

Task generation is a module rather than a single step because it owns three
sub-steps, a search, a validity contract, and a bounded feedback loop. The
construction algorithm lives in `algorithm/`, the support table contract lives in
`support/`, and decisions scoped to this module live in `decisions.md`.

## Input

- `CadGraph` from `02c`, one per active program;
- `ProgramMetadata` from `01b`, including family, split, and program tier;
- task reasoning step support tables from `05`;
- dataset release targets from the release contract;
- `DeficitLedger` from the previous pass, empty on the first pass;
- `ProgramReassignmentRequest` when `03c` chose the fast loop.

## Output

- `TaskDefinition` records, one per accepted task, with the answer evidence and
  the answer-equivalent set;
- `DeficitLedger`, carrying every unfilled quota target and the rejection
  reason that produced it;
- control records from `03c`: `ProgramReassignmentRequest`, `ProgramRequest`,
  or `AcceptedMiss`.

## Process

```text
CadGraph ──► 03a allocate quotas ──► TaskQuotaPlan
                                        │
                                        ▼
                                   03b construct tasks ──► TaskDefinition
                                        │
                                        ▼
                                   deficit? ──► 03c
                                                  ├── fast: reassign ──► 03a
                                                  ├── slow: request programs ──► 01b
                                                  └── accept the miss
```

The loop is bounded. It stops when the deficit is filled, the expansion budget
is exhausted, or the remaining miss is accepted and recorded.

## Documents

| Doc | Contract |
|---|---|
| [`03a-allocate-task-quotas.md`](03a-allocate-task-quotas.md) | Quota allocation to families, splits, and attempt budgets. |
| [`03b-construct-task-definitions.md`](03b-construct-task-definitions.md) | Task validity, identity, step accounting, and attempt budgets. |
| [`03c-resolve-deficits.md`](03c-resolve-deficits.md) | Deficit classification, replanning, and program requests. |
| [`decisions.md`](decisions.md) | Decisions scoped to this module. |

## Algorithm and support

| Doc | Contract |
|---|---|
| [`algorithm/construction.md`](algorithm/construction.md) | How a task is found: possible answers, facts, cover search, validity checks, acceptance. |
| [`support/clue-form-by-step.md`](support/clue-form-by-step.md) | Which clue forms are supported at each task reasoning step count. |

The clue model itself is in
[`03b-construct-task-definitions.md`](03b-construct-task-definitions.md): the
clue types, the reference binding, and the clue operand form. The vocabulary is
owned by `docs/dataset/requirements/task-structure.md`; this module references it
and does not restate it.
