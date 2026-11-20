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

`global_share` comes from `balance.yaml`. `supported_values` is the support-table
derivation's output: `03a` allocate task quotas calls the derivation in-process,
and `05` reads the tables it writes. One derivation, two readers, and `05` holds
no share of its own.

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

| Check | Requirement | Scope | Bound | Disposition |
|---|---|---|---|---|
| `target_category_coverage` | R-8 | each task reasoning step count | every supported task target category appears | enforced |
| `clue_type_coverage` | R-8 | each task reasoning step count | every supported clue type appears | enforced |
| `clue_operand_form_coverage` | R-8 | each task reasoning step count | every supported clue operand form appears among clues that carry a reference | enforced |
| `answer_meaning_coverage` | R-8 | each task reasoning step count | every supported answer meaning appears | enforced |
| `answer_format_coverage` | R-7 | each task reasoning step count | every supported answer format appears | enforced |

"Supported" means supported by the release implementation scope, as the support
tables record it. A value deferred to P1 has no row at that step count, and its
absence is not a gap in a P0 release.

A missing value makes the row a miss. A released value the support table does not
support at that step count is also a miss: it means the release contains a task
the specification says cannot exist, which is a defect in the constructor rather
than a coverage gap. A step count with no supported value for a dimension has
nothing to cover, and its row is `not_applicable`.

There is no whole-release coverage row. Global coverage is the union of the
per-step rows, and a union row would let a value pass globally while missing at
the step count where it was required.

## Release-level checks

| Check | Requirement | Quantity | Bound | Disposition |
|---|---|---|---|---|
| `release_task_count` | PRD §8 | tasks | at least `release.tasks_min` | enforced |
| `step_count_range` | R-9 | distinct `task_reasoning_step_count` values | exactly 1, 2, 3, 4, and 5 | enforced |
| `distinct_cad_model_count` | PRD §8, R-10 | distinct `program_id` | at least `release.programs_min` | enforced |
| `cad_model_share_cap` | R-10, cap part (P1) | tasks per `program_id` | at most `release.cad_model_max_share` | deferred |
| `built_shape_share_floor` | PRD §8, R-4 | tasks with `geometry_required` | at least `release.built_shape_min_share` | enforced |
| `split_share` | release contract §3 | tasks per `split` | within `release.share_tolerance` of `release.splits` | enforced |
| `step_share` | R-9, PRD §8 | tasks per `task_reasoning_step_count` | within `release.share_tolerance` of `task_reasoning_step_share` | enforced |
| `steps_three_or_more_share` | PRD §8 | tasks with three or more task reasoning steps | at least `release.three_or_more_step_min_share` | enforced |
| `warmup_set` | R-15 | tasks with `subset = warmup` | equal to the tasks with one task reasoning step | enforced |
| `answer_format_share_range` | R-7 | tasks per `answer_format` | in `[dimensions.answer_format.min, dimensions.answer_format.max]` | enforced |
| `answer_meaning_share_range` | R-12 | tasks per `answer_meaning` | in `[dimensions.answer_meaning.min, dimensions.answer_meaning.max]` | deferred |
| `target_category_share_cap` | R-12 | tasks per `target_category` | at most `dimensions.target_category.max` | deferred |
| `clue_type_share_cap` | R-12 | clue occurrences per `clue_type` | at most `dimensions.clue_type.max` | deferred |
| `clue_operand_form_release_share` | R-12 | clues that carry a reference, per clue operand form | the `dimensions.clue_operand_form.target` share, which is `equal` in the first policy | deferred |
| `distinct_answer_count` | R-11 | distinct correct answers | at least `release.distinct_answer_min` | deferred |
| `answer_share_cap` | R-11 | tasks per correct answer | at most `release.correct_answer_max_share` | deferred |

The disposition follows the requirement priority, not the `# p0` and `# p1`
markers in `balance.yaml`. A marker says when a number is used; a P1 bound can be
planned against in P0 and still be checked only in P1. `cad_model_share_cap` is
the case that matters: `03a` allocate task quotas plans the cap in P0 to spread
tasks across programs, and the release check waits for P1 with the rest of the cap
part of R-10.

`release.share_tolerance` is an absolute share, not a multiple. `03a` plans the
exact counts, and the release drifts from them because construction rejects
tasks. One percentage point is the amount of drift a release may show before the
plan and the release are treated as different plans.

`warmup_set` is a set comparison, not a percentage. Section 9 of the PRD labels
the lowest-step tasks as the warmup subset, so the two sets are the same set, and
a separate 5% check would be a second number for the same fact.

`step_count_range` is a coverage row at release scope: the supported set is the
task reasoning step counts 1 through 5, and the observed set is the distinct
counts in the release. It is a measurement of the release, not of the policy.
Without it a policy that dropped a step count from the mix would leave no row to
fail, and the release would silently cover four step counts.

R-9 also says that steps 3 and 4 carry most benchmark tasks. That is a sum of
`step_share` rows and needs no check of its own: at the default mix it is 65%, and
any mix within `release.share_tolerance` keeps it above half. A step count far
enough off target to break it is already a `step_share` miss.

PRD §8's "at least 80% of tasks need three or more steps" is different. It is a
floor, not a sum of the mix: the default mix sums to exactly 80%, so a mix within
tolerance can put the release at 77% and still pass every `step_share` row. It
gets its own check, `steps_three_or_more_share`. The mix shapes the release; the
floor is what the release must not go below.

## Per-step checks

One row per check, task reasoning step count, and value. The bound is a multiple
of the conditional release share, so it compares like with like: a step count
that supports only some values is not required to carry the whole-release
distribution.

