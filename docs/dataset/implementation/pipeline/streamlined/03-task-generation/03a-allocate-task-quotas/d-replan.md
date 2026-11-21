# 03a/d replan — residual allocation after a deficit

> Authoritative: `../../../03-task-generation/03a-allocate-task-quotas/d-replan.md`
> Models: `../../models/03-task-generation.md`

## Replan — residual allocation

READ:

- the current `TaskQuotaPlan` → absolute targets, `family_assignment`, `clue_occurrences`
- the current `DeficitLedger` → accepted counts per quota target, family, and task reasoning step count
- `ProgramReassignmentRequest` from `03c`

TRANSFORM:

- on `ProgramReassignmentRequest`, compute the remaining amounts:
  - `remaining_quota_target_count = max(0, new_quota_target_count - accepted_quota_target_count)`
  - `remaining_task_reasoning_step_quota = max(0, new_task_reasoning_step_quota - accepted_task_reasoning_step_count)`
  - `remaining_family_task_quota = max(0, new_family_task_quota - accepted_family_task_count)`
  - `remaining_family_task_reasoning_step_quota = max(0, new_family_task_reasoning_step_quota - accepted_family_task_reasoning_step_count)`
  - `remaining_quota_target_minimum = max(0, minimum - accepted_quota_target_count)`
  - `remaining_clue_occurrence_count = max(0, planned_clue_occurrences - accepted_clue_occurrence_count)`
  - `remaining_construction_attempt_budget = ceil(remaining_family_task_reasoning_step_quota * construction_attempt_multiplier)`
- allocate the remaining amounts with the same equations, using `remaining_quota_target_minimum` and `remaining_clue_occurrence_count`; do not allocate the absolute targets again
- a clue type with accepted clue occurrences has a remaining minimum of zero
- do not move an accepted task to another family or split; a family with accepted tasks keeps its split
- accepted definitions are immutable while the program, CAD graph, and definition-rule versions are unchanged; when any of them changes, do not reuse them and start a new plan
- reject the request and keep the current plan version when a new absolute target is below its accepted count, a bound is exceeded, the step quotas do not sum to the task count, or a family with accepted tasks would change split
- increment `plan_version`, set `parent_plan_version`; the previous plan and accepted definitions stay immutable
- do not fetch, normalize, or execute
- record the allocation detail from the pass; `03c` maps it to a `DeficitClass`

WRITE:

- `TaskQuotaPlan` `(plan_version, seed, balance_policy_version)` → `seed, parent_plan_version, balance_policy_sha256, task_reasoning_step_quotas, quota_targets, clue_quotas, clue_occurrences, program_census, family_profiles, family_assignment, construction_attempt_budgets, construction_attempt_multiplier, expansion_tier, expansion_rounds, expansion_growth_share_per_round, subset`
- allocation details → `DeficitLedger.entries[].allocation_detail` with an `AllocationDetail` value (`coverage_infeasible`, `answer_meaning_infeasible`, `clue_coverage_infeasible`, `identity_quota_infeasible`, `cap_conflict`, `split_capacity_short`, `family_quota_short`, `quota_target_family_unassigned`, `family_quota_target_conflict`)
