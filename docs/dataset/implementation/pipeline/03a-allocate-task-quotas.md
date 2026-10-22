# 03a — Allocate task quotas to program families

**Parent:** [`03-enumerate-tasks.md`](03-enumerate-tasks.md).

**Purpose:** allocate task quotas and quota cells to CADEvolve program
families, assign splits, and set sampling budgets before task definitions are
generated.

## Input / output

- Input: CAD graphs for the selected program pool, program metadata, the
  [task reasoning step support tables](../task-step-support.md), dataset release
  targets, and `ProgramReassignmentRequest` records from `03c`.
- Output: `ReleasePlan`.

## Release plan

`ReleasePlan` contains:

| Field | Meaning |
|---|---|
| `plan_version`, `seed` | Version and deterministic ordering seed. |
| `step_quotas` | Target task count for each task reasoning step count. |
| `quota_cells` | Dimension values with minimum, target, maximum, and priority. |
| `clue_quotas` | Clue type counts over clue occurrences. |
| `clue_occurrences` | Planned clue occurrences for each task reasoning step count. |
| `family_profiles` | Graph capabilities, capacity, and probe yield per CADEvolve program family. |
| `family_assignment` | Family to split, task quota, per-step task quotas, and assigned quota cells. |
| `sample_budgets` | One construction batch per cell and family. |
| `oversample_factor` | Sample multiplier over the accepted quota; default 1.5, or 2.0 for high-rejection cells. |
| `expansion_tier` | Current data tier before a deficit triggers `03c`. |

The plan is a target. It does not prove that the corpus can supply every cell.

## Quota cells

A quota cell is `(step count, dimension, value)`. It records:

- `minimum`: coverage requirement;
- `target`: desired count;
- `maximum`: balance or cap limit;
- `priority`: coverage first, then balance, then volume.

Plan four separate dimensions:

- target category;
- clue type;
- answer meaning;
- answer format.

Do not create a full target × clue × meaning × format cross-product. The
requirements are marginal: coverage and balance at each step count, not every
joint combination. A task contributes to one target category, one answer format,
one answer meaning, one step count, and one or more clue occurrences.

Clue quotas are over clue occurrences, because one task has several clues.

## Allocation equations

Define `largest_remainder(total, weights, seed, key)` as: normalize the weights,
floor each weighted share, then distribute the remaining units one at a time to
the largest fractional remainders; break ties by `sha256(seed || key)`. The
result sums exactly to `total`.

### Step quotas

`step_quota[step] = largest_remainder(dataset_release_task_count, step_share[step])`.

Use the fixed step shares 5%, 15%, 40%, 25%, and 15%. `step_quota[1]` is the
warmup quota. Allocate the exact dataset release task count; do not round each
step independently and leave a residual.

### Marginal cell targets

For each task reasoning step count and dimension:

- `supported_values(step, dimension)` comes from the task reasoning step support
  table and the release implementation scope.
- `conditional_share(step, dimension, value)` is the dimension value's global release
  share divided by the sum of the global shares of values supported at that step.
  The global release share is the release target for that dimension value. When the release
  target does not name a share, use an equal share among implemented values in
  that dimension.
- `cell_target(step, dimension, value) = 1 + largest_remainder(step_quota[step] - supported_count, conditional_share(step, dimension, value))`.

For clue type, replace `step_quota[step]` with `planned_clue_occurrences[step]`
and `supported_count` with the number of supported clue types.

The `+1` is the coverage minimum and is taken before the remainder allocation.
This guarantees at least one task per supported target category, answer meaning,
and answer format, and at least one clue occurrence per supported clue type.

Allocate the four dimensions separately. Do not divide `step_quota` by four and do
not create a full target × clue × meaning × format cross-product.

If `supported_count` exceeds the available task or clue count, record
`coverage_infeasible`; do not drop a supported value. A support-table conflict
cannot be repaired by `03c`.

### Clue occurrence budget

An answer-step task at step count `step_count` has `step_count - 1` task clue
steps. An identity answer task has `step_count` task clue steps. Start from the
answer-step baseline:

`baseline_clue_occurrences[step] = step_quota[step] * (step_count - 1)`.

`identity_tasks[step] = max(cell_target(step, answer_meaning, identity), identity_floor, clue_floor)`

