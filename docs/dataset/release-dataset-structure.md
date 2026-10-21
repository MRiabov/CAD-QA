# Release dataset structure

**Status:** draft, 2026-10-21. This document defines the **release dataset**
only. It does not define external datasets, the CADEvolve dataset, LLM
reasoning-output datasets, training artifacts, or evaluation responses.

A release dataset is the tasks and answers for one priority slice, validated
and versioned for release. The task file and the answer data are separate
tables. The LLM model sees the prompt column only; answer data is used for scoring
and audit.

## 1. Scope

A release dataset contains one priority slice:

- P0: the first benchmark release;
- P1: the P0 tasks plus tasks with P1 inputs and at most five task reasoning
  steps;
- P2: all tasks, including tasks with six or more task reasoning steps.

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
| `tasks.parquet` | Task file: prompt and selection metadata. | One per task. |
| `answers.parquet` | Answer data: gold answer, scoring, and evidence. | One per task. |
| `manifest.json` | Release counts, versions, hashes, split counts, and coverage summaries. | One file. |
| `dataset-card.md` | Human-readable dataset card. | One file. |
| `failures.jsonl` | Rejected programs and tasks with reasons. | One per rejection; may be empty. |

`tasks.parquet` and `answers.parquet` are joined 1:1 by `task_id`. Neither table
may contain a task without a matching row in the other table.

Parquet is canonical. JSONL is an optional export for streaming or inspection;
it is not a second release format.

## 3. Row count

For the first P0 release:

| Property | Target |
|---|---|
| Tasks | At least 10,000 |
| Answers | Exactly the task count |
| Distinct CAD programs | At least 1,000 |
| Warmup tasks | 500 to 1,000, included in the task count |
| Training / validation / test | Approximately 70% / 15% / 15% |
| One task reasoning step | 5% target |
| Three or more task reasoning steps | At least 80% |

The task table and answer table have the same row count. `task_id` is unique
within a release. One CAD program may produce many tasks, so `program_id`
repeats.

P1 and P2 are later cumulative releases. Their exact counts are recorded in
`manifest.json`. The warmup-size question for releases above 20,000 tasks is
PRD Q10; the caps for a dominant CAD model and repeated answers are PRD Q11.

## 4. Task file columns

`tasks.parquet` has one row per task.

| Column | Format | Required | Meaning |
|---|---|---|---|
| `task_id` | string | yes | Stable release key. It must not encode the answer. |
| `split` | enum `train`, `validation`, `test` | yes | Split assignment. The same program stays in one split. |
| `subset` | enum `warmup`, `main` | yes | Warmup is the labeled 1-step subset. |
| `prompt` | string | yes | Exact LLM model input, including program text, question, task clues, choices, and answer instruction. |
| `prompt_sha256` | string | yes | Content hash of `prompt`. |
| `program_id` | string | yes | Stable program key shared by tasks from the same CadQuery program. |
| `program_sha256` | string | yes | Hash of the normalized CadQuery program text. |
| `task_priority` | enum `P0`, `P1`, `P2` | yes | Task priority from its inputs and task reasoning step count. |
| `task_reasoning_step_count` | integer | yes | Number of task clue steps plus the task answer step, if any. |
| `target_category` | enum | yes | Task target category. |
| `clue_types` | list of enum | yes | Ordered task clue types; empty for a task with no task clue. |
| `answer_format` | enum | yes | Format the LLM model must return. |
| `answer_meaning` | enum | yes | What the answer is about. |
| `geometry_required` | boolean | yes | Whether at least one task clue depends on the built shape. |

The prompt is the only LLM-facing column. The other columns are release
metadata for selection, review, and reporting; the evaluation harness must not
pass them to the LLM model.

Question text, task clues, choices, and the answer instruction are not
duplicated as separate columns. They are part of `prompt`, which is the exact
LLM model input. A structured prompt record can be regenerated for audit if needed.

Every task in `tasks.parquet` is answer-free. It must not contain the gold
answer, answer-derived evidence, hidden entity identifiers, or scoring data.

## 5. Answer data columns

`answers.parquet` has one row per task.

| Column | Format | Required | Meaning |
|---|---|---|---|
| `task_id` | string | yes | Join key to `tasks.parquet`. |
| `answer_format` | enum | yes | Duplicated for validation against the task file. |
| `gold_answer_json` | string | yes | Canonical JSON for the gold answer. |
| `answer_unit` | string or null | yes | Unit; null means unitless. |
| `tolerance_json` | string or null | yes | Canonical JSON tolerance; null means exact. |
| `scoring_rule` | enum `exact`, `numeric_tolerance`, `structured_exact` | yes | How the answer is checked. |
| `answer_schema_version` | string | yes | Version of the answer representation. |
| `answer_sha256` | string | yes | Hash of the canonical answer and scoring fields. |
| `evidence_json` | string | yes | Canonical JSON evidence: measured or derived, references, and rule. |

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

