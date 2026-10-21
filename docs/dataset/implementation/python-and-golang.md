# Python and Go

**Status:** draft, 2026-10-21. This document defines the language boundary for
the dataset generator. The decision is recorded in
[`../decisions.md`](../decisions.md) DS-22.

## Default

Go is the default for all dataset implementation work that is not CadQuery/OCP
or Python-critical. "Python-critical" means the work cannot be made correct
without Python execution semantics or a Python-only CAD library; convenience is
not a reason to choose Python. A new component starts in Go unless it meets one
of these exceptions.

| Work | Language | Why |
|---|---|---|
| CLI, orchestration, caching, manifests | Go | File, process, and data-flow work. |
| `01a` metadata, `01b` select, `01c` fetch, `01e` manifest | Go | Metadata, selection, and file handling; no Python semantics. |
| `01d` normalize programs | Python | Needs the Python tokenizer and AST to canonicalize Python program text. |
| `02a` static extraction | Python | Reads the Python AST and CadQuery calls. |
| `02b` execute CadQuery | Python | Needs the CadQuery and OCP runtime. |
| `02c` build graph | Go | Consumes typed execution output; does not import CadQuery. |
| Pipeline stages `03`–`05` | Go | Task planning, task enumeration, prompt rendering, validation, and export. |

Pipeline stage contracts are language-agnostic. The language boundary does not
change their models.

## Prompt text

All LLM-facing prompt text is data in `prompts.yaml`, not code:

- dataset question, clue, choice, and answer-instruction templates;
- evaluation-harness instructions.

Go and Python select template IDs and fill typed placeholders. Neither language
hardcodes prompt copy. The dataset and evaluation sections are separate
namespaces in the same file. Template changes bump the prompt version and hash.

## Parallelism

The Go entry point owns orchestration and worker pools. Python work runs in
separate processes; it is never loaded into the Go process.

Clearly parallel per program:

- `01c` fetch;
- `01d` normalize;
- `02a` static extraction;
- `02b` CadQuery execution, bounded by OCP memory;
- `02c` graph construction;
- `03b` task-definition construction;
- `04` prompt and choice rendering.

Global or mostly serial:

- `01b` selection, because quotas and caps are global;
- `01e` external manifest writing;
- `03a` release planning;
- `03c` deficit control loop;
- `05` final export, manifest assembly, and support-table copy.

`05` may run validation checks in parallel, but the release write is single
writer. Parallel output is always merged by a stable key so reruns are
deterministic.

## Process boundary

The Go entry point invokes Python workers. Bulk data crosses the boundary as
versioned Parquet tables; small control documents may use JSON. Go and Python do
not share process memory. Go code
does not import CadQuery or OCP. Python code does not own release state. New
Python code outside this list needs a decision.