where `identity_floor` is 1 when identity is supported and 0 otherwise, and
`clue_floor = max(0, supported_clue_count - baseline_clue_occurrences[step])`.
If identity is not supported and `clue_floor` is positive, record
`clue_coverage_infeasible`. If `identity_tasks[step] > step_quota[step]`, record
`identity_quota_infeasible`.

`planned_clue_occurrences[step] = baseline_clue_occurrences[step] + identity_tasks[step]`.

Adjust the identity answer-meaning target to `identity_tasks[step]`. Let
`remaining_task_quota = step_quota[step] - identity_tasks[step]` and
`remaining_supported_count` be the number of other supported answer meanings.
For each remaining answer meaning, use:

`answer_meaning_target = 1 + largest_remainder(remaining_task_quota - remaining_supported_count, remaining_conditional_share)`,

where `remaining_conditional_share` is the answer meaning's global share
normalized over the remaining supported answer meanings. If
`remaining_task_quota < remaining_supported_count`, record
`answer_meaning_infeasible`.

This adjustment is the only exception to the equal/global-share target. It
exists because an identity answer is the only answer meaning that can add a clue
occurrence at step count 1.

### Coverage bounds and caps

Each quota cell records `minimum` and `maximum`:

- target category: `minimum = 1`; no step-level balance bound; release maximum
  `floor(0.25 * dataset_release_task_count)`.
- answer format: `minimum = max(1, floor(0.5 * cell_target))`;
  `maximum = min(ceil(2 * cell_target), floor(0.25 * dataset_release_task_count))`;
  release minimum `ceil(0.05 * dataset_release_task_count)`.
- answer meaning: `minimum = max(1, floor(0.5 * cell_target))`;
  `maximum = min(ceil(2 * cell_target), floor(0.10 * dataset_release_task_count))`;
  release minimum `ceil(0.01 * dataset_release_task_count)`.
- clue type: `minimum = 1`; `maximum = floor(0.25 * planned_clue_occurrences[step])`.

The target is the desired count; the minimum and maximum are acceptance bounds.
When a target violates a release cap, move units to values with slack. If no value
has slack, record `cap_conflict`; do not silently exceed the cap.

### Family capacity

Use `usable_program_count = max(1, active_programs_with_graph)` for active programs
with a CAD graph:

`per_program_task_quota = min(max(1, floor(0.01 * dataset_release_task_count)), max(1, ceil(dataset_release_task_count / usable_program_count)))`.

The first term enforces the no-CAD-model-above-1% cap. The second term gives each
program enough average quota to reach the dataset release size.

`family_probe_yield = (accepted_probe_tasks + 1) / (attempted_probe_tasks + 2)`
when a probe ran, otherwise 1.0.

`family_capacity = floor(program_count * per_program_task_quota * family_probe_yield)`.

Use the same smoothed ratio for `family_cell_probe_yield`, with 1.0 when no probe
ran for that family and cell.

### Split and family quotas

`split_target = largest_remainder(dataset_release_task_count, split_share)`; use
split shares 0.70, 0.15, and 0.15.

Assign each CADEvolve program family to exactly one split with deterministic
greedy balancing. Order families by capacity descending, then by
`sha256(seed || family_id)`. A family is atomic and cannot cross splits.

`split_capacity = sum(family_capacity)` over families assigned to the split. If
`split_capacity` is zero, record `split_capacity_short` and leave the split
unfilled. If `split_capacity < split_target`, record `split_capacity_short`.

`family_task_quota = largest_remainder(split_target, family_capacity)`, capped by
`family_capacity`. If the total is short, record `family_quota_short`.

`family_step_quota = largest_remainder(family_task_quota, step_quota)` for each
step, capped by `family_task_quota`. The per-step quotas sum to
`family_task_quota`.

### Cell-to-family division

For each step, dimension, and cell:

1. Find families in the split that have the cell capability and
   `family_step_quota > 0`.
2. Set `family_cell_weight = family_step_quota * family_cell_probe_yield`.
3. Set `family_cell_target = largest_remainder(cell_target, family_cell_weight)`.
4. If no family is eligible, record `cell_family_unassigned`.

The family cell targets are marginal targets. Do not sum them across dimensions
to derive `family_task_quota`. A family's constructed tasks at a step never
exceed `family_step_quota`; `03b` samples definitions that jointly satisfy the
marginal targets. If the row total exceeds `family_step_quota`, move the smallest
over-allocation to a family with slack in the same cell. If no family has slack,
record `family_cell_conflict`.

