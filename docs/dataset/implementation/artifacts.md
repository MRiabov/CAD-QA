# Dataset artifacts

**Status:** draft, 2026-10-21. This document defines who writes and reads each
dataset artifact, how artifacts are identified, and their storage format. Typed
pipeline stage I/O is in [`pipeline/io-contracts.md`](pipeline/io-contracts.md);
this document owns ownership, lifecycle, and format, not field definitions.

## Artifact ownership

| Artifact | Writer | Readers | Identity | Preferred format | Notes |
|---|---|---|---|---|---|
| CADEvolve Parquet cache | External | `01a` | Upstream dataset commit plus cache version | Parquet | Immutable external input. |
| Program metadata | `01a` | `01b`, `03a` | Cache revision plus metadata schema | Parquet | No program text. |
| Program selection | `01b` | `01c`, `01e` | Selection policy version plus seed | Parquet | Active and reserve IDs, supplemental deltas, `cadevolve_program_family_id`, counts, and exclusions. |
| Program pool | `01c` | `01d` | Selection identity plus cache revision | Parquet | Only selected rows, including program text and `cadevolve_program_family_id`. |
| Normalized program | `01d` | `02a`, `02b` | `program_sha256` plus normalization version | Parquet | Carries `program_id`, `cadevolve_program_family_id`, and canonical text. |
| External dataset manifest | `01e` | `05`, dataset card | External dataset version | JSON | Counts, hashes, and rejected records. |
| CadQuery program AST extraction result | `02a` | `02c` | Program hash plus extractor version | Parquet tables | No geometry measurements. |
| CadQuery program runtime extraction result | `02b` | `02c` | Program hash, CadQuery/OCP version, and environment | Parquet tables | Either runtime captures or a failure tombstone; no raw BRep. |
| CAD graph | `02c` | `03` | Program hash, graph schema version, and CadQuery program runtime extraction result hash | Parquet tables | One graph per program. |
| Task quota plan | `03a` | `03b`, `03c` | Plan version plus seed | Parquet or JSON | Quotas, family profiles, split assignment, and construction attempt budgets. |
| Prompt templates | Prompt authoring | `04`, evaluation harness | Template version plus file hash | YAML | `prompts.yaml`; all LLM-facing copy, with dataset and evaluation namespaces. |
| Task definition | `03b` | `04` | Canonical task identity plus definition hash | Parquet | Persisted, answer-bearing construction record; invalid definitions are rejected. |
| Deficit ledger | `03b` | `03a`, `03c` | Plan version plus update sequence | JSON | Accepted and rejected counts and remaining deficits by quota target, family, and task reasoning step count. |
| Release table | `04` | `05` | `release_id` | Parquet | One row per task; prompt is answer-free; carries `cadevolve_program_family_id`. |
| Task reasoning step support tables | Task-step support QA | `03a`, `05`, reviewers | Schema version | JSON | Four derived files used to check coverage; not generator inputs. |
| Release artifacts | `05` | Dataset consumers | `release_id` | Parquet, JSON, Markdown | `release.parquet`, `failures.parquet`, `manifest.json`, `dataset-card.md`, `support/`. |

`Failures` is a multi-writer record: every pipeline stage appends a failure with
the input identity and reason, and `05` exports the records as
`failures.parquet`.

## Format policy

- Parquet is the default for an artifact with many rows.
- Known schemas use typed nested structs and lists, not one JSON string per row.
- JSON is for small control documents and opaque versioned payloads that cannot
  be typed.
- JSONL is an optional inspection export, never a pipeline stage or release
  contract.
- Large tables are partitioned by program or release where useful.
- The schema version is recorded in Parquet metadata and the manifest.
- JSON parsing is not used on a bulk data path.

## Lifecycle rules

- An artifact has exactly one writer, except the failure record.
- A written artifact is immutable. A changed input or version produces a new
  artifact, not an in-place edit.
- Identity includes the input hash and the version of the code or schema that
  produced the artifact.
- A pipeline stage reads only the artifacts listed for it. It does not reach into another
  pipeline stage's private intermediate state.
- A rejected program or task is recorded with its pipeline stage and reason. It is never
  dropped silently.
- The prompt is the only LLM-facing artifact in the release. Answer columns stay
  out of the prompt.
- Python workers and Go dataset code exchange Parquet tables for bulk data; JSON
  is limited to small control documents. They do not share process memory.

## What is not here

- Field definitions and stage input/output models: `pipeline/io-contracts.md`.
- Release columns and consumer rules: `../requirements/release-dataset-contract.md`.
- Table DDL, partitioning layout, and file paths.
