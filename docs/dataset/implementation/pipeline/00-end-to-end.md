# Dataset pipeline — end to end

**Status:** draft, 2026-10-21. This document is the narrative overview of the
dataset pipeline. The authoritative pipeline stage I/O is in
[`io-contracts.md`](io-contracts.md). Requirements are in
[`../../requirements/`](../../requirements/), and the consumer contract is in
[`../../requirements/release-dataset-contract.md`](../../requirements/release-dataset-contract.md).

## Why a pipeline

The release dataset is a consumer artifact. Producing it needs several
artifacts with different failure modes and caching behavior:

- the external dataset is read and normalized once;
- the CAD graph is expensive to build and can be cached per program;
- task enumeration and answer resolution can fail per task;
- choices and prompts are derived per task;
- selection and validation operate on the whole release.

Splitting these into pipeline stages gives each artifact a typed contract,
isolates failures, and makes retries and cache hits possible. Pipeline stage
boundaries are derived from the current artifacts, not from the archived
generator.

## Stages

| Pipeline stage | Responsibility | Output |
|---|---|---|
| [`01-external-dataset-etl.md`](01-external-dataset-etl.md) | CADEvolve Parquet cache → normalized programs and manifest. | Normalized programs. |
| [`02-execute-cadquery-and-build-graph.md`](02-execute-cadquery-and-build-graph.md) | Static extraction and CadQuery execution → CAD graph. | CAD graph. |
| [`03-enumerate-tasks.md`](03-enumerate-tasks.md) | Graph → task definition, clues, step count, identity, gold answer. | Task definitions. |
| [`04-select-and-balance-release.md`](04-select-and-balance-release.md) | Task definitions → selected definitions with splits. | Selected tasks. |
| [`05-render-prompt-and-choices.md`](05-render-prompt-and-choices.md) | Selected tasks → prompt and choices. | Release table. |
| [`06-validate-and-export-release.md`](06-validate-and-export-release.md) | Release table → validated release artifacts. | Release dataset. |

## Flow

```text
CADEvolve Parquet cache
  → normalized programs
  → CAD graphs
  → task definitions with gold answers
  → selected task definitions
  → release table with prompts and choices
  → release.parquet + failures.parquet + manifest + dataset card + support/
```

## Supporting docs

- Artifact ownership: [`../artifacts.md`](../artifacts.md).
- Selection math: [`../selection-math.md`](../selection-math.md).

## What is not here

- Product requirements: [`../../requirements/PRD.md`](../../requirements/PRD.md).
- Consumer columns and row counts:
  [`../../requirements/release-dataset-contract.md`](../../requirements/release-dataset-contract.md).
- Feature-wide decisions: [`../../decisions.md`](../../decisions.md).
- The archived generator:
  `docs/_archive/dataset-pre-rebuild-2026-10-21/`.