Set each sample budget to `ceil(family_cell_target * oversample_factor)`.

### Plan acceptance

The allocator is complete only when all of these hold:

- `step_quota` sums to `dataset_release_task_count`;
- every supported value has a target of at least 1;
- every answer format, answer meaning, clue type, and target category is within
  its bounds, or a conflict is recorded;
- every family has a split and a task quota no greater than its capacity;
- every cell has at least one eligible family, or a deficit is recorded;
- every family cell target is a marginal target, and the family row balance
  holds.

The conditional release share is allocated from the global targets and then
filled from available data. It is not recomputed after seeing the whole
valid-task set.

## Oversampling

Rejected definitions are expected. A cell should not receive exactly its target
number of construction attempts, because every rejection would become a deficit.

- Use `1.5` as the default oversample factor.
- Use `2.0` for cells with a known high rejection rate.
- Construct one whole batch per plan revision. Accepted definitions are capped at
  the target.
- Do not top up a cell incrementally inside the same plan revision. That is more
  coordination work than constructing the batch and accepting the result.
- Track accepted and rejected counts per cell and family.
- Treat a high rejection rate as a constructor or validity issue before treating
  it as a data-supply issue.

The batch is parallelizable across programs, families, and cells. The factor is a
starting policy, not a guarantee. Sampling remains iterative at the plan level:
a batch is one iteration, and `03c` may trigger another revision. A cell still
becomes a deficit if its batch is underfilled.

## Family profiles

Build a family profile from the graphs in the selected pool:

- CADEvolve program family and program count;
- split status, if already assigned;
- available target categories;
- available clue predicates and relations;
- available measurements and answer meanings;
- available answer formats;
- approximate maximum task reasoning step count;
- task quota per program and family;
- probe acceptance yield per family and cell.

Profiles describe capability, not a list of all tasks. A bounded probe may
construct a small deterministic sample of task definitions per family to improve
yield estimates. That is sampling, not full enumeration.

## Family assignment order

The equations above define capacity, split quotas, and cell division. This order
is normative:

1. Treat each CADEvolve program family as atomic.
2. Assign families to train, validation, and test before task construction.
3. Order families by capacity descending, then by `sha256(seed || family_id)`.
4. Fill each split target with families while preserving family isolation.
5. Assign quota cells scarcity-first: rare values first, then common values.
6. Prefer families with the required capability and remaining quota.
7. Keep a reserve of families for `03c`.

A family receives a task quota, per-step task quotas, and a set of cells, not one
task type. If it cannot fill an assigned cell, the remainder returns to the plan.
`03b` stamps the family ID, split, and subset on each definition; `05` rechecks
family isolation on the final release table.

Exact split and cell assignment is a bin-packing problem and can be hard. The
contract does not require an exact optimum. Deterministic greedy allocation,
reserves, and recorded misses are sufficient.

## Program reassignment

`03a` accepts a `ProgramReassignmentRequest` from `03c` when the current graphs
can supply a deficit but the plan does not use them.

It can:

- assign an unassigned family to a quota cell;
- move task quota from a saturated family to one with spare capacity;
- relax an internal family quota;
- change a quota cell or sample budget within its release bounds.

It does not fetch, normalize, or execute. It increments the plan version and
returns control to `03b`.

## Deficits

A cell enters the deficit ledger when:

- its minimum or target is not met after the sample budget;
- the current graphs lack the required capability;
- family quotas or release caps block it;
- the requested value is structurally infeasible.

Record the reason code from the allocation step: `coverage_infeasible`,
`answer_meaning_infeasible`, `cap_conflict`, `split_capacity_short`,
`family_quota_short`, `cell_family_unassigned`, or `family_cell_conflict`.

`03c` decides whether to sample more from existing graphs, use unused or reserve
programs, request a supplemental `01b` selection, or accept the miss.

## Resolved questions

- **Q1.** *Resolved 2026-10-21.* Use quota planning, not enumerate-and-cut.
  Select and sample into a release plan.
- **Q3.** *Resolved 2026-10-21.* Allocate the conditional release share from the
  global targets before task construction, then fill from available data.

## Not here

Task definition validity, clue predicates, answer resolution, prompt rendering,
and release validation.
