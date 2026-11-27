# 03a/c quota allocation — test contract

**Parent:** [`README.md`](README.md).

**Contract under test:**
[`../../../03-task-generation/03a-allocate-task-quotas/c-quota-allocation.md`](../../../03-task-generation/03a-allocate-task-quotas/c-quota-allocation.md).

## Happy-path integration test (test-first, adversarial)

`test_03a_plan_happy_path_adversarial` — plans a release over the graph fixture
and asserts the persisted `TaskQuotaPlan` read back through the reader `03b`
construct task definitions uses.

**Given** four CADEvolve program families with 40, 30, 30, and 20 programs, and a
balance policy fixture that is deliberately small and readable: 1,000 tasks,
step shares 0.25, 0.25, and 0.50, split shares 0.70, 0.15, and 0.15, answer
meaning shares 0.20 for identity, 0.50 for length, and 0.30 for area, and caps
wide enough to be feasible. The support-table derivation over the fixture marks
two task target categories, two answer formats, three answer meanings, and three
clue types at step count 3, and one clue reduction form at step count 1 and three
at step count 3. The graphs support every value the fixture marks.

**When** `03a` plans with a fixed seed.

**Then** assert the persisted plan:

- `task_reasoning_step_quotas` is 250, 250, and 500, and sums to 1,000;
- the step count 3 target counts are 250 for each of the two task target
  categories, 100 for identity, 250 for length, and 150 for area;
- the identity count is the adjusted one: `planned_clue_occurrences` at step count
  3 is 1,100, which is 500 tasks times two clue steps plus 100 identity tasks;
- the two answer formats share 500 tasks equally;
- the three clue types share 1,100 clue occurrences, and the split is the one the
  test recomputes with its own `largest_remainder`, not one read back from the
  plan;
- each clue reduction form has a target count of 1 at every step count where it is
  marked, and no share is computed for it: reduction form is coverage-only in P0;
- a value the support fixture does not mark at a step count has no quota target
  at that step count;
- every quota target's `minimum` and `maximum` follow the documented rounding: a
  lower bound rounds up and an upper bound rounds down, so answer format at step
  count 3 has a minimum of 125 and a maximum of 500, where the 2× term binds
  before the policy cap does;
- the split task targets are 700, 150, and 150;
- every family sits in exactly one split, no family task quota exceeds its
  family task capacity, and the family task quotas in a split sum to the split
  task target;
- `per_program_task_quota` is 9, from the second term, because the 1% cap is 10;
- one named quota target's construction attempt budget is `ceil(target * 1.5)`,
  recomputed by the test;
- `family_profiles` carries the union of the member programs' capabilities, the
  summed entity counts, the states with a surviving point probe, and the maximum
  task reasoning step count, and no census table is written anywhere.

The test carries its own `largest_remainder`. A plan that agrees with itself
through a shared helper proves nothing about the equation.

`test_03a_one_percent_cap_binds` — 80 programs and 10,000 tasks give
`per_program_task_quota` 100 from the first term, so the families can carry 8,000
tasks, and `split_capacity_short` and `family_quota_short` are recorded. This is
the reason `programs_min` is 1,000: below 100 programs the 1% cap alone makes the
release size unreachable.

`test_03a_deterministic` — the same seed and policy produce a byte-identical
plan; a changed seed changes the tie-breaks and therefore the plan.

**TDD pin:** pins the step quotas, the identity adjustment and its clue
occurrences, the coverage floor of one, the reduction-form coverage rule, the
bound rounding, the split targets, the 1% cap, and the attempt budget before
`03a` exists.

## Failure-mode tests

- `test_03a_coverage_infeasible` — a step count with fewer tasks than supported
  values records `coverage_infeasible` and drops no supported value.
- `test_03a_cap_conflict` — a cap that no value has slack for records
  `cap_conflict`, and the plan does not silently exceed the cap.
- `test_03a_split_capacity_short` — a split with no capable family records
  `split_capacity_short` and leaves the split unfilled, rather than moving a
  family across splits.
- `test_03a_quota_target_family_unassigned` — a quota target that no family in
  the split supports records `quota_target_family_unassigned`.
- `test_03a_step_bound_routing` — a program whose census
  `max_task_reasoning_step_count` for a target category and answer meaning is
  below a target's step count is not eligible for that target. When no program
  supports the step count, the plan records `coverage_infeasible` instead of
  assigning an attempt that cannot succeed.

## What this does not prove

- That a replan preserves accepted work. That is
  [`d-replan.md`](d-replan.md).
- That a task can be constructed. That is
  [`../03b-construct-task-definitions/README.md`](../03b-construct-task-definitions/README.md).
