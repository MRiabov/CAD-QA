# Release dataset contract

**Status:** draft, 2026-10-21. This document is the consumer contract for the
**release dataset** only. It does not define external datasets, the CADEvolve
dataset, LLM reasoning-output datasets, training artifacts, or evaluation
responses.

A release dataset is the tasks and answers produced by one implementation scope,
validated and versioned for release. It is one table with task and answer columns. The
LLM model sees the prompt column only; the answer columns are for training,
scoring, and audit.

## 1. Scope

A release dataset contains the tasks produced by one generator implementation
scope. The first release implements the P0 scope; later releases add P1 and P2
values and are cumulative. P0/P1/P2 are implementation order, not row labels: a
task is never P0, P1, or P2, and the release table has no task-priority column.

The release dataset is not:

- an external dataset such as CADEvolve or BenchCAD;
- an LLM reasoning-output dataset, LLM model output, or training artifact;
- an upstream program collection;
- an evaluation response file.

Those artifacts may feed or use a release dataset. They do not share its
structure.

## 2. Required artifacts

A release directory contains:

| Artifact | Role | Rows |
|---|---|---|
| `release.parquet` | Release table: prompt and answer columns. | One per task. |
| `manifest.json` | Release counts, versions, hashes, split counts, and coverage summaries. | One file. |
| `dataset-card.md` | Human-readable dataset card: scope, counts, splits, provenance, that `prompt` is the user message, and the answer conventions per answer meaning — the angle convention, the signed material change, the declared position point and topology category, the membership boundary rule, and the answer precision. | One file. |
| `failures.parquet` | Rejected programs and tasks with reasons. | One per rejection; may be empty. |
| `support/` | Five task reasoning step support tables: `target-category-by-step.json`, `clue-type-by-step.json`, `clue-reduction-form-by-step.json`, `answer-meaning-by-step.json`, `answer-format-by-step.json`. | Five files. |

Internal control documents are copied into the release but are not consumer
artifacts: `review-ledger.parquet`, `absence-ledger.parquet`, and
`residual-ledger.parquet`. They record review provenance and are excluded from
`release_id`.

### Dataset release review ledgers

