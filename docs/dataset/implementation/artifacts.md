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
| Normalized program | `01d` | `02a`, `02b`, `02c`, `04` | `program_sha256` plus normalization version | Parquet | Carries `program_id`, `cadevolve_program_family_id`, and canonical text. |
| External dataset manifest | `01e` | `05`, dataset card | External dataset version | JSON | Counts, hashes, and rejected records. |
| CadQuery program AST extraction result | `02a` | `02c` | Program hash plus extractor version | Parquet tables | No geometry measurements. |
| CadQuery program runtime extraction result | `02b` | `02c` | Program hash, CadQuery/OCP version, and environment | Parquet tables | Either runtime captures or a failure tombstone; no raw BRep. |
| CAD graph | `02c` | `03` | Program hash, graph schema version, and CadQuery program runtime extraction result hash | Parquet tables | One graph per program. |
| Task quota plan | `03a` | `03b`, `03c` | Plan version, seed, and balance policy version | Parquet or JSON | Quotas, family profiles, split assignment, and construction attempt budgets. |
| Prompt templates | Prompt authoring | `04`, evaluation harness | Template version plus file hash | YAML | `prompts.yaml`; all LLM-facing copy, with dataset and evaluation namespaces. Schema in [`prompt-templates.md`](prompt-templates.md); a missing, extra, or untyped placeholder is a validation error. |
| Balance policy | Release authoring | `03a`, `05` | Policy version plus file hash | YAML | `balance.yaml`; every tunable quota and balance number. Not a scope. |
| Check policy | Release authoring | `05` | Policy version plus file hash | YAML | `checks.yaml`; the release checks `05` runs. Not a scope. |
| Task definition | `03b` | `04` | Canonical task identity plus definition hash | Parquet | Persisted, answer-bearing construction record; invalid definitions are rejected. |
| Deficit ledger | `03b` | `03a`, `03c` | Plan version plus update sequence | JSON | Accepted and rejected counts and remaining deficits by quota target, family, task reasoning step count, and deficit class. |
| Release table | `04` | `05` | `release_id` | Parquet | One row per task; prompt is answer-free; carries `cadevolve_program_family_id` and the labeled choice pool. |
| Review pack renders | Review pack tool | Reviewer | `release_id` plus the sample key | PNG | Regenerable review evidence under `runs/manual_verification/`; not a release file. |
| Review ledger | Review pack tool | `05`, auditors | `(task_id, definition_sha256, prompt_sha256)` | Parquet | One row per review verdict; append-only. The tool writes it under `runs/`; `05` copies it into the release as a control document. Internal: recorded as `review_ledger_sha256` in the manifest and excluded from `release_id`. |
| Task reasoning step support tables | Task-step support QA | `05`, reviewers | Schema version | JSON | Five derived files used to check coverage; not generator inputs. |
| Pipeline stage failure record | Every rejecting pipeline stage | `05` | `failure_id` | Parquet | One partition per pipeline stage, written as Parquet parts. A failure row is a completed unit for resume. Schema in [`failure-record.md`](failure-record.md). |
| Run manifest | Orchestrator | Every pipeline stage, `status`, reviewers | `run_id` | JSON | Declared inputs, generator and component versions, policy file hashes, the run-level `TolerancePolicy`, and the local `run_number`. Written once before the first pipeline stage. Schema in [`run-contract.md`](run-contract.md). |
| Pipeline stage completion marker | Orchestrator, for each pipeline stage | Orchestrator, downstream pipeline stages, `status` | Pipeline stage identity plus `parts_sha256` | JSON | One per pipeline stage that writes an artifact. Written after the last Parquet part is durable. Schema in [`run-contract.md`](run-contract.md). |
| Tolerance policy | Release authoring | Orchestrator, `02c` | Policy version plus file hash | YAML | `tolerance.yaml`; the six `TolerancePolicy` entries. Copied into the run manifest with `tolerance_policy_version` and `tolerance_policy_sha256`. |
| Run cache | Orchestrator | Pipeline stages | `artifact_identity_sha256` | Parquet parts | Optional shared cache under `<runs_root>/cache`. Not a release artifact and not part of `run_id`. |
| Release artifacts | `05` | Dataset consumers | `release_id` | Parquet, JSON, Markdown | `release.parquet`, `failures.parquet`, `manifest.json`, `dataset-card.md`, `support/`. |

`Failures` is one partition per rejecting pipeline stage. Each pipeline stage
writes its own partition, and `05` merges the partitions into
`failures.parquet`. The row schema,
dedupe key, merge, and reconciliation rules are in
[`failure-record.md`](failure-record.md).

Bulk run state is Parquet. A pipeline stage commits one immutable Parquet part
per unit, and the part is the unit's completion marker;
[`run-contract.md`](run-contract.md) owns the persistence, flush, cache, and
resume rules. JSON is limited to the run manifest, pipeline stage completion
markers, the deficit ledger, and other small or rare control documents. `DS-39`
measured JSON text at 41x the Parquet size and 57x the read time for the CAD
graph.

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

- An artifact has exactly one writer. The failure record is one partition per
  pipeline stage, so each partition has one writer.
- A committed artifact is immutable for its identity. A unit recompute writes a
  new part and replaces the superseded part; a part is never edited in place. The
  pipeline stage completion marker names the current part set.
- Identity includes the input hash and every component version and policy hash
  that affects the output; the exact composition is in
  [`run-contract.md`](run-contract.md).
- A pipeline stage reads only the artifacts listed for it. It does not reach into another
  pipeline stage's private intermediate state.
- A rejected program or task is recorded with its pipeline stage and reason. It is never
  dropped silently.
- The prompt is the only LLM-facing artifact in the release. Answer columns stay
  out of the prompt.
- Python workers and Go dataset code exchange Parquet tables for bulk data; JSON
  is limited to small control documents. They do not share process memory.

## What is not here

- Field definitions and pipeline stage input/output models: `pipeline/io-contracts.md`.
- Release columns and consumer rules: `../requirements/release-dataset-contract.md`.
- Table DDL and graph partitioning: `pipeline/extraction/graph-persistence.md`.
- Run directory layout and part paths: [`run-contract.md`](run-contract.md).
