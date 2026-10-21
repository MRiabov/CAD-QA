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

## Languages

Go is the default for dataset implementation. Python is used only when the work
needs Python execution semantics or a Python-only CAD library. "Python-critical"
means the work cannot be made correct without Python; convenience is not a
reason to choose Python. A new component starts in Go unless it meets one of
these exceptions.

| Work | Language | Why |
|---|---|---|
| CLI, orchestration, caching, manifests | Go | File, process, and data-flow work. |
| `01a` extract, `01c` manifest | Go | Archive and metadata handling; no Python semantics. |
| `01b` normalize programs | Python | Needs the Python tokenizer and AST to canonicalize Python program text. |
| `02a` static extraction | Python | Reads the Python AST and CadQuery calls. |
| `02b` execute CadQuery | Python | Needs the CadQuery and OCP runtime. |
| `02c` build graph | Go | Consumes typed execution output; does not import CadQuery. |
| Pipeline stages `03`–`06` | Go | Task enumeration, prompt rendering, selection, validation, and export. |

The Go entry point invokes Python workers. Data crosses the boundary as
versioned typed artifacts; Go and Python do not share process memory. Go code
does not import CadQuery or OCP. Python code does not own release state. New
Python code outside this list needs a decision.

## What belongs here

- pipeline stage docs, implementation contracts, and test contracts;
- typed I/O between pipeline stages;
- execution, graph-building, and release-building details.

## What does not belong here

- product requirements or user-facing promises;
- open product questions;
- the release consumer contract.
