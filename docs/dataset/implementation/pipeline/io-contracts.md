# Pipeline stage interfaces

**Status:** draft, 2026-10-21. This is the authoritative typed I/O contract
between pipeline stages. Pipeline stage docs describe why and how; they do not restate
these interfaces. If a pipeline stage doc disagrees with this file, this file wins.

Typed model names are provisional. Their fields are defined when the owning
pipeline stage is specified.

## Stages

| Pipeline stage | Responsibility | Input model | Output model |
|---|---|---|---|
| `01-external-dataset-etl` | Read and normalize the CADEvolve Parquet cache. | CADEvolve Parquet cache | `NormalizedProgram`, `ExternalDatasetManifest` |
| `02-execute-cadquery-and-build-graph` | Extract static structure, execute CadQuery, build the graph. | `NormalizedProgram` | `CadGraph` |
| `03-enumerate-tasks` | Build task definitions and resolve gold answers. | `CadGraph` | `TaskDefinition` |
| `04-select-and-balance-release` | Select, balance, and split the release. | `TaskDefinition` | `SelectedTask` |
| `05-assemble-prompt-and-choices` | Render the prompt and choices. | `SelectedTask` | `ReleaseTable` |
| `06-validate-and-export-release` | Validate and export the release dataset. | `ReleaseTable` | `ReleaseArtifacts` |

## Sub-steps

| Pipeline stage | Sub-steps |
|---|---|
| `01` | `01a` read metadata, `01b` select pool, `01c` fetch pool, `01d` normalize programs, `01e` write manifest. |
| `02` | `02a` static extraction, `02b` execute CadQuery, `02c` build graph. |

Sub-steps have their own typed models in their parent pipeline stage doc.

## Contract invariants

- A pipeline stage output is immutable once written for a given input and version.
- A `NormalizedProgram` has canonical text, a normalization version, and a
  stable program hash.
- `ExecutionResult` is either execution snapshots or a failure tombstone.
  Failure is data, not an exception across a pipeline stage boundary.
- A `TaskDefinition` is the persisted, answer-bearing construction record. It has
  exactly one gold answer; ambiguous definitions are rejected.
- A `SelectedTask` references a task definition and adds the split, subset, and
  selection metadata. Selection does not change the definition.
- A `ReleaseTable` has one row per task, an answer-free prompt, and exactly one
  answer set per task. Rendering does not change the task definition.
- Answer columns never appear in the prompt.
