# Task generation module

**Status:** draft, 2026-11-20. Working contract for pipeline stage `03`.

This document is the entry point for the `03` task-generation module. It states
what the module consumes, what it produces, how the sub-steps divide the work,
and where each contract lives. The sub-step input/output table stays in
[`../03-task-generation.md`](../03-task-generation.md).

Task generation is a module rather than a single step because it owns three
sub-steps, a search, a validity contract, and a bounded feedback loop. `03a` and
`03b` are folders: each holds the contract for its pipeline stage in `README.md` and its
sub-documents under lettered names (`a-`, `b-`, `c-`). The capability census
lives in `algorithm/`, and decisions scoped to this module live in `decisions.md`.

## Input

- `CadGraph` from `02c`, one per active program;
- `ProgramMetadata` from `01a`;
- `ProgramSelection` from `01b`, including family, split, and program tier;
- dataset release targets from the release contract;
- the release implementation scope;
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
| [`03a-allocate-task-quotas/README.md`](03a-allocate-task-quotas/README.md) | Quota allocation to families, splits, and attempt budgets. |
| [`03a-allocate-task-quotas/a-support-derivation.md`](03a-allocate-task-quotas/a-support-derivation.md) | The support-table derivation and the program capability census. |
| [`03a-allocate-task-quotas/b-balance.md`](03a-allocate-task-quotas/b-balance.md) | The balance policy and the conditional share. |
| [`03a-allocate-task-quotas/c-quota-allocation.md`](03a-allocate-task-quotas/c-quota-allocation.md) | The plan, quota targets, allocation equations, family assignment, and attempt budgets. |
| [`03a-allocate-task-quotas/d-replan.md`](03a-allocate-task-quotas/d-replan.md) | Residual replanning and the deficit details `03a` records. |
| [`03b-construct-task-definitions/README.md`](03b-construct-task-definitions/README.md) | Task validity, identity, step accounting, and attempt budgets. |
| [`03b-construct-task-definitions/a-construction.md`](03b-construct-task-definitions/a-construction.md) | Graph boundary, target binding, clue schema, validity, and the search algorithm. |
| [`03b-construct-task-definitions/b-answer-semantics.md`](03b-construct-task-definitions/b-answer-semantics.md) | Answer step, format, multiple-choice pool, resolver, evidence, and equality. |
| [`03b-construct-task-definitions/c-definition-identity.md`](03b-construct-task-definitions/c-definition-identity.md) | Canonical order, serialization, the three hashes, and provenance. |
| [`03c-resolve-deficits.md`](03c-resolve-deficits.md) | Deficit classification, replanning, and program requests. |
| [`decisions.md`](decisions.md) | Decisions scoped to this module. |

## Algorithm

| Doc | Contract |
|---|---|
| [`algorithm/program-capability-census.md`](algorithm/program-capability-census.md) | Per-program summary of the task shapes its graph can support. |

The clue model itself is in
[`03b-construct-task-definitions/README.md`](03b-construct-task-definitions/README.md):
the clue types, the reference binding, and the clue reduction form. The vocabulary
is owned by `docs/dataset/requirements/task-structure.md`; this module references
it and does not restate it.
