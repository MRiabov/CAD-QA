# 03c resolve deficits — adversarial integration test (TDD)

**Parent:** [`00-testing-strategy.md`](00-testing-strategy.md).

**Contract under test:**
[`../03-task-generation/03c-resolve-deficits.md`](../03-task-generation/03c-resolve-deficits.md),
with the deficit classes in
[`../03-task-generation/README.md`](../03-task-generation/README.md).

## Happy-path integration test (test-first, adversarial)

`test_03c_deficits_happy_path_adversarial` — resolves a ledger with four
deficits and asserts the control records read back through the readers `03a`,
`01b`, and `05` use.

**Given** a plan over 120 programs with 3 expansion rounds and a 20% growth cap,
and a ledger with:

- `(2, target_category, face)` short by 40, where a second family has the
  capability and spare quota;
- `(3, answer_meaning, area)` short by 30, where no family profile has `area`;
- `(1, answer_meaning, membership)` short by 5, where one state lost its point
  probe and every other family has a probe;
- `(3, answer_format, multiple_choice)` blocked by a plan cap.

**When** `03c` resolves them.

**Then** assert the control records:

- the `face` deficit becomes one `ProgramReassignmentRequest` and no
  `ProgramRequest`, because the capability is present and the plan did not use
  it;
- the `area` deficit becomes one `ProgramRequest` naming `area` as the missing
  capability, with the plan version, the remaining counts, the number of
  programs, and the graph-build budget;
- the round requests at most 24 programs, then at most 28, then at most 34, each
  recomputed by the test from the plan's growth cap and the pool size at that
  round;
- after the third round the `area` target gets one `AcceptedMiss` with the quota
  target, the remaining count, the reason, the owner, and the plan version, and
  no fourth round is requested;
- the `membership` deficit is dropped for that one state with no request,
  because a per-state missing probe stays local;
- the `multiple_choice` deficit is a `plan_conflict` with no request at all:
  neither loop removes a cap;
- every record carries the plan version it was produced against.

`test_03c_classification_table` — one table drives all seven allocation details
to their classes: `coverage_infeasible` and `answer_meaning_infeasible` to
`structural_deficit`, `cap_conflict` to `plan_conflict`, `split_capacity_short`,
`family_quota_short`, and `family_quota_target_conflict` to `capacity_deficit`,
and `quota_target_family_unassigned` to `capability_deficit` or
`capacity_deficit` depending on the family profiles.

`test_03c_capability_lookup` — the same detail maps to two different classes: with
one family profile carrying the capability the class is `capacity_deficit`, and
with none carrying it the class is `capability_deficit`. The request names the
capability and the plan version, and the lookup reads `family_profiles` rather
than the graphs.

`test_03c_census_is_a_filter_not_an_oracle` — a family profile reports `area`
and construction still yields zero accepted definitions. The class is
`construction_deficit`, the response raises the attempt budget, and no
`ProgramRequest` is emitted: a capability that is present but produces nothing is
a constructor or validity problem, not a data-supply problem.

`test_03c_escalation_order` — a deficit that a reassignment fixes produces no
fetch. A deficit whose split has no capable family at all produces a
`ProgramRequest` without a reassignment first. The test asserts the recorded
attempts, not just the final outcome.

`test_03c_round_budget_comes_from_the_plan` — a plan with one round and a 50%
growth cap stops after one round and requests up to half the pool. The same
ledger against the default plan takes three rounds. A constant in `03c` fails
both.

**TDD pin:** pins the seven-class mapping, the capability lookup, the local probe
rule, the escalation order, and the round budget before `03c` exists.

## Failure-mode tests

- `test_03c_structural_deficit_is_not_a_data_request` — a `structural_deficit`
  emits neither request and is recorded against the plan, because no program
  can make an infeasible step count feasible.
- `test_03c_delta_keeps_the_selection_immutable` — a `ProgramSelectionDelta`
  leaves the original selection byte-identical, a program in an assigned family
  inherits its split, and a new family is assigned in `03a` before generation.
- `test_03c_owner_accepts_the_miss` — an accepted miss stops the loop before the
  budget is spent and records the owner.
- `test_03c_no_render_no_export` — `03c` writes no release row and no prompt; the
  release artifacts are absent after every loop.

## What this does not prove

- That the residual plan is right. That is
  [`03a-allocate-task-quotas.md`](03a-allocate-task-quotas.md).
- That a definition can be constructed. That is
  [`03b-construct-task-definitions.md`](03b-construct-task-definitions.md).
- That the release is complete. That is `05-validate-and-export-release.md`.
