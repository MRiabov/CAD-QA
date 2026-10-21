# Release selection math

**Status:** draft, 2026-10-21. This document centralizes the arithmetic used to
select and balance a release. Product requirements remain authoritative; this
document explains how the constraints combine.

## Inputs

- The valid-task set from `03-enumerate-tasks`.
- The [task reasoning step support tables](task-step-support.md) for the release implementation scope.
- The release targets in the PRD and the release contract.
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

- target category;
- clue type;
- answer meaning;
- answer format.

Support is structural: a value is unsupported only when no valid task can
express it at that step count.

## Release-level targets

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
| Target category | No category above 25% |
| Clue type | No clue type above 25% of clues |
| CAD model | No CAD model above 1% of tasks |
| Correct answer | No correct answer above 1% of tasks |

Answer format and answer meaning shares are over tasks; clue type shares are
over clues. Target category is coverage-only at each step count; its 25% cap is
release-level. The step count mix is a target, not a hard quota. A miss is
documented and accepted by the owner.

## Per-step balance

At each step count, a value is checked against its conditional release share,
within half to twice that share. The definition of the conditional share and
whether it is allocated from global targets or computed from the valid-task set
is Q3 in
[`pipeline/04-select-and-balance-release.md`](pipeline/04-select-and-balance-release.md).

This document does not fix an allocation formula until Q3 is resolved. It fixes
the coverage rule, the implementation-scope rule, the release-level bounds, and
the split rule.

## Splits

The split unit is the CADEvolve program family, not the program or the task. A
CADEvolve program family is a CADEvolve generator family or a CADEvolve-predicted
ABC/ShapeNet mesh family; P and C versions of the same family share a family ID. All
tasks from one group share one split, and no group appears in both training and
evaluation.

## Open implementation choices

- **Selection strategy:** enumerate and cut, or plan quotas and generate into
  them (Q1 in pipeline stage `04`).
- **Conditional share allocation:** Q3 in pipeline stage `04`.
- **Tie-break rule:** must be deterministic; it belongs to pipeline stage `04`.
