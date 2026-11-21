# 03b construct task definitions — answer-bearing records

> Authoritative: `../../../03-task-generation/03b-construct-task-definitions/README.md`
> Models: `../../models/03-task-generation.md`

This folder mirrors the authoritative `03b` folder. The boundary for this pipeline stage is here;
the three phases are the lettered sub-documents.

READ:

- `CadGraph` from `02c`
- `TaskQuotaPlan` from `03a` → `quota_targets`, `program_census`, `construction_attempt_budgets`, `family_assignment`
- `DeficitLedger` on resume; empty on the first run

WRITE:

- `TaskDefinition` Parquet `(task_id)` → the fields declared in `../../models/03-task-generation.md`
- `choice_pool` is empty for every non-multiple-choice task
- `DeficitLedger` `(plan_version, update sequence)` → accepted and rejected counts by quota target, family, step count, and rejection reason; a `DeficitClass` value (`probe_deficit`, `construction_deficit`) where known
- failure partition `03b_construct_task_definitions`

## Phases

| Doc | Phase |
|---|---|
| [`a-construction.md`](a-construction.md) | Bind the target, build the clue chain, run the validity gates, and sample into the plan. |
| [`b-answer-semantics.md`](b-answer-semantics.md) | Resolve the answer, build the choice pool, and define answer equality. |
| [`c-definition-identity.md`](c-definition-identity.md) | Canonical order, serialization, the three hashes, and provenance. |

## Rules

- The definition is complete enough to reproduce the task without re-running construction; `04` renders it and never recomputes an answer.
- A rejected definition writes a failure row and consumes no quota.
- An underfilled target is a deficit for `03c`; `03b` does not loop.
