# Dataset implementation

**Status:** draft, 2026-10-21. This directory states how the generator satisfies
the dataset requirements. It is not a product requirement.

The requirements are in [`../requirements/`](../requirements/). Feature-wide
decisions are in [`../decisions.md`](../decisions.md).

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
| [`task-step-support.md`](task-step-support.md) | Derived task reasoning step support tables used for coverage checks. |
| [`python-and-golang.md`](python-and-golang.md) | The Python and Go language boundary. |
| [`open-questions.md`](open-questions.md) | Centralized inventory of unresolved questions across pipeline docs. |
| [`missing-contracts.md`](missing-contracts.md) | Ephemeral audit backlog of absent contracts by priority and decision owner. |
| [`pipeline/testing/`](pipeline/testing/README.md) | Per-pipeline-stage test contracts and end-to-end tests. |
| [`pipeline/streamlined/`](pipeline/streamlined/README.md) | Executable "what" docs, without rationale. |

## What belongs here

- pipeline stage docs, implementation contracts, and test contracts;
- typed I/O between pipeline stages;
- artifact, planning-math, and language-boundary explanations shared across
  pipeline stages;
- execution, graph-building, and release-building details;
- code and schema naming under [`DS-30`](../decisions.md).

## What does not belong here

- product requirements or user-facing promises;
- open product questions;
- the release consumer contract.
