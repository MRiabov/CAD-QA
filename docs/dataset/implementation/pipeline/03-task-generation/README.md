# Task generation module

**Status:** draft, 2026-11-20. Working contract for pipeline stage `03`.

This document is the entry point for the `03` task-generation module. It states
what the module consumes, what it produces, how the sub-steps divide the work,
and where each contract lives. The sub-step input/output table stays in
[`../03-task-generation.md`](../03-task-generation.md).

Task generation is a module rather than a single step because it owns three
sub-steps, a search, a validity contract, and a bounded feedback loop. The
mechanisms live in `algorithm/`, the per-item field contracts live in
`features/`, and decisions scoped to this module live in `decisions.md`.

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

## Planned splits

The module contract is being written now. These documents will carry the detail
that does not belong in the sub-step contracts:

| Planned doc | Scope |
|---|---|
| `algorithm/clue-grammar.md` | A clue is one narrowing statement; clue type and clue operand form; the support grid. |
| `algorithm/possible-answer-sets.md` | How the target category and state scope define the candidate set. |
| `algorithm/chain-search.md` | Cover search, clue ordering, and termination. |
| `algorithm/uniqueness.md` | The answer-equivalent set and the equality relation per answer meaning. |
| `algorithm/answer-resolution.md` | How the answer step turns the final set into one answer. |
| `algorithm/quota-scheduling.md` | Plan filling, the deficit ledger, and the forced-task flag. |
| `algorithm/choice-pool.md` | Where multiple-choice options come from and when they are available. |
| `features/clue-types.md` | Per clue type: what it asserts, support, and examples. |
| `features/answer-meanings.md` | Per answer meaning: equality rule and compatible answer formats. |
| `features/target-categories.md` | Per target category: entity set and available measurements. |
| `support/clue-form-by-step.md` | Contract for the clue-form support table. |
