# Dataset artifacts

**Status:** draft, 2026-10-21. This document defines who writes and reads each
dataset artifact, and how artifacts are identified. Typed stage I/O is in
[`pipeline/io-contracts.md`](pipeline/io-contracts.md); this document owns
ownership and lifecycle, not field definitions.

## Artifact ownership

| Artifact | Writer | Readers | Identity | Notes |
|---|---|---|---|---|
| CADEvolve export | External | `01a` | Upstream dataset version | Immutable external input. |
| Raw program record | `01a` | `01b` | Export member or row plus upstream version | Preserves collection metadata. |
| Normalized program | `01b` | `02a`, `02b` | `program_sha256` plus normalization version | Carries `program_id` and canonical text. |
| External dataset manifest | `01c` | `06`, dataset card | External dataset version | Counts, hashes, and rejected records. |
| Static CadQuery model | `02a` | `02c` | Program hash plus extractor version | No geometry measurements. |
| Execution result | `02b` | `02c` | Program hash, CadQuery/OCP version, and environment | Either execution snapshots or a failure tombstone. |
| CAD graph | `02c` | `03` | Program hash, graph schema version, and execution result hash | One graph per program. |
| Task candidate | `03` | `04` | Canonical task identity | Exactly one gold answer; invalid candidates are rejected. |
| Prompted task | `04` | `05` | Task identity plus prompt and choice versions | Prompt is answer-free. |
| Release table | `05` | `06` | `release_id` | One row per task. |
| Release artifacts | `06` | Dataset consumers | `release_id` | `release.parquet`, `manifest.json`, `dataset-card.md`, `failures.jsonl`. |

`Failures` is a multi-writer record: every pipeline stage appends a failure with the
input identity and reason, and `06` exports the records as `failures.jsonl`.

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
- Python workers and Go dataset code exchange serialized artifacts. They do not
  share process memory.

## What is not here

- Field definitions and stage input/output models: `pipeline/io-contracts.md`.
- Release columns and consumer rules: `../requirements/release-dataset-contract.md`.
- Storage technology, table DDL, and file layout.
