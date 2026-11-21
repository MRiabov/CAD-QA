# 03a allocate task quotas — plan quantities and families

> Authoritative: `../03-task-generation/03a-allocate-task-quotas/README.md`

READ:

- `CadGraph` per active program from `02c`
- `ProgramMetadata` from `01a`, and `ProgramSelection` from `01b` → `tier`, `cadevolve_program_family_id`, `SelectionPolicy`
- `balance.yaml` → the release policy
- `DeficitLedger`; empty on the first pass
- `ProgramReassignmentRequest` from `03c`
- release targets → `dataset_release_task_count = release.tasks_min`, the exact planned task count; implementation scope

## 1 — Census and policy

TRANSFORM:

- derive the program capability census from each active graph: available target categories, clue constructors, clue operand forms, measurements, answer meanings, and point probes
- store per family the union of member capabilities, summed entity counts, `states_with_point_probe`, `max_task_reasoning_step_count`, split status, `family_task_capacity`, and `family_probe_success_rate`
- a fast-loop replan reuses `family_profiles`; a slow-loop round derives the census only for the added programs
- `03c` reads `family_profiles`, never the census
- read every required `balance.yaml` key; an unknown key at any level is an error
- `task_reasoning_step_share` and `release.splits` each sum to 1 within `1e-9`; every share is in `(0, 1]`; `min <= max` when both are present; `version` is a positive integer
- a missing `min` means no minimum, a missing `max` means no cap, a missing `target` means an equal share among supported values
- `03a` holds no balance number of its own

WRITE:

- (none)

## 2 — Task quotas and quota targets

TRANSFORM:

- define `largest_remainder(total, weights, seed, key)`: normalize the weights, floor each weighted share, distribute the remaining units one at a time to the largest fractional remainders; ties by `sha256(seed || key)`; the counts sum exactly to `total`
- `task_reasoning_step_quota[s] = largest_remainder(dataset_release_task_count, task_reasoning_step_share[s])`; the quotas sum exactly to the task count
- `subset = warmup` at task reasoning step count 1, `main` otherwise; stamp it in the plan so `03b` copies it and `subset_matches_step_count` rechecks it
- for each step count `s` and share-bearing dimension `d`:
  - `supported_values(s, d)` comes from the support-table derivation, filtered by `implementation_scope`
  - `conditional_share(s, d, v) = global_share(v) / sum(global_share(x) for x in supported_values(s, d))`
  - `quota_target_count(s, d, v) = 1 + largest_remainder(task_reasoning_step_quota[s] - supported_value_count, conditional_share(s, d, v))`
  - for clue type, replace `task_reasoning_step_quota[s]` with `planned_clue_occurrences[s]` and `supported_value_count` with the supported clue type count
- clue operand form is coverage-only in P0: one clue occurrence per supported form at each feasible step count, no share
- `baseline_clue_occurrences[s] = task_reasoning_step_quota[s] * (s - 1)`
- `identity_floor = 1` when identity is supported, else 0; `clue_floor = max(0, supported_clue_count - baseline_clue_occurrences[s])`
- `identity_tasks[s] = max(quota_target_count(s, answer_meaning, identity), identity_floor, clue_floor)`; set the identity target count to it
- `planned_clue_occurrences[s] = baseline_clue_occurrences[s] + identity_tasks[s]`
- `remaining_task_quota = task_reasoning_step_quota[s] - identity_tasks[s]`; for each other supported answer meaning: `quota_target_count = 1 + largest_remainder(remaining_task_quota - remaining_supported_count, remaining_conditional_share)`
- bounds, rounded up on the lower side and down on the upper side:
  - task target category: `minimum = 1`; `maximum = floor(dimensions.target_category.max * dataset_release_task_count)`
  - answer format: `minimum = max(1, ceil(0.5 * quota_target_count))`; `maximum = min(floor(2 * quota_target_count), floor(dimensions.answer_format.max * dataset_release_task_count))`; plan minimum `ceil(dimensions.answer_format.min * dataset_release_task_count)`
  - answer meaning: `minimum = max(1, ceil(0.5 * quota_target_count))`; `maximum = min(floor(2 * quota_target_count), floor(dimensions.answer_meaning.max * dataset_release_task_count))`; plan minimum `ceil(dimensions.answer_meaning.min * dataset_release_task_count)`
  - clue type: `minimum = 1`; `maximum = floor(dimensions.clue_type.max * planned_clue_occurrences[s])`
- `supported_value_count > available task or clue count` → `coverage_infeasible`; never drop a supported value
- `remaining_task_quota < remaining_supported_count` → `answer_meaning_infeasible`
- identity not supported with positive `clue_floor` → `clue_coverage_infeasible`; `identity_tasks[s] > task_reasoning_step_quota[s]` → `identity_quota_infeasible`
- a target count that violates a plan cap → move units to a value with slack; no slack → `cap_conflict`

WRITE:

- (none)

## 3 — Families, splits, and target allocation

TRANSFORM:

