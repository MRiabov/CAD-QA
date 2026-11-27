# Review pack

**Status:** planned, 2026-11-21; dataset release absence and geometry residual ledgers defined 2026-11-27.
The review gate is P0; the renderer and the ledger writers land with the first
release. This document is the tool contract; the review gate rule is in
[`../pipeline/05-validate-and-export-release.md`](../pipeline/05-validate-and-export-release.md#review-gate).

## Purpose

Render a sample of the release so a person can confirm that each highlighted
entity is the one the clue names, that the answer matches the geometry, and that
the wording is clear, and record that judgement in a ledger the release gate can
read.

The pack answers three questions. Each has its own ledger:

| Ledger | Question | Unit | Method |
|---|---|---|---|
| Dataset release task review ledger | Is each released task clear and correct? | one release task | Human review of a render, stratified by the sampling matrix. |
| Dataset release absence ledger | Was each upstream absence legitimate? | one absent program, capability, or capacity | Exhaustive disposition with evidence. |
| Dataset release geometry residual ledger | Does the accepted pool carry geometry defects the checks cannot see? | one program drawn from the pinned dataset release program pool | Uniform sample, CAD graph kernel-oracle differential, statistical bound. |

## Why it is deferred

The pack needs the bound CAD graph entities and the `TaskDefinition` for each
sampled task. `05` is Go and receives neither. `MC-12` closed the release
projection, but the evidence shape has only been exercised on synthetic tasks.
The first release gives a real sample to build against. The missing data path is
`DA-3`/`MC-52` in the 2026-11-21 architecture audit.

## Inputs

- the release table for the sample;
- the `TaskDefinition` for each sampled task;
- the CAD graph and the normalized program for each sampled program;
- the five task reasoning step support tables, for the sampling matrix;
- the sample policy (the matrix below) and a selection seed;
- the deficit ledger from `03b` construct task definitions, and the
  per-pipeline-stage failure partitions, for the dataset release absence ledger;
- the per-program `GraphCompletenessReport` set from `02c` build CAD graph, for
  the dataset release absence ledger;
- the dataset release program pool from `01c` fetch program pool, after `01d`
  normalization, for the dataset release geometry residual-defect sample;
- the kernel-oracle runner, the run tolerance policy, and the CAD graph
  kernel-oracle differential version, for the dataset release geometry residual
  ledger.

## Outputs

One tool, four outputs.

| Output | Content | Lifecycle |
|---|---|---|
| `runs/manual_verification/review_pack/<release_id>/` | one render per sampled task and an `index.parquet` of task, hashes, render path, and matrix cell | regenerable; not a release file |
| `runs/manual_verification/review_pack/<release_id>/review-ledger.parquet` | one row per task verdict | append-only; the task browser writes the same file before the pack exists |
| `runs/manual_verification/review_pack/<release_id>/absence-ledger.parquet` | one row per absent program, capability, or capacity | append-only; `rejection_contact_sheet.py` writes it |
| `runs/manual_verification/review_pack/<release_id>/residual-ledger.parquet` | one row per program drawn from the pinned dataset release program pool | append-only; `residual_sample.py` writes it |

The tool writes all four. `05` reads the ledgers, copies them into the release
directory as control documents, and never renders.

### Renders

Each sampled task gets one render of the final solid state with the target and
every clue-bound entity in a distinct colour, labelled with its clue number, next
to the prompt text and the gold answer. The renderer matches a graph entity to
the shape by the geometric fingerprint: face centroid, area, normal, and bounding
box; edge endpoints and length; vertex point. Two entities in one state and
category with the same fingerprint are rejected at graph build, so the match is
unique.

The renderer is new code written against the current contracts. The deleted
explorer is a behaviour reference — one cached PNG per program, rendered
offscreen from the final `result` — not a base to extend.

### Dataset release task review ledger

| Column | Format | Null | Meaning |
|---|---|---|---|
| `task_id` | string | no | The reviewed task. |
| `definition_sha256` | string | no | The definition content the reviewer saw. |
| `prompt_sha256` | string | no | The rendered prompt the reviewer read. |
| `verdict` | enum `pending`, `pass`, `defect` | no | `pending` is not an approval. |
| `reviewer` | string | no | Who made the judgement. |
| `reviewed_at` | timestamp | no | When. Human provenance, not release identity. |
| `defect_note` | string | yes | Required when `verdict` is `defect`. |
| `render_sha256` | string | yes | The render the reviewer saw. |

The key is `(task_id, definition_sha256, prompt_sha256)`. A row with a different
key is a different review. The ledger is append-only within a run; a later row
supersedes an earlier row with the same key, and the latest row wins. `pending`
never satisfies the review gate.

`definition_sha256` covers the answer and `answer_evidence`; `prompt_sha256`
covers the rendered wording. A task whose content or wording changes gets a new
key and needs a new review. A task reproduced with the same inputs keeps its key
and its prior verdict.

`pack generate` writes the renders and one `pending` row per sampled task.
`pack record` appends `pass` or `defect` rows. The reviewer does not hand-edit
the ledger.

### Dataset release absence ledger

The dataset release task review ledger can only speak about tasks that became
release rows. The dataset release absence ledger speaks about the subjects that
did not: a rejected program, a declared capability no accepted graph realizes,
or a quota target whose deficit remains.
It is exhaustive, not sampled: one row per absent subject, keyed
`(pipeline_stage, subject_kind, subject_identity)`.

`rejection_contact_sheet.py` writes one `pending` row for every expected absence
and attaches an oracle render to each program row. The reviewer confirms the
proposed disposition or records a different one. `pack record` appends the
verdict; the latest row with the same key wins.

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
| `disposition` | enum `FailureDisposition` | no | Why the absence is legitimate, or `extractor_gap` when it is not. |
| `verdict` | enum `pending`, `pass`, `defect` | no | `pending` is not an approval. |
| `evidence` | string | no | Canonical reference: `failure:<failure_id>`, `completeness:<cell>`, `deficit:<entry key>`, or `render:<path>`. |
| `evidence_sha256` | string | yes | Hash of the evidence artifact, when it has bytes. |
| `render_sha256` | string | yes | The render the reviewer saw, for a program row. |
| `note` | string | yes | Why the disposition holds; at most 500 characters. |
| `reviewer` | string | no | Who made the judgement. |
| `reviewed_at` | timestamp | no | When. Human provenance, not release identity. |

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
`(pipeline_stage, subject_kind, subject_identity)`, with the namespace the UUID
v5 of `https://github.com/MRiabov/CAD-QA/review-pack` under the URL namespace.

`05` derives the expected key set, so the ledger cannot be satisfied by a
self-reported count:

- every failure row with `task_id` null yields a `program` key;
- every `MustExtractCapability` cell with `actual_count = 0` in every report
  yields an `extraction` key;
- every `DeficitLedger` entry with a remaining deficit above zero, including an
  accepted miss, yields a `capacity` key for `capacity_deficit` and a
  `capability` key for every other `DeficitClass`.

The absence gate requires a current `pass` for every expected key, and a `pass`
whose `disposition` is not `extractor_gap`. A `defect`, a missing key, or a
`pending` row blocks the export. `extractor_gap` always blocks, because it is a
generator defect, not a property of the corpus.

The disposition is the reviewer's judgement about the absence, not a second
failure-record function. A program row starts from the failure row's
disposition; a change needs a note. An extraction or task row has no failure row
to copy, so the reviewer assigns the disposition from the evidence.

### Dataset release geometry residual ledger

The dataset release task review ledger is stratified by what we already know to
look for; the dataset release absence ledger is exhaustive over what we know is
missing. Neither can find a defect class nobody named. The dataset release
geometry residual ledger draws programs uniformly from the normalized programs
of the pinned dataset release program pool and runs the CAD graph kernel-oracle
differential, so the release carries a stated bound on the share of the pool
with a detectable defect.

`residual_sample.py` writes one row per drawn program, in draw order. A mismatch
gets a disposition and a reviewer; a match needs neither.

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
| `disposition` | enum `FailureDisposition` | yes | Required on a mismatch; `extractor_gap` blocks. |
| `evidence` | string | yes | The differential report for the program. |
| `reviewer` | string | yes | Required on a mismatch. |
| `reviewed_at` | timestamp | yes | Required on a mismatch. |
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
`(run_id, program_id)`, with the same `review-pack` namespace.

The draw is uniform without replacement: sort the pinned dataset release program pool by
`sha256(utf8(sample_seed) || utf8(program_id))` ascending and take the first
`sample_size`, where `||` is concatenation with no separator and
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
policy.
It does not compare AST provenance, feature effects, selectors, or pair
relations; those are owned by the extraction-graph oracle set and the
completeness report.

With `sample_kind = sample` and no unexplained mismatch, the 95% upper
confidence bound on the share of the pinned dataset release program pool with a detectable differential
mismatch is `3 / sample_size`, which is `bound_p` at the policy size. A census
makes the result exact for the pool. An explained mismatch is one whose
disposition is `by_design` or `corpus_defect`; `extractor_gap` is never
explained and blocks the export.

### Dataset release geometry residual-defect sampling policy

**Decision (owner, 2026-11-27):** `bound_p = 0.01` at 95% confidence, so the
dataset release geometry residual-defect sample is `min(pool_size, 300)` programs. The bound is on defects the
kernel differential can detect. A defect class the differential cannot see is
outside the claim, which is why the absence review is exhaustive and the
task review is stratified rather than random.

## Sampling matrix

The sample is the cross product of the closed sets in the release:

- clue type;
- answer meaning;
- answer format;
- task reasoning step count.

A cell is required when the support tables say the combination is supported at
that step count and the release contains it. A cell the support tables mark
unsupported is recorded as `not_applicable`; it is not a silent gap. Steps 6–10
use at least 30 tasks per tier, or every task if the tier has fewer. The
selection inside a cell is deterministic from the release seed and the cell key,
so two runs review the same tasks.

This is the task review's sampling contract. The absence review is exhaustive
and the geometry residual-defect review is a uniform statistical sample; neither substitutes
for the matrix.

## Review gate

`05` checks three ledgers in the review gate.

**Dataset release task review ledger.** `05` builds the required matrix from the
support tables and the release rows and requires, for every required cell, a
current `pass` whose `(definition_sha256, prompt_sha256)` matches the release
row. A gap or a `defect` blocks the export until the task is re-reviewed.

**Dataset release absence ledger.** `05` derives the expected absence key set
from the failure partitions, the `GraphCompletenessReport` set, and the deficit
ledger, and requires a current `pass` for every key, with a `disposition` other
than `extractor_gap`. A missing key, a `pending` row, a `defect`, or an
`extractor_gap` blocks.

**Dataset release geometry residual ledger.** `05` requires this ledger to name the run
and the pinned dataset release program pool, to meet the `min(pool_size, 300)`
size, to contain one row per drawn program, and to carry no unexplained
mismatch. A short sample, a missing row, a mismatch without a disposition, or an
`extractor_gap` blocks.

`05` copies the three ledgers into the release as internal control documents and
records `review_ledger_sha256`, `absence_ledger_sha256`, and
`residual_ledger_sha256` in the manifest. They are review provenance, not
generation inputs: they are excluded from the `release_id` inputs, so
re-reviewing a release does not change its identity.

## First-release fallback

Until the pack exists, a task browser over the release table plus the prompt and
answer text is enough to review tasks. That is
`tools/manual-verification/task_browser.py` with the Vite+ app in
`tools/manual-verification/task-browser/`, under the manual verification
convention in [`README.md`](README.md#manual-verification); it lists, filters,
and opens tasks with an interactive 3D view and writes no static projection.
The reviewer records `pass` or `defect` with the browser's approval action,
which appends to the same ledger; `pack generate` reuses that writer and adds
the renders, the index, and the `pending` rows.

## What this does not prove

- that every answer is true; the
  [task-construction oracles](../pipeline/testing/oracles/task-construction/README.md)
  pin the supported cases and `03b` checks them, and the review gate is a sample;
- that the sample is representative beyond the matrix;
- that an absence disposition is correct; the contact-sheet render and the
  cited evidence are the check, so a `corpus_defect` that is really an
  `extractor_gap` can still pass;
- that the geometry residual bound covers a defect class the CAD graph kernel-oracle
  differential cannot detect; it is a bound on detectable mismatches, not on
  every defect;
- that the dataset release geometry residual-defect sample represents the
  release rather than the pinned dataset release program pool;
- that the reviewer is independent of the release author.
