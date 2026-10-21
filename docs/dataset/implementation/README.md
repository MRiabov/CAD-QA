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

## Language boundary

The boundary between Python and Go is in
[`python-and-golang.md`](python-and-golang.md).

## What belongs here

- pipeline stage docs, implementation contracts, and test contracts;
- typed I/O between pipeline stages;
- execution, graph-building, and release-building details.

## What does not belong here

- product requirements or user-facing promises;
- open product questions;
- the release consumer contract.
