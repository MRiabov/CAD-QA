# Dataset artifacts

**Status:** draft, 2026-10-21. This document defines who writes and reads each
dataset artifact, how artifacts are identified, and their storage format. Typed
pipeline stage I/O is in [`pipeline/io-contracts.md`](pipeline/io-contracts.md);
this document owns ownership, lifecycle, and format, not field definitions.

## Artifact ownership

| Artifact | Writer | Readers | Identity | Preferred format | Notes |
|---|---|---|---|---|---|
| CADEvolve Parquet cache | External | `01a` | Upstream dataset commit plus cache version | Parquet | Immutable external input. |
| Raw program record | `01a` | `01b` | Export member or row plus upstream version | Parquet | Preserves collection metadata. |
| Normalized program | `01b` | `02a`, `02b` | `program_sha256` plus normalization version | Parquet | Carries `program_id` and canonical text. |
| External dataset manifest | `01c` | `06`, dataset card | External dataset version | JSON | Counts, hashes, and rejected records. |
| Static CadQuery model | `02a` | `02c` | Program hash plus extractor version | Parquet tables | No geometry measurements. |
| Execution result | `02b` | `02c` | Program hash, CadQuery/OCP version, and environment | Parquet plus shape snapshot files | Either execution snapshots or a failure tombstone. |
| CAD graph | `02c` | `03` | Program hash, graph schema version, and execution result hash | Parquet tables | One graph per program. |
| Task candidate | `03` | `04` | Canonical task identity | Parquet | Exactly one gold answer; invalid candidates are rejected. |
| Prompted task | `04` | `05` | Task identity plus prompt and choice versions | Parquet | Prompt is answer-free. |
| Release table | `05` | `06` | `release_id` | Parquet | One row per task. |
| Release artifacts | `06` | Dataset consumers | `release_id` | Parquet, JSON, Markdown | `release.parquet`, `failures.parquet`, `manifest.json`, `dataset-card.md`. |

`Failures` is a multi-writer record: every pipeline stage appends a failure with
the input identity and reason, and `06` exports the records as
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
