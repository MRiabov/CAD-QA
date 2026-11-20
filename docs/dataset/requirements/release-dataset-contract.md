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
| `dataset-card.md` | Human-readable dataset card: scope, counts, splits, provenance, and the answer conventions per answer meaning — the angle convention, the signed material change, the declared position point and topology category, the membership boundary rule, and the answer precision. | One file. |
| `failures.parquet` | Rejected programs and tasks with reasons. | One per rejection; may be empty. |
| `support/` | Four task reasoning step support tables: `target-category-by-step.json`, `clue-type-by-step.json`, `answer-meaning-by-step.json`, `answer-format-by-step.json`. | Four files. |

`release.parquet` is the release dataset. It contains the gold answer because the
release is used for training, scoring, and audit. The `prompt` column is the only
LLM-facing column; the evaluation harness selects that column and does not pass
the answer columns to the LLM model.

Parquet is canonical. JSONL is an optional export for inspection; it is not a
second release format. Structured fields with a fixed schema use nested Parquet
column types; fields whose shape depends on an enum or version remain canonical JSON
strings.

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

| Column | Format | Required | Meaning |
|---|---|---|---|
| `task_id` | string | yes | Stable release key. It must not encode the answer. |
| `split` | enum `train`, `validation`, `test` | yes | Split assignment. The same CADEvolve program family stays in one split. |
| `subset` | enum `warmup`, `main` | yes | Warmup is the labeled 1-step subset. |
| `prompt` | string | yes | Exact LLM model input, including program text, question, task clues, choices, and answer instruction. |
| `prompt_sha256` | string | yes | Content hash of `prompt`. |
| `program_id` | string | yes | Stable program key shared by tasks from the same CadQuery program. |
| `program_sha256` | string | yes | Hash of the normalized CadQuery program text. |
| `cadevolve_program_family_id` | string | yes | Stable program family used as the split unit: a CADEvolve generator family or a CADEvolve-predicted ABC/ShapeNet mesh family. |
| `task_reasoning_step_count` | integer | yes | Number of task clue steps plus the task answer step, if any. |
| `target_category` | enum | yes | Task target category. |
| `clue_types` | list of enum | yes | Ordered task clue types; empty for a task with no task clue. |
| `answer_format` | enum | yes | Format the LLM model must return. |
| `answer_meaning` | enum | yes | What the answer is about. |
| `geometry_required` | boolean | yes | Whether at least one task clue depends on the built shape. |
| `gold_answer_json` | string | yes | Canonical JSON for the gold answer. |
| `answer_unit` | string or null | yes | Unit; null means unitless. |
| `tolerance_json` | string or null | yes | Canonical JSON tolerance; null means exact. |
| `scoring_rule` | enum `exact`, `numeric_tolerance`, `structured_exact` | yes | How the answer is checked. |
| `answer_schema_version` | string | yes | Version of the answer representation. |
| `answer_sha256` | string | yes | Hash of the canonical answer and scoring fields. |
| `evidence_json` | string | yes | Canonical JSON answer evidence: measured or derived, references, and rule. |

The first fourteen columns identify the task and support selection, review, and
reporting. The answer columns hold the gold answer, scoring fields, and answer
evidence. `prompt` is the only LLM-facing column; every other column stays out
of the LLM model input.

Question text, task clues, choices, and the answer instruction are not
duplicated as separate columns. They are part of `prompt`, which is the exact
LLM model input. A structured prompt record can be regenerated for audit if
needed.

The `prompt` column is answer-free. It must not contain the gold answer, content
derived from the answer, hidden entity identifiers, or scoring data.

`gold_answer_json` is parsed according to `answer_format`:

- multiple choice: the chosen label, as a JSON string;
- number: a JSON number;
- integer: a JSON integer;
- yes or no: a JSON boolean;
- 3D coordinate: a JSON array of three numbers;
- bounding box: a JSON object with `min` and `max` arrays;
- structured object: a JSON object with the documented fields.

Tolerance is explicit for every non-exact answer. This avoids relying on a
reader to infer the last stated place. For a numeric answer, a typical tolerance
is `{"kind": "absolute", "value": 0.005}`.
P2 choice audit: P2 implementation adds `choice_audit_json` for
multiple-choice tasks. It records the correct label, each distractor's error
mode, and which task clue or answer step it fails. The P0 and P1 scopes do not require this
column.

Answer evidence is nested in the answer columns because the first release has
10,000 tasks and the answer evidence is small enough to keep with the task. Split
answer evidence into a separate table only if a row becomes too large to scan or
transport.

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

- `release_id`, `schema_version`, `created_at`;
- `implementation_scope`;
- `generator_version` and upstream dataset version;
- task count and split counts;
- CADEvolve program family count and split counts by program family;
- task counts by task reasoning step count;
- warmup task count;
- distinct CAD program count;
- release-table hash and answer hash summary;
- prompt template version and `prompts.yaml` hash;
- coverage and balance summaries;
- support-table schema versions and hashes;
- known misses accepted by the owner;
- failure count.

The manifest is not a table. It describes the release and is never passed to
the LLM model.

## 8. Generation pipeline

Dataset generation starts at
[`../implementation/pipeline/00-end-to-end.md`](../implementation/pipeline/00-end-to-end.md).
