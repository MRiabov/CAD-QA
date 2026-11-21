# Review pack

**Status:** planned, 2026-11-21. The review gate is P0; the renderer and the
ledger writer land with the first release. This document is the tool contract;
the review gate rule is in
[`../pipeline/05-validate-and-export-release.md`](../pipeline/05-validate-and-export-release.md#review-gate).

## Purpose

Render a sample of the release so a person can confirm that each highlighted
entity is the one the clue names, that the answer matches the geometry, and that
the wording is clear, and record that judgement in a ledger the release gate can
read.

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
- the sample policy (the matrix below) and a selection seed.

## Outputs

One tool, two outputs.

| Output | Content | Lifecycle |
|---|---|---|
| `runs/manual_verification/review_pack/<release_id>/` | one render per sampled task and an `index.parquet` of task, hashes, render path, and matrix cell | regenerable; not a release file |
| `runs/manual_verification/review_pack/<release_id>/review-ledger.parquet` | one row per verdict | append-only; the tool's output |

The tool writes both. `05` reads the ledger, copies it into the release
directory as a control document, and never renders.

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

### Review ledger

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

This is the sampling contract `DA-3` says the review gate lacks.

## Review gate

`05` builds the required matrix from the support tables and the release rows and
requires, for every required cell, a current `pass` whose
`(definition_sha256, prompt_sha256)` matches the release row. A gap or a
`defect` blocks the export until the task is re-reviewed.

The manifest records `review_ledger_sha256`. The ledger is review provenance,
not a generation input: it is excluded from the `release_id` inputs, so
re-reviewing a release does not change its identity.

## First-release fallback

Until the pack exists, a per-program render of the final solid state plus the
prompt and answer text is enough to review one task. That is
`tools/manual-verification/render_task.py`, under the manual verification
convention in [`README.md`](README.md#manual-verification). The reviewer flags
tasks that need a closer look in the same ledger, with `verdict` and
`defect_note`.

## What this does not prove

- that the answer is true; the answer checks are in
  [`../pipeline/03-task-generation/03b-construct-task-definitions.md`](../pipeline/03-task-generation/03b-construct-task-definitions.md);
- that the sample is representative beyond the matrix;
- that the reviewer is independent of the release author.
