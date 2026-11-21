# Quota allocation

**Parent:** [`README.md`](README.md).

## Task quota plan

`dataset_release_task_count` is the exact number of tasks the plan allocates. It
is `release.tasks_min` from `balance.yaml`: the plan total and the release floor
are one number, so the plan cannot promise fewer tasks than the release requires.

`TaskQuotaPlan` contains:

| Field | Meaning |
|---|---|
| `plan_version`, `parent_plan_version`, `seed` | Version, previous version, and deterministic ordering seed. |
| `balance_policy_version`, `balance_policy_sha256` | The balance policy the plan was computed from. A changed policy produces a new plan version. |
| `task_reasoning_step_quotas` | Target task count for each task reasoning step count. |
| `quota_targets` | Quota targets: task reasoning step count, quota dimension, dimension value, minimum, target count, maximum, and priority. |
| `clue_quotas` | Clue quotas counted over clue occurrences. |
| `clue_occurrences` | Planned clue occurrences for each task reasoning step count. |
| `program_census` | The census of each active program, keyed by `program_sha256` and the graph part hash, so `03b` reads it instead of deriving it again. |
| `family_profiles` | The union of the member programs' census capabilities and summed entity counts, `states_with_point_probe`, `max_task_reasoning_step_count`, split status, family task capacity, and probe success rate per CADEvolve program family. |
| `family_assignment` | Family to split, task quota, per-task-reasoning-step task quotas, and assigned quota targets. |
| `construction_attempt_budgets` | One construction batch per family and task reasoning step count for the remaining work in this plan revision. |
| `construction_attempt_multiplier` | Construction attempt multiplier over the family's task reasoning step quota; default 1.5, or 2.0 for a high-rejection family and step count. |
| `expansion_tier`, `expansion_rounds`, `expansion_growth_share_per_round` | Current data tier before a deficit triggers `03c`, and the stop rule stamped from `expansion` in `balance.yaml`. |
| `subset` | The warmup and main rule: `warmup` at task reasoning step count 1, `main` otherwise. `03b` stamps it on each definition. |

The plan stores absolute targets; accepted and remaining counts live in the
`DeficitLedger`. The plan is a target; it does not prove that the corpus can
supply every quota target.

## Quota targets

A quota target is a count target for one quota dimension value at one task
reasoning step count. It is not a complete task. For example, a task with a task
reasoning step count of 3, task target category `face`, answer meaning `area`,
answer format `number`, clue types `relation` and `property`, and clue operand
forms `named` and none contributes to these quota targets:

- `(3, target_category, face)`;
- `(3, answer_meaning, area)`;
- `(3, answer_format, number)`;
- `(3, clue_type, relation)`;
- `(3, clue_type, property)`;
- `(3, clue_operand_form, named)`.

The task is one task, counted in several quota targets. A quota target records:

- `minimum`: coverage requirement;
- `quota_target_count`: desired count;
- `maximum`: balance or cap limit;
- `priority`: coverage first, then balance, then volume.

Plan five separate quota dimensions:

- task target category;
- clue type;
- clue operand form, as a coverage dimension in P0 and a balance dimension in
  P1;
- answer meaning;
- answer format.

Four of these carry a share and are allocated by the equations below. Clue
operand form is coverage-only in P0 (`DS-REQ-18`): its target count is the coverage
floor of one clue occurrence per supported form at each step count, and it has no
balance share, because a balance range is vacuous at a step count where a form
cannot exist. Balance over clue operand form is P1. This is a P0
simplification, not a property of the release: coverage guarantees presence, not
a useful mix, so one form can carry most clues and still pass.

Do not create a full task target category × clue type × clue operand form ×
answer meaning × answer format cross-product. The requirements are independent:
coverage and balance at each task reasoning step count, not every joint
combination. A task contributes to one task target category, one answer format,
one answer meaning, one task reasoning step count, and one or more clue
occurrences; each task clue with a reference contributes its clue operand form.

Clue quotas are over clue occurrences, because one task has several task clues.

## Allocation equations

Define `largest_remainder(total, weights, seed, key)` as: normalize the weights,
floor each weighted share, then distribute the remaining units one at a time to
the largest fractional remainders; break ties by `sha256(seed || key)`. It returns
one integer count per weight, and the counts sum exactly to `total`.

### Task reasoning step quotas

`task_reasoning_step_quota[task_reasoning_step_count] = largest_remainder(dataset_release_task_count, task_reasoning_step_share[task_reasoning_step_count])`.