Evidence is nested in the answer row because the first release has 10,000 tasks
and the evidence is small enough to keep with the answer. Split evidence into a
separate table only if a row becomes too large to scan or transport.

## 6. One table or two?

A single **task** table is enough for the LLM-facing side. Parquet supports
nested lists and structs, so prompt metadata, clue types, and choices do not
need extra tables.

A single **physical file** for the whole release is not enough. Parquet stores
one table per file. Putting the gold answer in `tasks.parquet` would put answers
in the same file the LLM model input comes from, which violates R-6 and DS-12.
Column-level hiding is not a release boundary.

The minimum clean release is therefore:

- `tasks.parquet`;
- `answers.parquet`;
- `manifest.json`;
- `dataset-card.md`;
- `failures.jsonl`.

That is one release dataset with two tables. A program table is not needed
initially: program text repeats inside `prompt`, and `program_id` plus
`program_sha256` support grouping and split checks. Add a program table only if
the repeated text becomes a storage or review problem.

## 7. Manifest

`manifest.json` records:

- `release_id`, `schema_version`, `created_at`;
- `priority_slice`;
- `generator_version` and upstream dataset version;
- task count, answer count, and split counts;
- task counts by task reasoning step count;
- warmup task count;
- distinct CAD program count;
- task-file and answer-data hashes;
- coverage and balance summaries;
- known misses accepted by the owner;
- failure count.

The manifest is not a table. It describes the release and is never passed to
the LLM model.

## 8. Open questions

- **Q1.** Is the release selection implemented by enumerating and cutting, or
  by planning quotas and generating into them?
  - **Option A — enumerate and cut.** Generate the valid tasks, then select a
    release that meets coverage and balance. Simple, but may do unused work.
  - **Option B — quota plan.** Allocate counts per task reasoning step count and
    dimension, then generate into the quotas with deterministic randomness.
    Avoids unused work, but must detect when the valid-task universe cannot fill
    a cell.
  - **Option C — hybrid.** Enumerate small cells and plan large cells.
  - **Recommendation:** This is an implementation choice, not a product
    decision. The contract fixes the release constraints and reproducibility; it
    does not mandate either strategy.

- **Q2.** Is a chain clue one task reasoning step or one step per relation? Is a
  clue that combines a relation and a property one condition or two?
  - **Option A — chain is one step; a compound sentence is one clue.** The
    current text allows “the face adjacent to X whose area is larger than X” as
    one clue.
  - **Option B — atomic predicates.** Each relation or property is one clue and
    one task reasoning step. The compound sentence becomes two clues; the chain
    becomes one clue per relation.
  - **Option C — hybrid.** Chains count per relation, but a relation plus a
    property in one sentence counts as one clue.
  - **Recommendation:** B. Example: “the face adjacent to X whose area is
    larger than X” is two steps; `A -> B -> C` is two steps. Split the prompt
    task clues accordingly. This makes the step count auditable.

- **Q3.** Is the conditional release share computed from the valid-task universe,
  or allocated from the global targets before selection?
  - **Option A — universe share.** Compute each value's share in the universe
    among the values supported at that step count, then require the release to
    approximate it.
  - **Option B — allocate quotas from the global targets, then fill from the
    universe.** Choose the target mix first, allocate counts per step count and
    dimension, then select tasks that fill the quotas.
  - **Option C — select, compute, repair.** Select a draft release, measure it,
    and move tasks until the targets hold.
  - **Recommendation:** B. Example: at step count 2, supported answer meanings
    `A`, `B`, and `C` have target shares 20%, 30%, and 50%; allocate the step-2
    quota in those proportions, fill from the universe, and report a conflict if
    the universe cannot fill a cell. This avoids the circular definition.

- **Q4.** Which answer formats are valid for each answer meaning?
  - **Option A — one answer format per answer meaning.** Simple, but identity
    would be limited to multiple choice.
  - **Option B — a compatibility table.** Each answer meaning lists its allowed
    answer formats.
  - **Option C — the generator chooses any format.** Flexible, but hard to
    audit.
  - **Recommendation:** B. Example mapping: identity -> multiple choice;
    volume, area, length, distance, angle -> number; count or rank -> integer;
    membership or validity -> yes or no; position -> 3D coordinate; extent ->
    bounding box; CadQuery workplane state -> structured object; material change
    -> number; topology change -> structured object.

- **Q5.** When is a task a duplicate of another task?
  - **Option A — canonical tuple.**
    `(program, target entity, clue sequence, task answer step, answer format)`.
  - **Option B — rendered prompt text.** Two tasks with the same prompt are
    duplicates.
  - **Option C — answer value.** Two tasks with the same answer are duplicates.
  - **Recommendation:** A, with canonical clue order. Example: the same target,
    clues, and answer but multiple choice vs number are two tasks. The same
    tuple rendered twice is one task. The same prompt text with two different
    answers is an ambiguity defect, not two tasks.
