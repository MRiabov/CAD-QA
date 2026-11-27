# 03a allocate task quotas — plan quantities and families

> Authoritative: `../../../03-task-generation/03a-allocate-task-quotas/README.md`
> Models: `../../models/03-task-generation.md`

This folder mirrors the authoritative `03a` folder. The boundary for this pipeline stage is here;
the four phases are the lettered sub-documents.

READ:

- `CadGraph` per active program from `02c`
- `ProgramMetadata` from `01a` → `source_id`, `source_collection`, `path_family`, `source_feature_tags`
- `ProgramSelection` from `01b` → `rows[].tier`, `rows[].cadevolve_program_family_id`, `SelectionPolicy`
- `balance.yaml` → the release policy
- the support-table derivation → `supported_values`; `03a` writes the single table to `support/support.parquet`
- `DeficitLedger`; empty on the first pass
- `ProgramReassignmentRequest` from `03c`
- release targets → `dataset_release_task_count = release.tasks_min`, the exact planned task count; implementation scope

WRITE:

- `TaskQuotaPlan` `(plan_version, seed, balance_policy_version)` → the fields declared in `../../models/03-task-generation.md`
- `support/support.parquet` → the task reasoning step support table; `TaskQuotaPlan.support_table_sha256` records its hash
- allocation details → `DeficitLedger.entries[].allocation_detail` with an `AllocationDetail` value (`coverage_infeasible`, `answer_meaning_infeasible`, `clue_coverage_infeasible`, `identity_quota_infeasible`, `cap_conflict`, `split_capacity_short`, `family_quota_short`, `quota_target_family_unassigned`, `family_quota_target_conflict`)
- the plan is a target; it does not prove that the corpus can supply it

## Phases

| Doc | Phase |
|---|---|
| [`a-support-derivation.md`](a-support-derivation.md) | Derive the program capability census, the family profiles, and the supported values. |
| [`b-balance.md`](b-balance.md) | Load the balance policy and compute the conditional share. |
| [`c-quota-allocation.md`](c-quota-allocation.md) | Allocate step quotas, quota targets, family quotas, splits, and attempt budgets. |
| [`d-replan.md`](d-replan.md) | Apply a `ProgramReassignmentRequest` as a residual plan revision. |

## Rules

- `03a` holds no balance number of its own.
- A fast-loop replan reuses `family_profiles`; a slow-loop round derives the census only for the added programs.
- `03c` reads `family_profiles`, never the census.
- A plan revision is a new part keyed by `plan_version`; accepted definitions stay immutable.