- count one program per `program_id`: when two selection rows share a `program_id`, use the row with the lexicographically smallest `source_id`, use its family, and exclude the other row from the plan with the conflict recorded
- `usable_program_count = max(1, active_programs_with_graph)`
- `usable_program_count` below `policy.usable_floor` → `capacity_deficit` with detail `program_floor_short`; `03c` promotes reserve programs, and an exhausted reserve leaves an `AcceptedMiss`
- `per_program_task_quota = min(max(1, floor(0.01 * dataset_release_task_count)), max(1, ceil(dataset_release_task_count / usable_program_count)))`
- `family_probe_success_rate = (accepted_probe_tasks + 1) / (attempted_probe_tasks + 2)` when a probe ran, else `1.0`
- `family_task_capacity = floor(program_count * per_program_task_quota * family_probe_success_rate)`
- `split_task_target = largest_remainder(dataset_release_task_count, release.splits)`
- order families by capacity descending, then `sha256(seed || family_id)`; a family is atomic and belongs to exactly one split
- assign families greedily to split targets in that order
- `split_capacity[split] = sum(family_task_capacity)`; zero or below target → `split_capacity_short`
- `family_task_quota = largest_remainder(split_task_target[split], family_task_capacity)`, capped by each capacity; total short → `family_quota_short`
- `family_task_reasoning_step_quota[f] = largest_remainder(family_task_quota[f], task_reasoning_step_quota)`, capped by `family_task_quota[f]`
- per step, dimension, and target: eligible families have the capability and `family_task_reasoning_step_quota[f][s] > 0`
- `family_quota_target_probe_success_rate` uses the same smoothed ratio, `1.0` when no probe ran for that family and target
- `family_quota_target_weight = family_task_reasoning_step_quota[f][s] * family_quota_target_probe_success_rate`
- `family_quota_target_count = largest_remainder(quota_target_count, family_quota_target_weight)`; no eligible family → `quota_target_family_unassigned`
- family target counts are independent across dimensions; never sum them to derive `family_task_quota`
- over-allocation → move the smallest over-allocation to a family with slack; no slack → `family_quota_target_conflict`
- `construction_attempt_budget = ceil(family_quota_target_count * construction_attempt_multiplier)`; `1.5` default, `2.0` for a high-rejection target
- `expansion_rounds = expansion.rounds` and `expansion_growth_share_per_round = expansion.growth_share_per_round` from `balance.yaml`; `03c` reads them from the plan, never from a constant
- `expansion_tier` = the data tier in use: `C` in P0/P1, `C+P` when the P2 P pool is in use
- a reserve program is promoted only through the plan: `03a` records the promotion, `03c` issues the slow-loop `ProgramRequest`, and the program enters at `01d` normalize because it is already fetched

WRITE:

- (none)

## 4 — Acceptance and replan

TRANSFORM:

- accept the plan only when `task_reasoning_step_quota` sums to the task count, every supported value has a target of at least 1, every value is inside its bounds or a conflict is recorded, every family has a split and a quota within capacity, and every target has an eligible family
- `03b` fills these targets in the plan's priority order, scarcest first, and accepts a definition only when it fills an unfilled target and pushes no cell past its maximum
- on `ProgramReassignmentRequest`, compute the remaining amounts:
  - `remaining_quota_target_count = max(0, new_quota_target_count - accepted_quota_target_count)`
  - `remaining_task_reasoning_step_quota = max(0, new_task_reasoning_step_quota - accepted_task_reasoning_step_count)`
  - `remaining_family_task_quota = max(0, new_family_task_quota - accepted_family_task_count)`
  - `remaining_family_task_reasoning_step_quota = max(0, new_family_task_reasoning_step_quota - accepted_family_task_reasoning_step_count)`
  - `remaining_quota_target_minimum = max(0, minimum - accepted_quota_target_count)`
  - `remaining_clue_occurrence_count = max(0, planned_clue_occurrences - accepted_clue_occurrence_count)`
  - `remaining_construction_attempt_budget = ceil(remaining_quota_target_count * construction_attempt_multiplier)`
- allocate the remaining amounts with the same equations, using `remaining_quota_target_minimum` and `remaining_clue_occurrence_count`; do not allocate the absolute targets again
- do not move an accepted task to another family or split; a family with accepted tasks keeps its split
- accepted definitions are immutable while the program, CAD graph, and definition-rule versions are unchanged; when any of them changes, do not reuse them and start a new plan
- reject the request and keep the current plan version when a new absolute target is below its accepted count, a bound is exceeded, or the step quotas do not sum to the task count
- increment `plan_version`, set `parent_plan_version`; the previous plan and accepted definitions stay immutable
- do not fetch, normalize, or execute

WRITE:

- `TaskQuotaPlan` `(plan_version, seed, balance_policy_version)` → `seed, parent_plan_version, balance_policy_sha256, task_reasoning_step_quotas, quota_targets, clue_quotas, clue_occurrences, family_profiles, family_assignment, construction_attempt_budgets, construction_attempt_multiplier, expansion_tier, expansion_rounds, expansion_growth_share_per_round, subset`
- allocation details → `DeficitLedger` (`coverage_infeasible`, `answer_meaning_infeasible`, `clue_coverage_infeasible`, `identity_quota_infeasible`, `cap_conflict`, `split_capacity_short`, `family_quota_short`, `quota_target_family_unassigned`, `family_quota_target_conflict`)
- the plan is a target; it does not prove that the corpus can supply it
