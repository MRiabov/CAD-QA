# Release coverage and balance checks

**Parent:** [`../05-validate-and-export-release.md`](../05-validate-and-export-release.md).

**Status:** draft, 2026-11-20.

`03a` allocate task quotas plans against coverage and balance targets. This
document is the other half: how `05` validate and export release measures the
finished release against the same targets, and what a miss does.

The checks never change the release. `05` does not drop a task to make a share
fit. A miss is fixed by a new plan or accepted by the owner.

## One implementation of the conditional release share

The conditional release share is defined once, in the allocation code that
`03a` and `05` both call:

```text
conditional_release_share(task_reasoning_step_count, quota_dimension, dimension_value)
  = global_share(dimension_value)
    / sum(global_share(v) for v in supported_values(task_reasoning_step_count, quota_dimension))
```

`global_share` comes from `balance.yaml`, and `supported_values` comes from the
task reasoning step support tables. `05` holds no share of its own.

A second definition would let the plan and the release check disagree about what
the plan was aiming at, and the release check would then be measuring a target
nobody planned for.

## What is counted

| Quantity | Unit | Denominator | Release column |
|---|---|---|---|
| Task target category | task | tasks | `target_category` |
| Answer format | task | tasks | `answer_format` |
| Answer meaning | task | tasks | `answer_meaning` |
| Task reasoning step count | task | tasks | `task_reasoning_step_count` |
| Built shape | task | tasks | `geometry_required` |
| CAD model | task | tasks | `program_id` |
| Correct answer | task | tasks | `answer_format`, `gold_answer_json`, `answer_unit` |
| Clue type | clue occurrence | clue occurrences | `clue_types` |
| Clue operand form | clue occurrence that carries a reference | clue occurrences that carry a reference | `clue_operand_form_profile` |
| Warmup | task | — | `subset` |
| Split | task | tasks | `split` |

Three of these need a word of explanation.

**A CAD model is a `program_id`.** One CadQuery program builds one shape, and the
release contract and `03a` both count distinct programs, so the two numbers are
the same number.

**A correct answer is `(answer_format, gold_answer_json, answer_unit)`.** It is
deliberately coarser than `answer_sha256`, which also covers the scoring fields.
Two tasks that ask for the same number with different tolerances have the same
correct answer, and R-11 is about the answer, not about the tolerance.

**A clue operand form is counted only on clues that carry a reference.** A clue
with no reference has no form (`03b` construct task definitions), so it is not in
the denominator. `05` checks first that `clue_operand_form_profile` has one entry
per `clue_types` entry, in the same order with the same clue type. That is part
of release table schema validation, so the two columns cannot disagree.

## Coverage checks

One row per check and task reasoning step count. The row carries the supported
values, the observed values, the missing values, and the released values that the
support table does not support.

| Check | Requirement | Scope | Bound | First release |
|---|---|---|---|---|
| `target_category_coverage` | R-8 | each task reasoning step count | every supported task target category appears | enforced |
| `clue_type_coverage` | R-8 | each task reasoning step count | every supported clue type appears | enforced |
| `clue_operand_form_coverage` | R-8 | each task reasoning step count | every supported clue operand form appears among clues that carry a reference | enforced |
| `answer_meaning_coverage` | R-8 | each task reasoning step count | every supported answer meaning appears | enforced |
| `answer_format_coverage` | R-7 | each task reasoning step count | every supported answer format appears | enforced |

A missing value makes the row a miss. A released value the support table does not
support at that step count is also a miss: it means the release contains a task
the specification says cannot exist, which is a defect in the constructor rather
than a coverage gap. A step count with no supported value for a dimension has
nothing to cover, and its row is `not_applicable`.

There is no whole-release coverage row. Global coverage is the union of the
per-step rows, and a union row would let a value pass globally while missing at
the step count where it was required.

## Release-level checks

