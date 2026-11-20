# Pipeline stage interfaces

**Status:** draft, 2026-10-21. This is the authoritative typed I/O contract
between pipeline stages. Pipeline stage docs describe why and how; they do not restate
these interfaces. If a pipeline stage doc disagrees with this file, this file wins.

This file covers stage boundaries only. Sub-step boundaries are owned by the
parent document, which defines the sub-step models and artifacts without
restating the parent interface.

Typed model names are provisional. Their fields are defined when the owning
pipeline stage is specified.

## Stages

| Pipeline stage | Responsibility | Input model | Output model |
|---|---|---|---|
| `01-external-dataset-etl` | Read and normalize the CADEvolve Parquet cache. | CADEvolve Parquet cache | `NormalizedProgram`, `ExternalDatasetManifest` |
| `02-execute-cadquery-and-build-graph` | Extract AST structure, execute CadQuery, build the graph. | `NormalizedProgram` | `CadGraph` |
| `03-task-generation` | Plan the release, construct task definitions, resolve deficits by replanning or expanding data. | `CadGraph` | `TaskDefinition` |
| `04-render-prompt-and-choices` | Render the prompt and choices. | `TaskDefinition` | `ReleaseTable` |
| `05-validate-and-export-release` | Validate and export the release dataset. | `ReleaseTable` | `ReleaseArtifacts` |

## Sub-steps

| Pipeline stage | Sub-steps |
|---|---|
| `01` | `01a` read metadata, `01b` select pool, `01c` fetch pool, `01d` normalize programs, `01e` write manifest. |
| `02` | `02a` AST extraction, `02b` execute CadQuery, `02c` build graph. |
| `03` | `03a` allocate task quotas, `03b` construct task definitions, `03c` resolve deficits by replanning or expanding data. |

Sub-steps have their own typed models and I/O tables in their parent document.

## Contract invariants

- A pipeline stage output is immutable once written for a given input and version.
- A `NormalizedProgram` has canonical text, a normalization version, and a
  stable program hash.
- `CadQueryRuntimeExtractionResult` is either runtime captures or a failure tombstone.
  Failure is data, not an exception across a pipeline stage boundary.
- A `TaskDefinition` is the persisted, answer-bearing construction record. It has
  exactly one gold answer; ambiguous definitions are rejected.
- A `ReleaseTable` has one row per task, an answer-free prompt, and exactly one
  answer set per task. Rendering does not change the task definition.
- Answer columns never appear in the prompt.
