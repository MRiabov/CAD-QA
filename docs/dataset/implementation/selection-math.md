# Release selection math

**Status:** draft, 2026-10-21. This document centralizes the arithmetic used to
select and balance a release. Product requirements remain authoritative; this
document explains how the constraints combine.

## Inputs

- The valid-task set from `03-enumerate-tasks`.
- The task reasoning step support table for the priority slice.
- The release targets in the PRD and the release contract.
- The split rule: a CadQuery program belongs to one split.

## Task priority

A task inherits the highest priority of its inputs. Six or more task reasoning
steps force P2.

```text
if any input is P2 or step_count >= 6:  priority = P2
else if any input is P1:                priority = P1
else:                                   priority = P0
```

A P0 task uses only P0 inputs and has at most five steps. A P1 task may use P0
and P1 inputs. A P2 task may use any input.

## Priority slices

```text
P0 release = tasks with priority P0
P1 release = tasks with priority P0 or P1
P2 release = tasks with priority P0, P1, or P2
```

P1 and P2 are cumulative. A later slice keeps the split assignment of a task it
inherits from an earlier slice.

## Coverage

Coverage is checked at every task reasoning step count and per priority slice.
For each step count in the slice, every supported value must appear:

- target category;
- clue type;
- answer meaning;
- answer format.

Support is structural: a value is unsupported only when no valid task can
express it at that step count. A value deferred to a later priority is not a gap
in the current slice.

## Release-level targets

| Property | Target |
|---|---|
| Tasks | At least 10,000 in P0 |
| Distinct CAD programs | At least 1,000 in P0 |
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
[`pipeline/05-select-and-balance-release.md`](pipeline/05-select-and-balance-release.md).

This document does not fix an allocation formula until Q3 is resolved. It fixes
the coverage rule, the priority rule, the release-level bounds, and the split
rule.

## Splits

The split unit is the CadQuery program, not the task. All tasks from one program
share one split. The same program never appears in both training and evaluation.

## Open implementation choices

- **Selection strategy:** enumerate and cut, or plan quotas and generate into
  them (Q1 in pipeline stage `05`).
- **Conditional share allocation:** Q3 in pipeline stage `05`.
- **Tie-break rule:** must be deterministic; it belongs to pipeline stage `05`.
