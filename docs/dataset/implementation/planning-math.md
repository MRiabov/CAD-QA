# Task quota planning math

**Status:** draft, 2026-10-21. This document centralizes the arithmetic used to
plan and balance a dataset release. Product requirements remain authoritative;
this document explains how the constraints combine.

## Inputs

- The task-definition rules from `pipeline/03b-construct-task-definitions.md`.
- The [task reasoning step support tables](task-step-support.md) for the release implementation scope.
- The task-count targets in the PRD and the release contract.
- The split rule: a CADEvolve program family belongs to one split.

## Implementation scope

P0/P1/P2 describe implementation order for requirements and generation inputs.
They are not task labels. The first release implements the P0 values and
contains tasks with task reasoning step counts 1 through 5. Later releases add P1 and P2 values and are
cumulative. A task is never labelled P0, P1, or P2.

Coverage and balance are checked against the values implemented by the release.
A value deferred to a later implementation scope is not a gap in the current
release.

## Coverage

Coverage is checked at every task reasoning step count and per release
implementation scope. For each step count in the release, every supported value
must appear:

- task target category;
- clue type;
- answer meaning;
- answer format.

Support is structural: a value is unsupported only when no valid task can
express it at that step count.

## Plan-level targets

| Property | Target |
|---|---|
| Tasks | At least 10,000 in the first release |
| Distinct CAD programs | At least 1,000 in the first release |
| Warmup | 5% of tasks |
| Splits | Approximately 70% train, 15% validation, 15% test |
| One step | 5% target |
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

Construction attempt budgets multiply the accepted quota in one batch per plan revision:
`ceil(quota_target_count * construction_attempt_multiplier)` by default, or `2.0` for
quota targets with a high rejection rate.
Rejections consume construction attempts, not dataset release rows. An underfilled batch is a
deficit; there is no per-quota-target top-up loop inside one plan revision.

## Per-step balance

At each step count, a value is checked against its conditional release share,
within half to twice that share. The conditional share is allocated from the
global targets before task construction, then filled from available data; the
plan is in
[`pipeline/03a-allocate-task-quotas.md`](pipeline/03a-allocate-task-quotas.md).

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
