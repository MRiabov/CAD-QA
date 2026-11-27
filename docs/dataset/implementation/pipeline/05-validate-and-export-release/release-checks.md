# Release coverage and balance checks

**Parent:** [`../05-validate-and-export-release.md`](../05-validate-and-export-release.md).

**Status:** draft, 2026-11-20.

`03a` allocate task quotas plans against coverage and balance targets. This
document is the other half: how `05` validate and export release measures the
finished release against the same targets, and what a miss does.

The checks never change the release. `05` does not drop a task to make a share
fit. A miss is fixed by a new plan or accepted by the owner.

## One implementation of the conditional release share

The reference share is defined once, in the allocation code that `03a` and `05`
both call:

```text
reference_share(scope, quota_dimension, dimension_value)
  = policy_share(dimension_value)
    / sum(policy_share(v) for v in supported_values(scope, quota_dimension))
```

`policy_share` comes from `balance.yaml`. `supported_values` is the support-table
derivation's output: `03a` allocate task quotas calls the derivation in-process,
and `05` reads the tables it writes. One derivation, two readers, and `05` holds
no share of its own.

At a task reasoning step count the scope is that step count. At release scope the
supported values are all supported values of the dimension, so a dimension whose
policy target is `equal` gives one over the number of supported values.

A second definition would let the plan and the release check disagree about what
the plan was aiming at, and the release check would then be measuring a target
nobody planned for.

## What is counted

| Quantity | Dimension | Unit | Denominator | Release column |
|---|---|---|---|---|
| Task target category | `target_category` | task | tasks | `target_category` |
| Answer format | `answer_format` | task | tasks | `answer_format` |
| Answer meaning | `answer_meaning` | task | tasks | `answer_meaning` |
| Task reasoning step count | `task_reasoning_step_count` | task | tasks | `task_reasoning_step_count` |
| Built shape | `geometry_required` | task | tasks | `geometry_required` |
| CAD model | `program_id` | task | tasks | `program_id` |
| Correct answer | `correct_answer` | task | tasks | `answer_format`, `answer_meaning`, `gold_answer` or `choices` |
| Clue type | `clue_type` | clue occurrence | clue occurrences | `clue_types` |
| Clue reduction form | `clue_reduction_form` | clue occurrence that carries a reference | clue occurrences that carry a reference | `clue_reduction_form_profile` |
| Warmup | `warmup` | task | — | `subset` |
| Split | `split` | task | tasks | `split` |
| Release task count | `task_count` | task | — | one row per task |
| Extraction capability | `extraction_capability` | capability cell | — | the `GraphCompletenessReport` set |

Six of these need a word of explanation.

