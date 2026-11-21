# Replanning and deficits

**Parent:** [`README.md`](README.md).

## Replanning after a deficit

`03a` is re-entered with the current `TaskQuotaPlan`, the current `DeficitLedger`,
and a `ProgramReassignmentRequest`. It emits a new plan version; it does not
construct or validate task definitions.

Accepted definitions are immutable while the program, CAD graph, and
task-definition rule versions are unchanged. If any of those inputs changes,
accepted definitions from the old inputs are not reused; `03a` starts a new plan
instead.

A plan revision is a work-list input to `03b`, not part of an accepted
definition's identity. A new plan version does not invalidate accepted
definitions: `03b` skips their `task_id`s and constructs only the remaining
work. The identity rule is in
[`../../../run-contract.md`](../../../run-contract.md#6-pipeline-stage-identity).

The `DeficitLedger` carries accepted and rejected counts by quota target, family,
and task reasoning step count. A task can contribute to several quota targets, so
accepted quota-target counts are independent and must not be added together.

A rare quota target is a residual target, not a reason to rewrite an accepted
definition. If the capable family has no unused capacity, `03a` uses unused
capacity in another capable family, adds a family or program in the same split
through the slow loop, or records the deficit. Split isolation and plan caps are
hard constraints; moving or regenerating accepted tasks does not solve them.

For each new absolute target, compute the remaining amount:

`remaining_quota_target_count = max(0, new_quota_target_count - accepted_quota_target_count)`

`remaining_task_reasoning_step_quota = max(0, new_task_reasoning_step_quota - accepted_task_reasoning_step_count)`

`remaining_family_task_quota = max(0, new_family_task_quota - accepted_family_task_count)`

`remaining_family_task_reasoning_step_quota = max(0, new_family_task_reasoning_step_quota - accepted_family_task_reasoning_step_count)`

`remaining_quota_target_minimum = max(0, minimum - accepted_quota_target_count)`

`remaining_clue_occurrence_count = max(0, planned_clue_occurrences - accepted_clue_occurrence_count)`

`remaining_construction_attempt_budget = ceil(remaining_family_task_reasoning_step_quota * construction_attempt_multiplier)`

`construction_attempt_budgets` in the new plan use these remaining amounts.
Accepted definitions are not retried.

Allocate the remaining amounts with the same equations used for the first plan,
but use `remaining_quota_target_minimum` instead of the original coverage
minimum. For clue type, use `remaining_clue_occurrence_count` instead of
`planned_clue_occurrences`. A clue type with accepted clue occurrences has a
remaining minimum of zero. Do not allocate the new absolute targets again: accepted definitions
already consume part of every applicable target and satisfy coverage.

The new absolute plan must satisfy all of these, or `03a` rejects the request and
keeps the current plan version:

- `new_task_reasoning_step_quota` sums to `dataset_release_task_count`;
- every `new_quota_target_count` is at least its `accepted_quota_target_count`;
- every `new_family_task_quota` is at least `accepted_family_task_count`;
- every `new_family_task_reasoning_step_quota` is at least
  `accepted_family_task_reasoning_step_count`;
- every target stays within its `minimum` and `maximum`;
- a family with accepted tasks keeps its split.

`03a` may apply the request to unused capacity only:

- assign an unassigned family to a residual quota target;
- move unused task quota from a saturated family to one with spare capacity;
- relax an internal family quota;
- change a quota target or construction attempt budget within its plan bounds.

It does not move an accepted task to another family or split. It does not fetch,
normalize, or execute.

The fast loop keeps the current graphs and recomputes only the residual plan. The
slow loop adds the new families or programs from `01b`/`01c`/`01d`/`02`, updates
their family task capacity and probe success rate, assigns a split to each new
family, and then recomputes the residual plan. In both loops, `03b` resumes with
the new plan version and the same `DeficitLedger`; accepted definitions are not
regenerated.

The plan version increments and `parent_plan_version` names the previous version.
The previous plan and the accepted definitions remain immutable.

## Deficits

A quota target enters the deficit ledger when:

- its minimum or target count is not met after the construction attempt budget;
- the current graphs lack the required capability;
- family quotas or plan caps block it;
- the requested value is structurally infeasible.

Record the allocation detail from the pass: `coverage_infeasible`,
`answer_meaning_infeasible`, `cap_conflict`, `split_capacity_short`,
`family_quota_short`, `quota_target_family_unassigned`, or
`family_quota_target_conflict`.

The detail says what the allocator hit, not what to do about it. `03c`
resolve deficits maps it to a `DeficitClass`.

`03c` decides whether to sample more from existing graphs, use unused or reserve
programs, request a supplemental `01b` selection, or accept the miss.
