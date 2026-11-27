# Dataset implementation

**Status:** draft, 2026-10-21. This directory states how the generator satisfies
the dataset requirements. It is not a product requirement.

The requirements are in [`../requirements/`](../requirements/). Requirements-level
decisions are in [`../requirements/decisions.md`](../requirements/decisions.md);
implementation decisions that span pipeline stages are in [`decisions.md`](decisions.md).

## Pipeline

The generation pipeline starts at
[`pipeline/00-end-to-end.md`](pipeline/00-end-to-end.md). The I/O contract
between pipeline stages is
[`pipeline/io-contracts.md`](pipeline/io-contracts.md).

## Supporting docs

| Document | What it defines |
|---|---|
| [`artifacts.md`](artifacts.md) | Artifact ownership, identity, and lifecycle. |
| [`planning-math.md`](planning-math.md) | Priority, coverage, balance, split, and cap math. |
| [`task-step-support.md`](task-step-support.md) | The derived task reasoning step support table used for coverage checks and the balance denominator. |
| [`failure-record.md`](failure-record.md) | The row schema for a rejected program or task, and the rules that merge it. |
| [`run-contract.md`](run-contract.md) | The run manifest, incremental Parquet persistence, pipeline stage completion markers, cache, resume, command-line interface, and exit codes. |
| [`prompt-templates.md`](prompt-templates.md) | The `generator/config/prompts.yaml` artifact and its schema: template IDs, typed placeholders, label tables, variants, and validation. |
| [`python-and-golang.md`](python-and-golang.md) | The Python and Go language boundary. |
| [`file-trees.md`](file-trees.md) | Where the replacement generator's code, tests, fixtures, and config live. |
| [`stacks.md`](stacks.md) | Declared Python and Go toolchains and libraries. |
| [`open-questions.md`](open-questions.md) | Centralized inventory of unresolved questions across pipeline docs. |
| [`missing-contracts.md`](missing-contracts.md) | Ephemeral audit backlog of absent contracts by priority and decision owner. |
| [`pipeline/testing/`](pipeline/testing/README.md) | Per-pipeline-stage test contracts and end-to-end tests. |
| [`pipeline/streamlined/`](pipeline/streamlined/README.md) | Executable "what" docs, without rationale. |
| [`pipeline/streamlined/models/`](pipeline/streamlined/models/README.md) | Typed model declarations, ownership, and a pipeline stage boundary audit. |
| [`devtools/`](devtools/README.md) | Developer tools that are not pipeline stages: the dataset browser, the review ledgers it records, benchmarks, and doc checkers. |

## What belongs here

- pipeline stage docs, implementation contracts, and test contracts;
- typed I/O between pipeline stages;
- artifact, planning-math, and language-boundary explanations shared across
  pipeline stages;
- execution, graph-building, and release-building details;
- code and schema naming under [`TERM-2`](../requirements/terminology.md#4-naming-decisions).

## What does not belong here

- product requirements or user-facing promises;
- open product questions;
- the release consumer contract.