Use `task_reasoning_step_share` from `balance.yaml`; 5%, 10%, 30%, 25%, 15%, 7%,
4%, 2%, 1%, and 1% is the default. The 6–10 tail is P1 and is used only when the
6–10 release gate in `requirements/PRD.md` section 6.1 passes. When the release gate is closed, the
release policy sets `task_reasoning_step_share` to the
`task_reasoning_step_share_p0_fallback` values and bumps `version`.
`task_reasoning_step_quota[1]` is the warmup quota. Allocate the exact dataset
release task count; do not round each task reasoning step count independently
and leave a residual.

### Quota target counts

For each task reasoning step count and each share-bearing quota dimension:

- `supported_values(task_reasoning_step_count, quota_dimension)` is the output of
  the support-table derivation; see
  [`a-support-derivation.md`](a-support-derivation.md).
- `conditional_share(task_reasoning_step_count, quota_dimension, dimension_value)`
  is defined in [`b-balance.md`](b-balance.md#conditional-share).
- `quota_target_count(task_reasoning_step_count, quota_dimension, dimension_value) = 1 + largest_remainder(task_reasoning_step_quota[task_reasoning_step_count] - supported_value_count, conditional_share(task_reasoning_step_count, quota_dimension, dimension_value))`.

For clue type, replace `task_reasoning_step_quota[task_reasoning_step_count]` with `planned_clue_occurrences[task_reasoning_step_count]`
and `supported_value_count` with the number of supported clue types.

The `+1` is the coverage minimum and is taken before the remainder allocation.
This guarantees at least one task per supported task target category, answer
meaning, and answer format, and at least one clue occurrence for each supported
clue type. Clue operand form gets the same coverage floor without a share: its
target count is one clue occurrence per supported form at each step count where
the task-definition rules mark it feasible.

Allocate the four share-bearing quota dimensions separately. Do not divide `task_reasoning_step_quota` by four
and do not create a full task target category × clue type × clue operand form ×
answer meaning × answer format cross-product.

If `supported_value_count` exceeds the available task or clue count, record
`coverage_infeasible`; do not drop a supported value. A feasibility conflict
cannot be repaired by `03c`.

### Clue occurrence budget

An answer-step task at task reasoning step count `task_reasoning_step_count` has `task_reasoning_step_count - 1` task clue
steps. An identity answer task has `task_reasoning_step_count` task clue steps. Start from the
answer-step baseline:

`baseline_clue_occurrences[task_reasoning_step_count] = task_reasoning_step_quota[task_reasoning_step_count] * (task_reasoning_step_count - 1)`.

`identity_tasks[task_reasoning_step_count] = max(quota_target_count(task_reasoning_step_count, answer_meaning, identity), identity_floor, clue_floor)`

where `identity_floor` is 1 when identity is supported and 0 otherwise, and
`clue_floor = max(0, supported_clue_count - baseline_clue_occurrences[task_reasoning_step_count])`.
If identity is not supported and `clue_floor` is positive, record
`clue_coverage_infeasible`. If `identity_tasks[task_reasoning_step_count] > task_reasoning_step_quota[task_reasoning_step_count]`, record
`identity_quota_infeasible`.

`planned_clue_occurrences[task_reasoning_step_count] = baseline_clue_occurrences[task_reasoning_step_count] + identity_tasks[task_reasoning_step_count]`.

Adjust the identity answer-meaning target count to `identity_tasks[task_reasoning_step_count]`. Let
`remaining_task_quota = task_reasoning_step_quota[task_reasoning_step_count] - identity_tasks[task_reasoning_step_count]` and
`remaining_supported_count` be the number of other supported answer meanings.
For each remaining answer meaning, use:

`quota_target_count = 1 + largest_remainder(remaining_task_quota - remaining_supported_count, remaining_conditional_share)`,

where `remaining_conditional_share` is the answer meaning's global share
normalized over the remaining supported answer meanings. If
`remaining_task_quota < remaining_supported_count`, record
`answer_meaning_infeasible`.

This adjustment is the only exception to the equal/global-share target. It
exists because an identity answer is the only answer meaning that can add a clue
occurrence at task reasoning step count 1.

### Coverage bounds and plan caps

Each quota target records `minimum` and `maximum`. The release-level numbers
come from `dimensions` in `balance.yaml`; the half and twice bounds are the
per-step balance rule and stay in the equations. A lower bound rounds up and an
upper bound rounds down, so an accepted count is inside the range in shares too.

- task target category: `minimum = 1`; no task-reasoning-step balance bound; plan maximum
  `floor(dimensions.target_category.max * dataset_release_task_count)`.
- answer format: `minimum = max(1, ceil(0.5 * quota_target_count))`;
  `maximum = min(floor(2 * quota_target_count), floor(dimensions.answer_format.max * dataset_release_task_count))`;
  plan minimum `ceil(dimensions.answer_format.min * dataset_release_task_count)`.
- answer meaning: `minimum = max(1, ceil(0.5 * quota_target_count))`;
  `maximum = min(floor(2 * quota_target_count), floor(dimensions.answer_meaning.max * dataset_release_task_count))`;
  plan minimum `ceil(dimensions.answer_meaning.min * dataset_release_task_count)`.
- clue type: `minimum = 1`;
  `maximum = floor(dimensions.clue_type.max * planned_clue_occurrences[task_reasoning_step_count])`.

The target count is the desired count; the minimum and maximum are acceptance
bounds. When a target count violates a plan cap, move units to values with slack.
If no value has slack, record `cap_conflict`; do not silently exceed the cap.

Fill targets in the priority order above, and within a tier process the
scarcest targets first. A task is accepted when it fills an unfilled target and
does not push any cell past its maximum; an acceptance that would overfill is
rejected and recorded.

### Family task capacity

`active_programs_with_graph` counts one program per `program_id`. Two selection
rows can share a `program_id` when the same normalized text appears in two
collections, because `01d` normalize programs gives identical bytes one identity.
The row with the lexicographically smallest `source_id` is used and its family is
the program's family; the other row is excluded from the plan and the conflict is
recorded, because `task_id` is keyed on `program_sha256` and two families for one
program would put one task in two splits.

When `usable_program_count` is below `policy.usable_floor` from `01b`, the plan
records a `capacity_deficit` with detail `program_floor_short`. `03c` resolve
deficits resolves it by promoting reserve programs through the slow loop; when
the reserve is exhausted and the floor is still missed, it records an
`AcceptedMiss` and the `programs_min` check blocks the export.

Use `usable_program_count = max(1, active_programs_with_graph)` for active programs
with a CAD graph:

`per_program_task_quota = min(max(1, floor(0.01 * dataset_release_task_count)), max(1, ceil(dataset_release_task_count / usable_program_count)))`.

The first term enforces the no-CAD-model-above-1% cap. The second term gives each
program enough average quota to reach the dataset release size.

`family_probe_success_rate = (accepted_probe_tasks + 1) / (attempted_probe_tasks + 2)`
when a probe ran, otherwise 1.0.

`family_task_capacity = floor(program_count * per_program_task_quota * family_probe_success_rate)`.

Use the same smoothed ratio for `family_quota_target_probe_success_rate`, with 1.0
when no probe ran for that family and quota target.

### Split and family quotas

`split_task_target = largest_remainder(dataset_release_task_count, split_share)`;
use `release.splits` from `balance.yaml`; 0.70, 0.15, and 0.15 is the default.
`split_task_target` is a map with one count per split, not one scalar. For 10,000
tasks the map is 7,000 / 1,500 / 1,500. For
10,001 tasks the exact shares are 7,000.7 / 1,500.15 / 1,500.15; the three floors
sum to 10,000, so the one remaining task goes to train because it has the largest
fractional remainder.

Assign each CADEvolve program family to exactly one split with deterministic
greedy balancing. Order families by capacity descending, then by
`sha256(seed || family_id)`. A family is atomic and cannot cross splits.

`split_capacity[split] = sum(family_task_capacity[family])` over families assigned
to that split. If `split_capacity[split]` is zero, record `split_capacity_short`
and leave the split unfilled. If `split_capacity[split] < split_task_target[split]`,
record `split_capacity_short`.

`family_task_quota` is the largest-remainder allocation of
`split_task_target[split]` across the capacities of the families in that split,
capped by each family task capacity. If the total is short, record
`family_quota_short`.

`family_task_reasoning_step_quota[family] = largest_remainder(family_task_quota[family], task_reasoning_step_quota)`,
capped by `family_task_quota[family]`. The per-task-reasoning-step quotas sum to
`family_task_quota[family]`.

### Quota target allocation to families

For each task reasoning step count, quota dimension, and quota target:

1. Find families in the split that have the quota target capability and
   `family_task_reasoning_step_quota[family][task_reasoning_step_count] > 0`.
2. Set `family_quota_target_weight = family_task_reasoning_step_quota[family][task_reasoning_step_count] * family_quota_target_probe_success_rate`.
3. Set `family_quota_target_count = largest_remainder(quota_target_count, family_quota_target_weight)`.
4. If no family is eligible, record `quota_target_family_unassigned`.

Family target counts are independent across quota dimensions. Do not sum them to
derive `family_task_quota`. A family's constructed tasks at a task reasoning step count never exceed
`family_task_reasoning_step_quota[family][task_reasoning_step_count]`; `03b` samples definitions that jointly satisfy the independent
targets. If a family's target counts sum to more than `family_task_reasoning_step_quota[family][task_reasoning_step_count]`, move
the smallest over-allocation to a family with slack in the same quota target. If no family has
slack, record `family_quota_target_conflict`.

Set each construction attempt budget with the family-and-step formula in
[Construction attempt budgets](#construction-attempt-budgets); do not size it
from a single quota target.

### Plan acceptance

The allocator is complete only when all of these hold:

- `task_reasoning_step_quota` sums to `dataset_release_task_count`;
- every supported value has a target count of at least 1;
- every answer format, answer meaning, clue type, clue operand form, and task
  target category is within its bounds, or a conflict is recorded;
- every family has a split and a task quota no greater than its family task capacity;
- every quota target has at least one eligible family, or a deficit is recorded;
- every family target count is independent, and a family's target counts sum to no
  more than `family_task_reasoning_step_quota[family][task_reasoning_step_count]`.

The conditional release share is allocated from the global quota shares and then
filled from available data. It is not recomputed after seeing the whole
valid-task set.

## Construction attempt budgets

Rejected definitions are expected. A batch should not receive exactly the number
of definitions it needs, because every rejection would become a deficit.

The budget is per CADEvolve program family and task reasoning step count, not per
quota target. One accepted definition fills several quota targets at once, so a
per-target budget would provision the same definition several times.

- Use `construction.attempt_multiplier` from `balance.yaml`; `1.5` is the
  default.
- Use `construction.high_rejection_attempt_multiplier` (`2.0`) for a
  `(family, task reasoning step count)` pair with a known high rejection rate.
- `attempt_budget[family][step] = ceil(remaining_family_task_reasoning_step_quota[family][step] * construction_attempt_multiplier)`.
- Construct one whole batch per family and step count per plan revision. Accepted
  definitions are capped at the family's task reasoning step quota.
- Do not top up a quota target incrementally inside the same plan revision.
- Track accepted and rejected counts per quota target, family, step count, and
  rejection reason; a single acceptance decrements every target it fills.
- Treat a high rejection rate as a constructor or validity issue before treating
  it as a data-supply issue.

A batch is one program pass at one task reasoning step count: the program's graph
and census are loaded once and every target assigned to it at that step count is
filled from that pass (see `03b`). Passes are parallel across programs, not across quota targets. The
multiplier is a starting policy, not a guarantee. Sampling remains iterative at
the plan level: a batch is one iteration, and `03c` may trigger another revision.
A quota target still becomes a deficit if its batch is underfilled.

## Family profiles

Build a family profile from the graphs in the selected pool:

- CADEvolve program family and program count;
- split status, if already assigned;
- available task target categories;
- available clue predicates and relations;
- available measurements and answer meanings;
- available answer formats;
- `max_task_reasoning_step_count`, the approximate maximum task reasoning step
  count;
- `states_with_point_probe`, the states with at least one surviving point probe,
  so a membership target has a family to go to;
- task quota per program and family;
- probe success rate per family and quota target.

Profiles describe capability, not a list of all tasks. A bounded probe may
construct a small deterministic sample of task definitions per family to improve
success-rate estimates. That is sampling, not full enumeration.

## Family assignment order

The equations above define family task capacity, split task targets, and quota
target allocation. This order is normative:

1. Treat each CADEvolve program family as atomic.
2. Assign families to train, validation, and test before task construction.
3. Order families by capacity descending, then by `sha256(seed || family_id)`.
4. Fill each split task target with families while preserving family isolation.
5. Assign quota targets scarcity-first: rare values first, then common values.
6. Prefer families with the required capability and remaining quota.
7. Keep a reserve of families for `03c`.

A family receives a task quota, per-task-reasoning-step task quotas, and a set of
quota targets,
not one task type. If it cannot fill an assigned quota target, the remainder
returns to the plan.
`03b` stamps the family ID, split, and subset on each definition; `05` rechecks
family isolation on the final release table.

Exact split and quota target assignment is a bin-packing problem and can be hard. The
contract does not require an exact optimum. Deterministic greedy allocation,
reserves, and recorded misses are sufficient.
