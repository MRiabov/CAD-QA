# Pipeline stage interfaces

**Status:** draft, 2026-10-21. This is the authoritative typed I/O contract
between pipeline stages. Pipeline stage docs describe why and how; they do not restate
these interfaces. If a pipeline stage doc disagrees with this file, this file wins.

Typed model names are provisional. Their fields are defined when the owning
pipeline stage is specified.

## Stages

| Pipeline stage | Responsibility | Input model | Output model |
|---|---|---|---|
| `01-external-dataset-etl` | Read and normalize the CADEvolve export. | CADEvolve export | `NormalizedProgram`, `ExternalDatasetManifest` |
| `02-execute-cadquery-and-build-graph` | Extract static structure, execute CadQuery, build the graph. | `NormalizedProgram` | `CadGraph` |
| `03-enumerate-tasks` | Build task candidates and resolve gold answers. | `CadGraph` | `TaskCandidate` |
| `04-assemble-prompt-and-choices` | Render the prompt and generate choices. | `TaskCandidate` | `PromptedTask` |
| `05-select-and-balance-release` | Select, balance, and split the release. | `PromptedTask` | `ReleaseTable` |
| `06-validate-and-export-release` | Validate and export the release dataset. | `ReleaseTable` | `ReleaseArtifacts` |

## Sub-steps

| Pipeline stage | Sub-steps |
|---|---|
| `01` | `01a` extract export, `01b` normalize programs, `01c` write manifest. |
| `02` | `02a` static extraction, `02b` execute CadQuery, `02c` build graph. |

Sub-steps have their own typed models in their parent pipeline stage doc.

## Contract invariants

- A pipeline stage output is immutable once written for a given input and version.
- A `NormalizedProgram` has canonical text, a normalization version, and a
  stable program hash.
- `ExecutionResult` is either execution snapshots or a failure tombstone.
  Failure is data, not an exception across a pipeline stage boundary.
- A `TaskCandidate` has exactly one gold answer; ambiguous candidates are
  rejected.
- A `PromptedTask` has an answer-free prompt and, for multiple choice, a choice
  set.
- A `ReleaseTable` has one row per task and exactly one answer set per task.
- Answer columns never appear in the prompt.
