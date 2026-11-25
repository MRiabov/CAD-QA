# Task quota planning math

**Status:** draft, 2026-10-21. This document centralizes the arithmetic used to
plan and balance a dataset release. Product requirements remain authoritative;
this document explains how the constraints combine.

## Inputs

- The task-definition rules from `pipeline/03-task-generation/03b-construct-task-definitions/README.md`.
- The program capability census for each selected program, derived from its
  CAD graph.
- The release implementation scope, from the product priorities.
- The task-count targets in the PRD and the release contract.
- The balance policy in `generator/config/balance.yaml`.
- The split rule: a CADEvolve program family belongs to one split.

## Implementation scope

P0/P1/P2 describe implementation order for requirements and generation inputs.
They are not task labels. The first release implements the P0 values and
contains tasks with task reasoning step counts 1 through 5. The thesis release
adds the P1 6–10 tiers when the 6–10 release gate in `requirements/PRD.md` section 6.1
passes. Later releases add P1 and P2 values and are cumulative. A task is never
labelled P0, P1, or P2.

Coverage and balance are checked against the values implemented by the release.
A value deferred to a later implementation scope is not a gap in the current
release.

## Coverage

Coverage is checked at every task reasoning step count and per release
implementation scope. For each step count in the release, every supported value
must appear:

- task target category;
- clue type;
- clue reduction form, for task clues that carry a reference and as a coverage-only
  dimension in P0;
- answer meaning;
- answer format.

Support is observed: a value is supported at a step count when the constructor
produced a valid definition for it over the coverage fixture set. The table
records what the constructor did, not what the grammar permits; the trade is in
[`task-step-support.md`](task-step-support.md).

## Plan-level targets

| Property | Target |
|---|---|
| Tasks | At least 10,000 in the first release |
| Distinct CAD programs | At least 1,000 in the first release |
| Warmup | 5% of tasks |
| Splits | Approximately 70% train, 15% validation, 15% test |
| One step | 5% target |
| 6–10 steps | 15% target (P1, only when the 6–10 release gate passes) |
| Three or more steps | At least 80% |
| Built shape required | At least 95% |
| Answer format | 5–25% each |
| Answer meaning | 1–10% each |
| Task target category | No category above 25% |
| Clue type | No clue type above 25% of clues |
| CAD model | No CAD model above 1% of tasks |
| Correct answer | No correct answer above 1% of tasks |

Answer format and answer meaning shares are over tasks; clue type shares are
over clues. Task target category is coverage-only at each step count; its 25%
cap is plan-level. The step count mix is a target, not a hard quota. A miss is
documented and accepted by the owner.

The table records the default policy. The release instance is the root
`balance.yaml`, which `03a` allocate task quotas reads when planning and `05`
validate and export release reads when checking. A release may depart from a
default; the manifest records the policy version and hash, so the departure is
visible.

Construction attempt budgets multiply the family's per-step task quota in one
batch per plan revision:
`ceil(family_task_reasoning_step_quota[family][step] * construction_attempt_multiplier)`
by default, or `2.0` for a family and step count with a high rejection rate.
Rejections consume construction attempts, not dataset release rows. An
underfilled batch is a deficit; there is no per-quota-target top-up loop inside
one plan revision.

## Per-step balance

At each step count, a value is checked against its conditional release share,
within half to twice that share. The conditional share is allocated from the
global targets before task construction, then filled from available data; the
plan is in
[`pipeline/03-task-generation/03a-allocate-task-quotas/README.md`](pipeline/03-task-generation/03a-allocate-task-quotas/README.md).
The release-side check, including the clue reduction form exception and the
superseded outcome, is in
[`pipeline/05-validate-and-export-release/release-checks.md`](pipeline/05-validate-and-export-release/release-checks.md).

This document fixes the coverage rule, the implementation-scope rule, the
plan-level bounds, and the split rule. The quota allocator applies them.

## Splits

The split unit is the CADEvolve program family, not the program or the task. A
CADEvolve program family is a CADEvolve generator family or a CADEvolve-predicted
ABC/ShapeNet mesh family; P and C versions of the same family share a family ID. All
tasks from one group share one split, and no group appears in both training and
evaluation.

## Implementation choices

- **Planning strategy:** quota planning, not enumerate-and-cut; see pipeline stage `03a`.
- **Conditional share allocation:** allocated from the global targets before
  construction; see pipeline stage `03a`.
- **Tie-break rule:** deterministic; see pipeline stage `03a`.
