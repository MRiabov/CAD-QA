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
- planning and validation operate on the whole release.

Splitting these into pipeline stages gives each artifact a typed contract,
isolates failures, and makes retries and cache hits possible under the
[run contract](../run-contract.md). Pipeline stage
boundaries are derived from the current artifacts, not from the archived
generator.

A run is incremental. Each pipeline stage commits immutable Parquet parts as
units complete or at the flush interval, and a rerun resumes from them. The run
manifest fixes the inputs, component versions, policy hashes, and the run-level
tolerance policy; a changed input or version is a new run directory. The run
contract is [`../run-contract.md`](../run-contract.md).

## Stages

| Pipeline stage | Responsibility | Output |
|---|---|---|
| [`01-external-dataset-etl.md`](01-external-dataset-etl.md) | CADEvolve Parquet cache → normalized programs and manifest. | Normalized programs. |
| [`02-execute-cadquery-and-build-graph.md`](02-execute-cadquery-and-build-graph.md) | AST extraction and CadQuery execution → CAD graph. | CAD graph. |
| [`03-task-generation.md`](03-task-generation.md) | Plan quotas, construct task definitions, and resolve deficits by replanning or expanding data. | Task definitions. |
| [`04-render-prompt-and-choices.md`](04-render-prompt-and-choices.md) | Task definitions → prompt and choices. | Release table. |
| [`05-validate-and-export-release.md`](05-validate-and-export-release.md) | Release table → validated release artifacts. | Release dataset. |

## Flow

```text
CADEvolve Parquet cache
  → normalized programs
  → CAD graphs
  → task quota plan
  → task definitions with gold answers
  → [deficit loops: 03c → 03a → 03b, or 03c → 01b/01c/01d/02 → 03a → 03b]
  → release table with prompts and choices
  → release.parquet + failures.parquet + manifest + dataset card + support/
```

## Supporting docs

- Artifact ownership: [`../artifacts.md`](../artifacts.md).
- Planning math: [`../planning-math.md`](../planning-math.md).
- Run contract: [`../run-contract.md`](../run-contract.md).

## What is not here

- Product requirements: [`../../requirements/PRD.md`](../../requirements/PRD.md).
- Consumer columns and row counts:
  [`../../requirements/release-dataset-contract.md`](../../requirements/release-dataset-contract.md).
- Feature-wide decisions: [`../../decisions.md`](../../decisions.md).
- The archived generator:
  `docs/_archive/dataset-pre-rebuild-2026-10-21/`.