| Check | Requirement | Quantity | Bound | First release |
|---|---|---|---|---|
| `release_task_count` | PRD §8 | tasks | at least `release.tasks_min` | enforced |
| `distinct_cad_model_count` | PRD §8, R-10 | distinct `program_id` | at least `release.programs_min` | enforced |
| `cad_model_share_cap` | R-10 | tasks per `program_id` | at most `release.cad_model_max_share` | deferred |
| `built_shape_share_floor` | PRD §8, R-4 | tasks with `geometry_required` | at least `release.built_shape_min_share` | enforced |
| `split_share` | release contract §3 | tasks per `split` | within `release.share_tolerance` of `release.splits` | enforced |
| `step_share` | R-9, PRD §8 | tasks per `task_reasoning_step_count` | within `release.share_tolerance` of `task_reasoning_step_share` | enforced |
| `warmup_set` | R-15 | tasks with `subset = warmup` | equal to the tasks with one task reasoning step | enforced |
| `answer_format_share_range` | R-7 | tasks per `answer_format` | in `[dimensions.answer_format.min, dimensions.answer_format.max]` | enforced |
| `answer_meaning_share_range` | R-12 | tasks per `answer_meaning` | in `[dimensions.answer_meaning.min, dimensions.answer_meaning.max]` | deferred |
| `target_category_share_cap` | R-12 | tasks per `target_category` | at most `dimensions.target_category.max` | deferred |
| `clue_type_share_cap` | R-12 | clue occurrences per `clue_type` | at most `dimensions.clue_type.max` | deferred |
| `clue_operand_form_release_share` | R-12 | clues that carry a reference, per clue operand form | the `dimensions.clue_operand_form.target` share, which is `equal` in the first policy | deferred |
| `distinct_answer_count` | R-11 | distinct correct answers | at least `release.distinct_answer_min` | deferred |
| `answer_share_cap` | R-11 | tasks per correct answer | at most `release.correct_answer_max_share` | deferred |

`release.share_tolerance` is an absolute share, not a multiple. `03a` plans the
exact counts, and the release drifts from them because construction rejects
tasks. One percentage point is the amount of drift a release may show before the
plan and the release are treated as different plans.

`warmup_set` is a set comparison, not a percentage. Section 9 of the PRD labels
the lowest-step tasks as the warmup subset, so the two sets are the same set, and
a separate 5% check would be a second number for the same fact.

R-9 also says that steps 3 and 4 carry most benchmark tasks, and PRD §8 says at
least 80% of tasks need three or more steps. Both are sums of `step_share` rows:
65% for steps 3 and 4, 80% for steps 3, 4, and 5 at the default mix. Neither is a
second check. A second bound could disagree with the mix that the plan actually
allocated, and the report carries both sums so the targets are visible.

## Per-step checks

One row per check, task reasoning step count, and value. The bound is a multiple
of the conditional release share, so it compares like with like: a step count
that supports only some values is not required to carry the whole-release
distribution.

| Check | Requirement | Quantity | Bound | First release |
|---|---|---|---|---|
| `answer_format_step_mix` | R-7 | share of tasks at the step count | between 0.5 and 2 times the conditional release share | enforced |
| `clue_type_step_share_cap` | R-12 | share of clue occurrences at the step count | at most `dimensions.clue_type.max` | deferred |
| `clue_type_step_mix` | R-12 | share of clue occurrences at the step count | between 0.5 and 2 times the conditional release share | deferred |
| `answer_meaning_step_mix` | R-12 | share of tasks at the step count | between 0.5 and 2 times the conditional release share | deferred |
| `clue_operand_form_severe_mix` | R-12, `DS-37` | share of clues that carry a reference at the step count | between `dimensions.clue_operand_form.severe.below` and `.above` times the conditional release share | enforced |
| `clue_operand_form_step_mix` | R-12 | share of clues that carry a reference at the step count | between 0.5 and 2 times the conditional release share | reported |

Clue operand form has two rows because `DS-37` makes the wide range the P0
requirement and the narrow range the P1 requirement. In P0 the narrow row is
computed and reported so the imbalance is visible, and only the wide row can
block. In P1 both are enforced, and the narrow row implies the wide one.

## Bound arithmetic

Bounds are compared as exact rationals. A row stores the integer count and the
integer denominator, and each bound as canonical decimal text, as
[`03b` construct task definitions](../03-task-generation/03b-construct-task-definitions.md)
defines it. The comparison multiplies through, so no floating-point value is ever
compared and a 5% bound on 10,000 tasks is exactly 500.

A per-step lower bound is at least one task:

