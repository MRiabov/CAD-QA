# Pipeline stage interfaces

**Status:** draft, 2026-10-21. This is the authoritative typed I/O contract
between pipeline stages. Pipeline stage docs describe why and how; they do not restate
these interfaces. If a pipeline stage doc disagrees with this file, this file wins.

This file covers stage boundaries only. Sub-step boundaries are owned by the
parent document, which defines the sub-step typed models and artifacts without
restating the parent interface.

Typed model names are declared with their fields in
[`streamlined/models/`](streamlined/models/README.md). This file owns the boundary between pipeline stages; the typed model
declarations own the field set.

## Stages

| Pipeline stage | Responsibility | Input model | Output model |
|---|---|---|---|
| `01-external-dataset-etl` | Read and normalize the CADEvolve Parquet cache. | CADEvolve Parquet cache | `NormalizedProgram`, `ExternalDatasetManifest` |
| `02-execute-cadquery-and-build-graph` | Extract AST structure, execute CadQuery, build the graph. | `NormalizedProgram` | `CadGraph` |
| `03-task-generation` | Plan the release, construct task definitions, resolve deficits by replanning or expanding data. | `CadGraph` | `TaskDefinition` |
| `04-render-prompt-and-choices` | Render the prompt and choices. | `TaskDefinition`, `NormalizedProgram`, `RenderConfig` | `ReleaseTable` |
| `05-validate-and-export-release` | Validate and export the release dataset. | `ReleaseTable`, `RenderConfig` | `ReleaseArtifacts` |

`RenderConfig` is the rendering control input: the validated
`PromptTemplateSet` and the release `RenderSeed` (a stable integer). It is not an
artifact; the same value is passed to `04` and `05`.

Pipeline stage rows list the primary typed inputs and outputs. `05` also reads
the task reasoning step support table, the `TaskQuotaPlan` support hash,
`balance.yaml`, the external dataset manifest, the external benchmark program
set, the failure partitions, and the deficit ledger; its Inputs section lists
them. The task and residual dataset release review ledgers are control inputs in
the same section; `05` writes the absence ledger itself.

## Sub-steps

| Pipeline stage | Sub-steps |
|---|---|
| `01` | `01a` read metadata, `01b` select pool, `01c` fetch pool, `01d` normalize programs, `01e` write manifest. |
| `02` | `02a` AST extraction, `02b` execute CadQuery, `02c` build graph. |
| `03` | `03a` allocate task quotas, `03b` construct task definitions, `03c` resolve deficits by replanning or expanding data. |

Sub-steps have their own typed models and I/O tables in their parent document.
Their field sets are declared in [`streamlined/models/`](streamlined/models/README.md).

## Contract invariants

- A pipeline stage output is immutable once written for a given input and version.
- A `NormalizedProgram` has canonical text, a normalization version, and a
  stable program hash.
- `CadQueryRuntimeExtractionResult` is either runtime captures or a failure tombstone.
  Failure is data, not an exception across a pipeline stage boundary.
- A `TaskDefinition` is the persisted, answer-bearing construction record. It has
  exactly one gold answer; ambiguous definitions are rejected.
- A `PromptTemplateSet` is validated before rendering. Every template ID is
  unique, every placeholder is declared with a form, and every variant uses
  exactly the declared placeholders. A missing, extra, or untyped placeholder is
  a release defect.
- A `RenderConfig` carries the validated `PromptTemplateSet` and the release
  `RenderSeed`. `04` derives the task render seed from the release seed and
  `task_id`; the derivation is part of the `04` version, identified by the
  manifest's `generator_version`. The release manifest records the release seed,
  the template version, and the template file hash.
- A `ReleaseTable` has one row per task, an answer-free prompt, and exactly one
  answer set per task. Rendering does not change the task definition.
- Answer columns never appear in the prompt.