The three internal control documents have the schemas below. The
[dataset browser](../implementation/devtools/dataset-browser.md) writes the task
review ledger; `05` derives the absence ledger from the failure partitions, the
`GraphCompletenessReport` set, and the deficit ledger; `residual_sample.py`
writes the geometry residual ledger. Only the task review ledger carries a human
verdict. The review gate invariants for all three are in
[`05` validate and export release](../implementation/pipeline/05-validate-and-export-release.md#review-gate).

All three use the UUID v5 namespace
`uuid5(URL namespace, "https://github.com/MRiabov/CAD-QA/dataset-review-ledger")`.

#### Dataset release task review ledger

| Column | Format | Null | Meaning |
|---|---|---|---|
| `task_id` | string | no | The reviewed task. |
| `definition_sha256` | string | no | The definition content the reviewer saw. |
| `prompt_sha256` | string | no | The rendered prompt the reviewer read. |
| `verdict` | enum `pending`, `pass`, `defect` | no | `pending` is not an approval. |
| `reviewer` | string | no | Who made the judgement. |
| `reviewed_at` | timestamp | no | When. Human provenance, not release identity. |
| `defect_note` | string | yes | Required when `verdict` is `defect`. |
| `scene_sha256` | string | yes | SHA-256 of the canonical scene payload the reviewer saw. |
| `scene_version` | integer | yes | The tessellation version that produced the scene. |

The key is `(task_id, definition_sha256, prompt_sha256)`. A row with a different
key is a different review. The ledger is append-only within a run; a later row
supersedes an earlier row with the same key, and the latest row wins. `pending`
never satisfies the review gate.

`definition_sha256` covers the answer and `answer_evidence`; `prompt_sha256`
covers the rendered wording. A task whose content or wording changes gets a new
key and needs a new review. A task reproduced with the same inputs keeps its key
and its prior verdict.

`scene_sha256` covers the canonical scene payload: the tessellated geometry, the
clue colours, and the labels. The browser serves that scene from
`program_sha256`, the `TaskDefinition`, the CAD graph, and `scene_version`, so
the ledger names the scene without a render file.

#### Dataset release absence ledger

The task review ledger can only speak about tasks that became release rows. The
absence ledger speaks about the subjects that did not: a rejected program, a
declared capability no accepted graph realizes, or a quota target whose deficit
remains. It is exhaustive, not sampled: one row per absent subject, keyed
`(pipeline_stage, subject_kind, subject_identity)`.

The row is derived, not judged. `disposition` is the upstream failure row's
`FailureDisposition`; a program row always carries one, and an extraction or
capacity row carries null when no failure row defines one. The ledger has no
verdict and no reviewer, and the browser shows it read-only.

| Column | Format | Null | Meaning |
|---|---|---|---|
| `ledger_id` | UUID v5 | no | Deterministic identity of the key. |
| `run_id` | string | no | The run the upstream artifacts belong to. |
| `release_id` | string | no | The release the ledger is evidence for. |
| `pipeline_stage` | enum | no | The upstream pipeline stage that dropped the subject, in the `failure-record.md` pipeline stage names. |
| `subject_kind` | enum `program`, `capability`, `capacity` | no | Which kind of absence. |
| `subject_identity` | string | no | The canonical identity below. |
| `deficit_class` | enum | yes | `DeficitClass` for a task or capacity absence; null for a program or extraction capability. |
| `reason_code` | string | yes | The upstream failure reason or deficit detail; null when the absence comes from the completeness report. |
| `disposition` | enum `FailureDisposition` | yes | The upstream failure row's disposition; null when no failure row defines one. |
| `evidence` | string | no | Canonical reference: `failure:<failure_id>`, `completeness:<cell>`, or `deficit:<entry key>`. |
| `evidence_sha256` | string | yes | Hash of the evidence artifact, when it has bytes. |

The identity is canonical per subject kind:

- `program:<program_id>@<program_sha256>` — one rejected or unfetchable program.
  `program_sha256` is the failure row's `input_sha256`.
- `extraction:<cell>` — one must-extract capability cell whose
  `actual_count` is zero across the report set.
- `capability:<quota_target>@<family>@<task_reasoning_step_count>@<deficit_class>`
  — one task-shape deficit from the deficit ledger. `<quota_target>` is the
  canonical `QuotaTargetRef` text (`<quota_dimension>=<dimension_value>`);
  `<family>` is `cadevolve_program_family_id`, or `unassigned` when null;
  `<deficit_class>` is `unclassified` when the entry's class is null.
- `capacity:<quota_target>@<family>@<task_reasoning_step_count>` — one capacity
  deficit from the deficit ledger.

`ledger_id` is `uuid5(namespace, key)` over the canonical JSON of
`(pipeline_stage, subject_kind, subject_identity)`.

#### Dataset release geometry residual ledger

The task review ledger is stratified by what we already know to look for; the
absence ledger is exhaustive over what we know is missing. Neither can find a
defect class nobody named. The geometry residual ledger draws programs uniformly
from the normalized programs of the pinned dataset release program pool and runs
the CAD graph kernel-oracle differential, so the release carries a stated bound
on the share of the pool with a detectable defect.

`residual_sample.py` writes one row per drawn program, in draw order. A mismatch
is not dispositioned: the review gate blocks every mismatch, so a legitimate mismatch is
fixed in the differential contract or the generator, not waived in the ledger.

| Column | Format | Null | Meaning |
|---|---|---|---|
| `ledger_id` | UUID v5 | no | Deterministic identity of `(run_id, program_id)`. |
| `run_id` | string | no | The run the pinned dataset release program pool belongs to. |
| `release_id` | string | no | The release the ledger is evidence for. |
| `draw_index` | integer | no | Zero-based position in the draw order. |
| `program_id` | string | no | The drawn program. |
| `program_sha256` | string | no | Its normalized-program hash. |
| `status` | enum `match`, `mismatch` | no | The CAD graph kernel-oracle differential result. |
| `mismatch_count` | integer | no | Compared rows outside tolerance or missing/orphan. |
| `mismatch_kinds` | list of string | no | The compared row kinds that disagreed; empty on a match. |
| `evidence` | string | yes | The differential report for the program. |
| `sample_seed` | string | no | The seed that orders the draw. |
| `pool_sha256` | string | no | SHA-256 over the canonical JSON of the sorted `[program_id, program_sha256]` pairs. |
| `pool_size` | integer | no | Programs in the pinned dataset release program pool. |
| `sample_size` | integer | no | Programs in the draw. |
| `sample_kind` | enum `sample`, `census` | no | `census` when every pool program is drawn. |
| `bound_p` | decimal string | no | The policy bound, `0.01`. |
| `draw_sha256` | string | no | SHA-256 over the canonical JSON of the drawn `[program_id, program_sha256]` pairs in draw order. |
| `differential_version` | string | no | The differential implementation. |
| `tolerance_policy_sha256` | string | no | The tolerance policy the comparison used. |

`ledger_id` is `uuid5(namespace, key)` over the canonical JSON of
`(run_id, program_id)`.

The draw is uniform without replacement: sort the pinned dataset release program
pool by `sha256(utf8(sample_seed) || utf8(program_id))` ascending and take the
first `sample_size`, where `||` is concatenation with no separator and
`sample_size = min(pool_size, ceil(3 / bound_p))`. At `bound_p = 0.01` that is
300 programs. A census is allowed and preferred when the CAD graph
kernel-oracle differential is affordable; it replaces the statistical bound
with an exact result for the pool.

`05` does not read the pool, so the reviewer verifies the draw against the `01c`
artifact; `pool_sha256`, `sample_seed`, and `draw_sha256` make that check
reproducible. `05` checks the ledger's arithmetic and row set.

The differential compares the persisted graph with a plain CadQuery and OCP
recomputation of the final solid state: entity counts by entity kind, incidence,
and the P0 measurements in the measurement catalog, under the run tolerance
policy. It does not compare AST provenance, feature effects, selectors, or pair
relations; those are owned by the extraction-graph oracle set and the
completeness report.

With `sample_kind = sample` and no mismatch, the 95% upper confidence bound on
the share of the pinned dataset release program pool with a detectable
differential mismatch is `3 / sample_size`, which is `bound_p` at the policy
size. A census makes the result exact for the pool.

#### Dataset release geometry residual-defect sampling policy

**Decision (owner, 2026-11-27):** `bound_p = 0.01` at 95% confidence, so the
dataset release geometry residual-defect sample is `min(pool_size, 300)`
programs. The bound is on defects the kernel differential can detect. A defect
class the differential cannot see is outside the claim, which is why the absence
review is exhaustive and the task review is stratified rather than random.

`release.parquet` is the release dataset. It contains the gold answer because the
release is used for training, scoring, and audit. The `prompt` column is the only
LLM-facing column; the evaluation harness selects that column and does not pass
the answer columns to the LLM model.

`prompt` is the user message. The dataset supplies no system prompt; a harness
may add one (`DS-REQ-24`).

Parquet is canonical. JSONL is an optional export for inspection; it is not a
second release format. Structured fields with a fixed schema use nested Parquet
column types, including the answer value, tolerance, and answer evidence.
Canonical JSON text is limited to an opaque payload that has no typed schema; in
P0 that is the `structured` CadQuery workplane-state answer only.

## 3. Row count

For the first release (P0 implementation scope):

| Property | Target |
|---|---|
| Tasks | At least 10,000 |
| Answer sets | Exactly one per task, in the same row |
| Distinct CAD programs | At least 1,000 |
| Warmup tasks | 5% of tasks, included in the task count |
| Training / validation / test | Approximately 70% / 15% / 15% |
| One task reasoning step | 5% target |
| Three or more task reasoning steps | At least 80% |

The release table has one row per task, and every row has exactly one answer set.
`task_id` is unique within a release. One CAD program may produce many tasks, so
`program_id` repeats. One CADEvolve program family may contain many programs, so
`cadevolve_program_family_id` also repeats.

Later releases add P1 and P2 values and are cumulative. Their exact counts are
recorded in `manifest.json`. Warmup is 5% of the release, with no absolute cap.
No CAD model and no correct answer is above 1% of tasks.

## 4. Release table columns

`release.parquet` has one row per task.

### Answer value schema

The answer columns are typed Parquet structs, not JSON text. A tagged union
carries exactly one non-null group matching `kind`, the same pattern the CAD
graph uses for `MeasurementValue`. `Point3D`, `BoundingBox`, and `EvidenceRef`
are the structs from the CAD graph schema.

```text
AnswerValue = STRUCT<
  kind: STRING,
  label: STRING | NULL,
  number_text: STRING | NULL,
  integer: INT64 | NULL,
  boolean: BOOLEAN | NULL,
  point: Point3D | NULL,
  bounding_box: BoundingBox | NULL,
  structured: STRING | NULL
>

Tolerance = STRUCT<
  kind: STRING,
  value_text: STRING | NULL,
  unit: STRING | NULL
>

AnswerEvidence = STRUCT<
  evidence_kind: STRING,
  evidence_rule: STRING,
  evidence_refs: LIST<EvidenceRef>,
  answer_equivalent_count: INT64,
  answer_equivalent_answer: AnswerValue,
  point_probe: STRUCT<
    point: Point3D,
    location: STRING,
    distance_to_face_surface: STRING,
    classifier: STRING,
    margin: STRING
  > | NULL
>
```

`AnswerValueKind`: `label`, `number`, `integer`, `boolean`, `point`,
`bounding_box`, `structured`.

- `label` is a multiple-choice position, `A` to `G`.
- `number` carries `number_text`, canonical decimal text. It is text, not a
  binary float, so Go and Python cannot disagree on formatting.
- `integer` carries `integer`; `boolean` carries `boolean`.
- `point` carries `point`; `bounding_box` carries `bounding_box`.
- `structured` carries `structured`, canonical JSON text for the
  CadQuery workplane-state answer. It is the only JSON text in the answer
  columns, and its shape is versioned by `answer_schema_version`.

`ToleranceKind`: `exact`, `absolute`, `relative`. `exact` has null `value_text`
and null `unit`; `absolute` carries `value_text` and a unit; `relative` carries
`value_text` and null `unit`.

`AnswerEvidence` carries the rule and references, the number of entries in the
answer-equivalent set, and the shared answer value. It does not carry the full
set: the set can hold one entry per candidate, so its size is bounded only by
`max_state_entities`. The full set stays in the task definition, and `05` reads
it from there when it needs to recheck uniqueness.

| Column | Format | Required | Meaning | Carries |
|---|---|---|---|---|
| `task_id` | string | yes | Stable release key. It must not encode the answer. | `TaskDefinition.task_id` |
| `split` | enum `train`, `validation`, `test` | yes | Split assignment. The same CADEvolve program family stays in one split. | `TaskDefinition.split` |
| `subset` | enum `warmup`, `main` | yes | Warmup is the labeled 1-step subset. | `TaskDefinition.subset` |
| `prompt` | string | yes | Exact LLM model input, including program text, question, task clues, choices, and answer instruction. | Rendered by `04` render prompt and choices |
| `prompt_sha256` | string | yes | Content hash of `prompt`. | SHA-256 of the `prompt` UTF-8 bytes |
| `program_id` | string | yes | Stable program key shared by tasks from the same CadQuery program. | `TaskDefinition.program_id` |
| `program_sha256` | string | yes | Hash of the normalized CadQuery program text. | `TaskDefinition.program_sha256` |
| `cadevolve_program_family_id` | string | yes | Stable program family used as the split unit: a CADEvolve generator family or a CADEvolve-predicted ABC/ShapeNet mesh family. | `TaskDefinition.cadevolve_program_family_id` |
| `task_reasoning_step_count` | integer | yes | Number of task clue steps plus the task answer step, if any. | `TaskDefinition.task_reasoning_step_count` |
| `target_category` | enum | yes | Task target category. | `TaskDefinition.target_category` |
| `clue_types` | list of enum | yes | Ordered task clue types; empty for a task with no task clue. | The clue type sequence of `clue_reduction_form_profile` |
| `clue_reduction_form_profile` | list of struct `{clue_type, clue_reduction_form}` | yes | Ordered clue type and clue reduction form of every task clue, one entry per `clue_types` entry. `clue_reduction_form` is null for a clue that carries no reference. | `TaskDefinition.clue_reduction_form_profile` |
| `answer_format` | enum | yes | Format the LLM model must return. | `TaskDefinition.answer_format` |
| `choices` | list of struct `{label, candidate}`, both strings | yes | The multiple-choice pool: the position label and the answer value it denotes, as canonical text. Empty for every other answer format. | `TaskDefinition.choice_pool`, label and answer value |
| `answer_meaning` | enum | yes | What the answer is about. | `TaskDefinition.answer_meaning` |
| `geometry_required` | boolean | yes | Whether at least one task reasoning step (a task clue step or the task answer step) depends on the built shape. | `TaskDefinition.geometry_required` |
| `gold_answer` | `AnswerValue` struct | yes | The gold answer, tagged by `kind`. | `TaskDefinition.gold_answer` |
| `answer_unit` | string or null | yes | Unit; null means unitless. | `TaskDefinition.answer_unit` |
| `tolerance` | `Tolerance` struct or null | yes | Answer tolerance; null means exact. | `TaskDefinition.tolerance` |
| `scoring_rule` | enum `exact`, `numeric_tolerance`, `structured_exact` | yes | How the answer is checked. | `TaskDefinition.scoring_rule` |
| `answer_schema_version` | string | yes | Version of the answer representation. | `TaskDefinition.answer_schema_version` |
| `answer_sha256` | string | yes | Hash of the canonical answer and scoring fields. | `TaskDefinition.answer_sha256`, copied |
| `answer_evidence` | `AnswerEvidence` struct | yes | Measured or derived evidence: the rule, references, the answer-equivalent count and shared answer, and the point probe. | `TaskDefinition.answer_evidence`, with the full set removed |

The `Carries` column says what the column is, not how it is produced: a column
carries a `TaskDefinition` field unchanged, the part of a field the release
needs, or a value that `04` render prompt and choices computes from the
definition. `04` writes every column of the release table.

`04` copies the typed answer value, tolerance, and answer evidence unchanged and
never re-serializes or recomputes an answer value. `03b` construct task
definitions already produced them, and a second serializer could format a number
differently. `04` has no serializer for an answer value.

`clue_types` is the clue type sequence of `clue_reduction_form_profile`, not a
second derivation from `task_clues`. The two columns then cannot disagree, and
`05` validate and export release still checks them, because a release file can be
corrupted after it is written.

`prompt_sha256` is SHA-256 over the UTF-8 bytes of the `prompt` string, with no
normalization and no added trailing newline. A consumer that normalizes the
prompt before hashing it gets a different value.

The columns before `gold_answer` identify the task, the answer space, and
the fields selection, review, and reporting need. The answer columns hold the
gold answer, scoring fields, and answer evidence. `prompt` is the only
LLM-facing column; every other column stays out of the LLM model input.

`answer_sha256` is computed by
[`03b` construct task definitions](../implementation/pipeline/03-task-generation/03b-construct-task-definitions/README.md)
from the definition's answer and scoring fields, and copied by `04` render
prompt and choices. Export does not recompute it. The hash covers a fixed set of answer
fields in a canonical form, so recomputing it in `04` would be a second
implementation of that canonical form, and a mismatch would be ambiguous between
a changed answer column and two serializers that drifted. `release_table_sha256`
protects the exported bytes, and `answer_sha256` identifies the answer across
releases.

Question text, task clues, choice descriptions, and the answer instruction are
not duplicated as separate columns. They are part of `prompt`, which is the exact
LLM model input. A structured prompt record can be regenerated for audit if
needed. The `choices` column is not a copy of the rendered choices: it holds the
label and the answer value, which the prompt does not state.

A label is a position, not an answer. For a multiple-choice row,
`gold_answer.label` is the label the LLM model must return, and `choices` maps
every label to the answer value it denotes, so the answer value stays recoverable
from the release.
The distinguishing facts a description is rendered from stay in the task
definition, because the release does not need them.

The `prompt` column is answer-free. It must not contain the answer value the label
denotes, content derived from that answer value, hidden entity identifiers, or
scoring data. A multiple-choice label is not answer data: the prompt lists every
label, and which one is correct is not stated.

`gold_answer` is checked against `answer_format`:

- multiple choice: `kind` is `label`, and `label` is the chosen label. The label's
  answer value is in `choices`;
- number: `kind` is `number`, and `number_text` is canonical decimal text;
- integer: `kind` is `integer`;
- yes or no: `kind` is `boolean`;
- 3D coordinate: `kind` is `point`;
- bounding box: `kind` is `bounding_box`;
- structured object: `kind` is `structured`, with canonical JSON text.

Tolerance is explicit for every non-exact answer. This avoids relying on a
reader to infer the last stated place. For a numeric answer, a typical tolerance
is `{kind: absolute, value_text: "0.005"}`.
P2 choice audit: P2 implementation adds `choice_audit_json` for
multiple-choice tasks. It records the correct label, each distractor's error
mode, and which task clue or answer step it fails. The P0 and P1 scopes do not require this
column.

Answer evidence is nested in the answer columns because the first release has
10,000 tasks. The release carries the set's size and shared answer, not the full
answer-equivalent set, so a row cannot grow with the candidate count. The full
set stays in the task definition; split it into a separate table only if a
consumer needs it in bulk.

## 5. Who consumes it

The release dataset is one artifact, but consumers read different columns:

- **Training:** reads `prompt` and the answer columns; the training recipe
  excludes the test split.
- **Evaluation:** passes only `prompt` to the LLM model; the scorer reads the
  answer columns.
- **Audit and review:** reads all columns.
- **Publishing:** the release includes answers. The held-out property comes from
  the split rule, not from hiding answer columns.

If a consumer needs a file without answers, derive a prompt-only view from the
release table. That view is a serving artifact, not the canonical release
dataset.

## 6. One table is enough

One Parquet table is enough. Parquet supports nested lists and structs, so
prompt metadata, clue types, choices, and answer evidence do not need extra tables.

A separate answer table is not required. The release must contain answers for
training and scoring, and the evaluation harness selects the prompt column. The
file boundary is not the leak boundary; column selection is.

A program table is not needed initially: program text repeats inside `prompt`,
and `program_id` plus `program_sha256` support grouping and split checks. Add a
program table only if the repeated text becomes a storage or review problem.
Likewise, add an answer evidence table only if answer evidence becomes too large
for one row.

## 7. Manifest

`manifest.json` records:

| Field | Value |
|---|---|
| `release_id` | `cadqarel:<sha256>` over the release inputs. |
| `schema_version` | The manifest schema version. |
| `created_at` | UTC timestamp of the export. It is not part of `release_id`. |
| `implementation_scope` | The release implementation scope; `P0` for the first release. |
| `generator_version` | The declared generator version. |
| `upstream_dataset_version` | `cache_revision` from the external dataset manifest, verbatim. |
| `external_dataset_manifest_sha256` | SHA-256 of the external dataset manifest. |
| `release_table_sha256` | SHA-256 of the `release.parquet` file bytes. |
| `external_benchmark_id`, `external_benchmark_revision`, `external_benchmark_split` | The transfer benchmark, its revision, and the declared split (R-16). |
| `external_benchmark_program_set_sha256` | SHA-256 of the external benchmark program set file. |
| `task_count`, `split_counts` | Tasks in the release, and tasks per `split`. |
| `program_family_count`, `program_family_split_counts` | CADEvolve program families in the release, and per `split`. |
| `task_reasoning_step_counts` | Tasks per `task_reasoning_step_count`. |
| `warmup_task_count` | Tasks with `subset = warmup`. |
| `distinct_cad_model_count` | Distinct `program_id` values. A CAD model is one program. |
| `answer_set_sha256` | SHA-256 over the sorted distinct correct answers. |
| `prompt_template_version`, `prompts_yaml_sha256`, `release_seed` | The template set version and file hash, and the seed `04` rendered from. |
| `balance_policy_version`, `balance_policy_sha256` | The balance policy version and file hash. |
| `checks_policy_version`, `checks_policy_sha256` | The check policy version and file hash. |
| `support_table_versions`, `support_table_sha256` | Schema version and file hash of each of the five support tables. |
| `checks` | One or more rows per coverage and balance check in [`05` validate and export release](../implementation/pipeline/05-validate-and-export-release/release-checks.md). |
| `known_misses` | The `checks` misses the owner accepted, with their reasons. |
| `failure_count` | Rows in `failures.parquet`. |
| `review_ledger_sha256` | SHA-256 of the dataset release task review ledger. |
| `absence_ledger_sha256` | SHA-256 of the dataset release absence ledger. |
| `residual_ledger_sha256` | SHA-256 of the dataset release geometry residual ledger. |

The manifest is not a table. It describes the release and is never passed to
the LLM model.

### 7.1 Release identity

`release_id` is `cadqarel:<sha256>` over the canonical JSON of the release
inputs:

| Input | What it pins |
|---|---|
| `generator_version` | The generator rules. |
| `implementation_scope` | Which requirement values the release implements. |
| `external_dataset_manifest_sha256` | The program pool and the upstream dataset. |
| `balance_policy_sha256` | The quota and balance policy. |
| `prompt_template_version`, `prompts_yaml_sha256` | The LLM-facing copy. |
| `release_seed` | The wording and order choices. |

The same inputs give the same id, so two runs of the same generation are the same
release. `created_at` is not an input, so re-exporting a generation keeps its id.

The external benchmark fields are not identity inputs. They are validation
provenance: the benchmark set changes no release row, only whether the transfer
overlap check passes. `05` records them in the manifest and excludes them from
`release_id`, as it does the three dataset release review ledger hashes. The run manifest pins
them because they are declared run inputs, so they are part of `run_id`
([`run-contract.md`](../implementation/run-contract.md#2-run-identity-and-the-run-manifest)).

The id names the generation, not the bytes. A table that differs while every
input matches is a generator defect: the fix is a `generator_version` bump, not a
new id. Byte integrity is `release_table_sha256`, which is a file hash and is
deliberately not the identity, because two Parquet writers emit different bytes
for the same rows.

### 7.2 Generator version

`generator_version` is a declared version string for the generator code, in the
form `cadqa-generator/<major>.<minor>.<patch>`, bumped when the generator's
behaviour changes. It is a constant in the code.

- It is not the git commit. A commit changes for docs, tests, and unrelated
  pipeline stages, and keying a release on it makes every commit look like a new
  generator.
- The component versions are what make a missed bump visible, and they stay on
  the artifacts that carry them: the graph schema version on the graph,
  `constructor_version` and `definition_schema_version` on each definition, and
  `answer_schema_version` on each release row. `05` validate and export release
  records the template and balance policy versions itself, because it also
  records their file hashes.
- A dirty working tree does not block the export. The declared version is the
  contract; the working tree is not.

A behaviour change without a version bump is a defect, and the release identity
inherits it. Recording the git commit instead would make every documentation and
test commit look like a new generator, which is the wrong trade for a dataset.

### 7.3 Answer set summary

`answer_set_sha256` is SHA-256 over the sorted, deduplicated correct answers of
the release. It uses the same answer identity as the `distinct_answer_count`
check in `05`: `(answer_format, gold_answer, answer_unit)`. Each answer is
encoded as the canonical JSON array of those three values, with `gold_answer` in
its canonical text form. The count and the
digest therefore describe the same set.

It is not a summary of the per-row `answer_sha256` column. That column covers the
answer and the scoring fields per task; `answer_set_sha256` answers "did the set of
distinct answers change between two releases" without shipping either table.

## 8. Dataset card

`dataset-card.md` is human-readable. Every number in it is copied from
`manifest.json`, never recomputed, so the card and the manifest cannot disagree.

| Section | Content |
|---|---|
| What this is | The dataset name, `release_id`, implementation scope, task count, and what a task asks for in one paragraph. |
| What a task is | The prompt parts, the frame convention, and that `prompt` is the user message with no system prompt supplied by the dataset. |
| Columns | The release table columns, that `prompt` is the only LLM-facing column, and that the answer columns are for training, scoring, and audit. |
| Counts and splits | Task count, tasks per task reasoning step count, split counts, warmup count, distinct CAD models, and distinct correct answers. Names the test set (R-14). |
| Answer conventions | The table below. |
| Provenance | `generator_version`, `upstream_dataset_version`, the selection identity, `balance_policy_version`, `prompt_template_version`, `release_seed`, and the support-table versions. |
| Known misses | Every entry in `known_misses`, with its reason, or a statement that the release has none. |
| Regenerating this release | The inputs listed under Provenance, the entry point at [`../implementation/pipeline/00-end-to-end.md`](../implementation/pipeline/00-end-to-end.md), and the step that rebuilds each artifact from them (R-18). |

The frame convention is stated as: `+x` is right, `+y` is back, `+z` is up.

The answer conventions table is required for every answer meaning present in the
release:

| Convention | The card states |
|---|---|
| Angle | Two faces: the angle between the outward normals, 0–180°. Two edges: the acute angle between the lines, 0–90°. Degrees. Parallel and perpendicular are renderings of 0 or 180° and 90°, not separate values. |
| Distance | The shortest distance between the two entities' geometry, at their closest points, or from the point to the nearest point of the entity. Millimetres; 0 when they touch or intersect. Never the distance between centroids. |
| Material change | Signed: added material is positive, a cut is negative. |
| Position | The point the question declares: a face area centroid, an edge midpoint, a vertex point, a region center of mass, or a solid state center of mass. A centroid is the measure-weighted center: the volume centroid (the center of mass under uniform density) for a solid state or region, the area centroid for a face, the length centroid for an edge, and the point for a vertex. The center of the bounding box is a different point and is never this answer. |
| Topology change | The signed change in the entity category the question declares. |
| Membership | Inside or outside. A point within the clear-case margin of a face surface is not used, so "on the boundary" is never an answer. |
| Answer precision | Four significant figures by default. The stated precision is the precision a scorer compares at. |
| Units | The `answer_unit` column; null means unitless. |

## 9. Generation pipeline

Dataset generation starts at
[`../implementation/pipeline/00-end-to-end.md`](../implementation/pipeline/00-end-to-end.md).