```text
minimum_count = max(1, floor(lower_multiple * conditional_release_share * denominator))
maximum_count = ceil(upper_multiple * conditional_release_share * denominator)
```

The `max(1, ...)` is the same rule [`task-structure.md`
section 6](../../../requirements/task-structure.md) states: when half of a
value's conditional release share is less than one task, one task satisfies the
lower bound.

A step count with zero or one supported value for a dimension has no mix to
balance. Its per-step rows are `not_applicable`.

## When a bound is superseded

A bound is `superseded` when the coverage floor makes it impossible to hold, and
the release is not at fault. Two tests:

- an interval bound: `n * maximum < 1` or `n * minimum > 1`, where `n` is the
  number of supported values at that scope. Each supported value needs at least
  one task, and their shares sum to 1, so no assignment exists.
- a per-step mix: the sum of the per-step lower bounds exceeds the denominator.

This is the conflict [`task-structure.md`
section 6](../../../requirements/task-structure.md) says is reported rather than
resolved by dropping coverage. A superseded row is recorded and does not block,
and it is not a known miss, because there is nothing to accept.

A superseded row usually means the coverage check at the same scope is a miss.
The coverage miss is the real defect, and it is the row that blocks.

## Outcomes

| Outcome | Meaning | Blocks export |
|---|---|---|
| `pass` | The check holds. | no |
| `miss` | The check fails. | yes, until the owner accepts it |
| `superseded` | The coverage floor makes the bound impossible. | no |
| `not_applicable` | Zero or one supported value at this scope, so there is no mix. | no |
| `deferred` | The requirement is outside the release implementation scope. | no |

Every in-scope miss blocks until the owner accepts it. The PRD calls the step mix
a target rather than a hard quota, and a target miss still goes to the owner:
section 8 says a miss is documented and accepted, not hidden. One rule covers
both, and no requirement is quietly downgraded to a warning.

An accepted miss is recorded in `known_misses` in `manifest.json`, one entry per
accepted row:

| Field | Meaning |
|---|---|
| `check` | The check name. |
| `scope` | `release` or the task reasoning step count. |
| `value` | The dimension value, when the check is per value. |
| `observed` | The measured count or share. |
| `bound` | The bound the count or share missed. |
| `reason` | Why the owner accepts it. |

A `deferred` row is present in every release, including the first one, so the
scope boundary is visible. The check list above is the contract. `05` emits one
row per listed check, and a report that omits one is itself a rejection.

## The report

The report is `checks` in `manifest.json`. It is a control document, not a
release table, and it is never passed to the LLM model.

Coverage row:

| Field | Meaning |
|---|---|
| `check` | The check name. |
| `scope` | `step_<n>`. |
| `supported` | The supported values at that scope. |
| `observed` | The values present in the release at that scope. |
| `missing` | `supported` minus `observed`. |
| `unexpected` | `observed` minus `supported`. |
| `outcome` | The outcome. |

Balance row:

| Field | Meaning |
|---|---|
| `check` | The check name. |
| `scope` | `release` or `step_<n>`. |
| `value` | The dimension value, or the program or answer key for a cap on a high-cardinality quantity. |
| `count` | The integer count. |
| `denominator` | The integer denominator. |
| `conditional_share` | Canonical decimal text, or null when the bound is not relative. |
| `minimum`, `maximum` | Canonical decimal text, or null when the bound is one-sided. |
| `outcome` | The outcome. |
| `acceptance` | Null, or the `known_misses` entry that accepts a miss. |

A dimension with a small value set reports every value: task target category,
answer format, answer meaning, clue type, clue operand form, task reasoning step
count, split, and subset. A cap on a high-cardinality quantity reports the
extreme share, the program or answer that holds it, and the programs or answers
over the bound. A program and a correct answer each have at least a thousand
values, so a row per value would bury the answer in the manifest, and the cap
only needs the offenders.

Rows are sorted by check name, then scope, then value, so two runs over the same
release produce the same report.

## Not here

- Multiple-choice fairness: the choice checks.
- Release table schema, prompt answer-freedom, `task_id` uniqueness, and split
  isolation: `05` validate and export release.
- Failure record reconciliation and the review gate: `05` validate and export
  release.
- The allocation equations: `03a` allocate task quotas.
- The support-table derivation: [`../../task-step-support.md`](../../task-step-support.md).