**Extraction capability is not read from the release table.** It is the only
release-scope check whose observed side is the accepted graphs: the release can
carry every task the constructor can build and still be missing a capability the
extraction contract declares. Its declared set, cell identity, and coverage rule
are in
[`extraction/validation.md`](../extraction/validation.md#the-must-extract-capability-set).

**A CAD model is a `program_id`.** One CadQuery program builds one shape, and the
release contract and `03a` both count distinct programs, so the two numbers are
the same number.

**A correct answer is `(answer_format, answer_meaning, gold_answer)`, with
`gold_answer` in its canonical text form, except for multiple choice.** It is deliberately coarser than `answer_sha256`, which also
covers the scoring fields. Two tasks that ask for the same number with different
tolerances have the same correct answer, and R-11 is about the answer, not about
the tolerance.

**A multiple-choice answer is counted by its answer value.** A label is a
position, not an answer: counting labels would collapse thousands of tasks into
seven values. The counted answer of a multiple-choice task is the `candidate` of
the entry whose label is `gold_answer.label`, read from `choices`. Every other
answer format counts `gold_answer` directly.

**A clue reduction form is counted only on clues that carry a reference.** A clue
with no reference has no form (`03b` construct task definitions), so it is not in
the denominator. `05` checks first that `clue_reduction_form_profile` has one entry
per `clue_types` entry, in the same order with the same clue type. That is part
of release table schema validation, so the two columns cannot disagree.

**Release task count is a dimension with one value.** It exists so the size floor
is a check like any other, not a special case in the export code.

## The check policy file

The check list is data in
[`generator/config/release-checks.yaml`](../../../../../generator/config/release-checks.yaml). `05` reads it, runs every check it
lists, and records one or more report rows per check. `manifest.json` records the
file version and hash, so a release names the check list it was measured against.

A check that is not in the file is not run. A report row whose check is not in
the file is a defect. That is what makes a missing check visible: the list is one
artifact, not a table in this document and a second table in code.

```yaml
- id: answer_format_share_range
  requirement: [R-7]
  arithmetic: share_range
  scope: release
  dimension: answer_format
  minimum: dimensions.answer_format.min
  maximum: dimensions.answer_format.max
  disposition: enforced
```

| Field | Meaning |
|---|---|
| `id` | Unique check name. It is the report row's `check` value. |
| `requirement` | The requirement sources the check enforces, from the closed set in this document. |
| `arithmetic` | The arithmetic. One of `coverage`, `count_floor`, `share_range`, `relative_range`, `share_target`, `set_equal`. |
| `scope` | `release`, or `per_step` for one row per task reasoning step count. |
| `dimension` | The counted quantity, from the table above. |
| `value` | For `share_range`, the one dimension value the check measures. |
| `minimum_value` | For `share_range`, the smallest dimension value in a cumulative share. |
| `disposition` | `enforced`, `reported`, or `deferred`. |
| bounds | The fields the `arithmetic` needs. |

`05` rejects an unknown field, an unknown `arithmetic`, a duplicate `id`, and a
bound reference that does not resolve in `balance.yaml`. A policy that fails
validation stops the export before any check runs. A `target` or `values` entry
that names a cell the support table marks unsupported is a policy error, like an
unknown key: an unsupported cell has no target and no share.

The requirement sources are `R-4`, `R-7`, `R-8`, `R-9`, `R-10`, `R-11`, `R-12`,
`R-15`, `R-19` for extraction capability coverage, `PRD-8` for the PRD section 8
target table, `release-contract-3` for the release contract's row-count table,
and `DS-REQ-18`.

### Bound references

A bound field is a number, or a dotted path into `balance.yaml`. A path that
names a mapping is indexed by the dimension value: `task_reasoning_step_share`
resolves per task reasoning step count and `release.splits` per split.

`release-checks.yaml` holds no number that `balance.yaml` already owns. The multiples
`0.5` and `2` are the per-step balance rule, and they stay in the check file
because they are the rule, not a policy setting.

### Arithmetic

| `arithmetic` | Bound fields | Holds when |
|---|---|---|
| `coverage` | none | The observed value set equals the supported value set at the scope. |
| `count_floor` | `minimum` | The count is at least `minimum`. |
| `share_range` | `minimum`, `maximum` | The share is inside the range. Either bound may be absent, which makes it a floor or a cap. |
| `relative_range` | `below`, `above` | The share is between `below` and `above` times its reference share. |
| `share_target` | `target`, `tolerance` | The share is within `tolerance` of `target`. |
| `set_equal` | `values` or `to` | The observed value set equals the listed values, or the named derived set. |

`to` names a derived set. `to: one_step_tasks` compares the warmup set with the
tasks that have one task reasoning step. `to: must_extract_capabilities` compares
the declared capability set with the declared cells at least one accepted graph
realizes; [extraction capability coverage](#extraction-capability-coverage)
defines both sides.

### Selecting the measured value

A `share_range` check measures the share of the denominator whose dimension
value is selected. `value` selects one value: `value: true` on
`geometry_required` measures the share of tasks that require the built shape.
`minimum_value` selects that value and every larger value: `minimum_value: 3` on
`task_reasoning_step_count` measures the share of tasks with at least three
task reasoning steps. With neither, the check measures every supported value and
emits one row per value. A check sets at most one of the two.

## Coverage

A `coverage` row carries the supported values, the observed values, the missing
values, and the released values the support table does not support at that step
count. A row that names one `(dimension, value, scope)` cell, including every
balance row, also carries `supported_cell` and `reason_code` from the support
table. That is how a zero is classified without shipping the matrix: a supported
cell with zero tasks is a gap, an unsupported cell with a target is a policy
defect, and a supported cell with a capacity shortfall is a deficit.

"Supported" means supported by the release implementation scope, as the support
tables record it. A value deferred to P1 has no row at that step count, and its
absence is not a gap in a P0 release.

A missing value makes the row a miss. A released value the support table does not
support at that step count is also a miss: it means the release contains a task
the specification says cannot exist, which is a defect in the constructor rather
than a coverage gap. A step count with no supported value for a dimension has
nothing to cover, and its row is `not_applicable`.

There is no whole-release coverage row for a dimension. Global coverage is the
union of the per-step rows, and a union row would let a value pass globally while
missing at the step count where it was required. The release-scope `set_equal`
checks are the exception, because they are about the release as a whole rather
than about a dimension's values.

## Extraction capability coverage

`extraction_capability_coverage` is the release-scope check that the extraction
contract's P0 capability list is realized. Its two sides are:

- **declared** — `MustExtractCapability`, the closed set in
  [`extraction/validation.md`](../extraction/validation.md#the-must-extract-capability-set).
  It comes from the P0 marks of the entity, relation, and measurement vocabulary,
  not from a graph, the census, or an earlier release.
- **observed** — the declared cells that at least one accepted program's
  `GraphCompletenessReport` carries with `actual_count > 0`
  ([`extraction/graph-completeness.md`](../extraction/graph-completeness.md#8-report)).
  `05` already reads that report set for `graph_completeness`.

Both sides are drawn from the declared set, so `set_equal` is exactly the
coverage requirement: a cell present in `declared` and absent from `observed` is a
miss. A realized P1 cell is outside both sides and is never an `unexpected`
value. The report row is the coverage/set_equal row, with `supported` carrying
the declared cells and `unexpected` empty.

The check exists because no support-table check can see this loss. A capability
missing from every accepted graph is missing from the fixture graphs too, so the
constructor produces no definition for it, the support table records that
dimension value as unsupported, and every per-step `coverage` row reads it as
`not_applicable`. The census and `capability_deficit` are quota-planning tools
over the same graphs and cannot substitute: they read the capability as absent,
not as a miss.

A miss is `enforced` and blocks the export. The one acceptance path is
`known_misses`, with the reason naming whether the capability is an extractor gap
or a corpus gap. Removing the cell from the declared set is a contract change to
[`extraction/validation.md`](../extraction/validation.md#the-must-extract-capability-set),
not a release decision.

## Outcomes and dispositions

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

`reported` exists for the rows `DS-REQ-18` makes non-blocking: the narrow clue
reduction form mix is computed and reported in P0 so the imbalance is visible, and
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

`05` emits at least one row per listed check, so a deferred requirement is
visible rather than absent, and a report that omits a check is itself a
rejection.

## Bound arithmetic

Every bound becomes an integer count before anything is compared:

```text
share range:      minimum_count = ceil(minimum_share * denominator)
                  maximum_count = floor(maximum_share * denominator)
relative range:   minimum_count = max(1, ceil(below * reference_share * denominator))
                  maximum_count = floor(above * reference_share * denominator)
target tolerance: minimum_count = ceil((target - tolerance) * denominator)
                  maximum_count = floor((target + tolerance) * denominator)
```

A lower bound rounds up and an upper bound rounds down, so a count inside the
range is also inside the range in shares. The other rounding is too loose: with a
reference share of one third and ten tasks, `floor` would accept one task at 0.3
times the share, and `ceil` would accept seven at 2.1 times it.

The `max(1, ...)` is the same rule [`task-structure.md`
section 6](../../../requirements/task-structure.md) states: when half of a
value's reference share is less than one task, one task satisfies the lower
bound. `03a` allocate task quotas uses the same conversion on the planned count,
so the plan and the check convert a share the same way.

The report stores counts, not shares. A share is a ratio of two integers and its
decimal expansion can be infinite: three supported values at a step count have a
reference share of one third, and half of one third has no canonical decimal
text. Counts are exact, and every comparison is integer arithmetic. A 5% bound on
10,000 tasks is exactly 500.

A step count with zero or one supported value for a dimension has no mix to
balance. Its per-step rows are `not_applicable`.

## When a bound is superseded

A bound is `superseded` when the coverage floor makes it impossible to hold, and
the release is not at fault. Three tests, all in counts:

- an interval bound: `n * maximum_count < denominator` or
  `n * minimum_count > denominator`, where `n` is the number of supported values
  at that scope. Each supported value needs at least one task, and their counts
  sum to the denominator, so no assignment exists.
- a per-step mix: the sum of the `minimum_count` values exceeds the denominator.
- a single value: `maximum_count < minimum_count`, which happens when the
  reference share is under half a task. Coverage requires one task and the upper
  bound forbids it, so the upper bound is the part that cannot hold.

This is the conflict [`task-structure.md`
section 6](../../../requirements/task-structure.md) says is reported rather than
resolved by dropping coverage. A superseded row is recorded and does not block,
and it is not a known miss, because there is nothing to accept.

A superseded row usually means the coverage check at the same scope is a miss.
The coverage miss is the real defect, and it is the row that blocks.

## The report

The report is `checks` in `manifest.json`. It is a control document, not a
release table, and it is never passed to the LLM model.

Coverage and `set_equal` row:

| Field | Meaning |
|---|---|
| `check` | The check name. |
| `scope` | `release` or `step_<n>`. |
| `supported` | The supported values at that scope. |
| `supported_cell`, `reason_code` | For a row that names one cell, whether it is feasible and why not. |
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
| `supported_cell`, `reason_code` | Whether the cell is feasible at this scope, and the support reason when it is not. |
| `count` | The integer count. |
| `denominator` | The integer denominator. |
| `minimum_count`, `maximum_count` | The integer bound, or null when the bound is one-sided. |
| `outcome` | The outcome. |
| `disposition` | What a miss costs. |

A cumulative `share_range` row (`minimum_value`) records that bound as its
`value`, so the row names the cumulative set it measured.

A `deferred` row carries the check, the scope, and the outcome, and measures
nothing, because the requirement is outside the release implementation scope.

A dimension with a small value set reports every value: task target category,
answer format, answer meaning, clue type, clue reduction form, task reasoning step
count, split, and subset. A cap on a high-cardinality quantity reports the
extreme count, the program or answer that holds it, and the programs or answers
over the bound. A program and a correct answer each have at least a thousand
values, so a row per value would bury the answer in the manifest, and the cap
only needs the offenders.

Rows are sorted by check name, then scope, then value, so two runs over the same
release produce the same report.

## Not here

- Multiple-choice fairness: the construction checks are in [`03b` construct task
  definitions](../03-task-generation/03b-construct-task-definitions/README.md), and
  the released pool recheck is in `05` validate and export release.
- Release table schema, prompt answer-freedom, `task_id` uniqueness, and split
  isolation: `05` validate and export release.
- The transfer overlap check (R-16): `05` validate and export release. It is a
  validity check, not a coverage or balance check, so it has no `release-checks.yaml`
  row and no accepted miss.
- Failure record reconciliation and the review gate: `05` validate and export
  release.
- The allocation equations: `03a` allocate task quotas.
- The support-table derivation: [`../../task-step-support.md`](../../task-step-support.md).