| Check | Requirement | Quantity | Bound | Disposition |
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

Every bound becomes an integer count before anything is compared:

```text
absolute range: minimum_count = ceil(minimum_share * denominator)
                maximum_count = floor(maximum_share * denominator)
per-step range: minimum_count = max(1, ceil(0.5 * conditional_release_share * denominator))
                maximum_count = floor(2 * conditional_release_share * denominator)
```

A lower bound rounds up and an upper bound rounds down, so a count inside the
range is also inside the range in shares. The other rounding is too loose: with a
conditional release share of one third and ten tasks, `floor` would accept one
task at 0.3 times the share, and `ceil` would accept seven at 2.1 times it.

The clue operand form severe row uses its own multiples in place of 0.5 and 2.

The `max(1, ...)` is the same rule [`task-structure.md`
section 6](../../../requirements/task-structure.md) states: when half of a
value's conditional release share is less than one task, one task satisfies the
lower bound. `03a` allocate task quotas uses the same floor and ceiling on the
planned count, so the plan and the check convert a share the same way.

The report stores counts, not shares. A share is a ratio of two integers and its
decimal expansion can be infinite: three supported values at a step count have a
conditional release share of one third, and half of one third has no canonical
decimal text. Counts are exact, and every comparison is integer arithmetic. A
5% bound on 10,000 tasks is exactly 500.

A step count with zero or one supported value for a dimension has no mix to
balance. Its per-step rows are `not_applicable`.

## When a bound is superseded

A bound is `superseded` when the coverage floor makes it impossible to hold, and
the release is not at fault. Two tests, both in counts:

- an interval bound: `n * maximum_count < denominator` or
  `n * minimum_count > denominator`, where `n` is the number of supported values
  at that scope. Each supported value needs at least one task, and their counts
  sum to the denominator, so no assignment exists.
- a per-step mix: the sum of the `minimum_count` values exceeds the denominator.
- a single value: `maximum_count < minimum_count`, which happens when the
  conditional release share is under half a task. Coverage requires one task and
  the upper bound forbids it, so the upper bound is the part that cannot hold.

This is the conflict [`task-structure.md`
section 6](../../../requirements/task-structure.md) says is reported rather than
resolved by dropping coverage. A superseded row is recorded and does not block,
and it is not a known miss, because there is nothing to accept.

A superseded row usually means the coverage check at the same scope is a miss.
The coverage miss is the real defect, and it is the row that blocks.

## Outcomes

| Outcome | Meaning |
|---|---|
| `pass` | The check holds. |
| `miss` | The check fails. |
| `superseded` | The coverage floor makes the bound impossible. |
| `not_applicable` | Zero or one supported value at this scope, so there is no mix. |
| `deferred` | The requirement is outside the release implementation scope. |

The outcome says what happened. A second field, `disposition`, says what a miss
costs:

| Disposition | A miss |
|---|---|
| `enforced` | Blocks the export until the owner accepts it. |
| `reported` | Is recorded and does not block. |
| `deferred` | Does not occur; the row's outcome is `deferred`. |

`reported` exists for the rows `DS-37` makes non-blocking: the narrow clue
operand form mix is computed and reported in P0 so the imbalance is visible, and
only the wide range can block. A `reported` miss is not a known miss, because
there is nothing to accept.

Every `enforced` miss blocks until the owner accepts it. The PRD calls the step
mix a target rather than a hard quota, and a target miss still goes to the owner:
section 8 says a miss is documented and accepted, not hidden. A requirement is
never quietly downgraded to a warning; if a check should not block, that is
written in its disposition.

An accepted miss is recorded in `known_misses` in `manifest.json`, one entry per
accepted row:

| Field | Meaning |
|---|---|
| `check` | The check name. |
| `scope` | `release` or the task reasoning step count. |
| `value` | The dimension value, when the check is per value. |
| `count`, `denominator` | The measured count and its denominator. |
| `minimum_count`, `maximum_count` | The bound the count missed. |
| `reason` | Why the owner accepts it. |

The check list above is the contract. `05` emits at least one row per listed
check, so a deferred requirement is visible rather than absent, and a report that
omits a check is itself a rejection.

## The report

The report is `checks` in `manifest.json`. It is a control document, not a
release table, and it is never passed to the LLM model.

Coverage row:

| Field | Meaning |
|---|---|
| `check` | The check name. |
| `scope` | `release` or `step_<n>`. |
| `supported` | The supported values at that scope. |
| `observed` | The values present in the release at that scope. |
| `missing` | `supported` minus `observed`. |
| `unexpected` | `observed` minus `supported`. |
| `outcome` | The outcome. |
| `disposition` | What a miss costs. |

Balance row:

| Field | Meaning |
|---|---|
| `check` | The check name. |
| `scope` | `release` or `step_<n>`. |
| `value` | The dimension value, or the program or answer key for a cap on a high-cardinality quantity. |
| `count` | The integer count. |
| `denominator` | The integer denominator. |
| `minimum_count`, `maximum_count` | The integer bound, or null when the bound is one-sided. |
| `outcome` | The outcome. |
| `disposition` | What a miss costs. |
| `acceptance` | Null, or the `known_misses` entry that accepts a miss. |

A `deferred` row carries the check, the scope, and the outcome, and measures
nothing, because the requirement is outside the release implementation scope.

A dimension with a small value set reports every value: task target category,
answer format, answer meaning, clue type, clue operand form, task reasoning step
count, split, and subset. A cap on a high-cardinality quantity reports the
extreme count, the program or answer that holds it, and the programs or answers
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
