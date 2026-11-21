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
| `02a` AST extraction | Python | Reads the Python AST and CadQuery calls. |
| `02b` execute CadQuery | Python | Needs the CadQuery and OCP runtime. |
| `02c` build graph | Go | Consumes typed execution output; does not import CadQuery. |
| Pipeline stages `03`–`05` | Go | Task planning, task enumeration, prompt rendering, validation, and export. |

Pipeline stage contracts are language-agnostic. The language boundary does not
change their models.

## Libraries and toolchains

The concrete Python and Go libraries, toolchain versions, and open library
questions are in [`stacks.md`](stacks.md). This document decides which language
owns work, not which library it imports.

`DS-22` limits Python to work that needs Python execution semantics. The stack
document lists what that work may import; it is not a general permission for new
Python code.

The Go module and its shared package exist under `generator/`; pipeline stage
code lands one pipeline stage at a time. Go reads the YAML policy files
(`balance.yaml`, `checks.yaml`, `tolerance.yaml`) with `gopkg.in/yaml.v3`
(`DS-46`); Python keeps `PyYAML` for `prompts.yaml`.

## JSON at the boundary

The encoders are `orjson` in Python and `encoding/json` in Go; both are declared
in [`stacks.md`](stacks.md). Both languages produce the same canonical
definition bytes for `03b` construct task definitions: sorted keys, raw UTF-8, no
HTML escaping, and no binary floats. `03b` owns the exact serialization rule.

## Parquet at the boundary

Both languages write the same typed tables. `DS-23` forbids JSON columns, and
`graph-persistence.md` defines the graph tables.

- Columns are typed. A struct, list, or tagged union is a Parquet struct, list,
  or nullable group, never a JSON string.
- Graph-local IDs are the native UUID logical type, never text.
- Go writes UUIDs with `parquet-go`, which maps `uuid.UUID` with no tag.
  `arrow-go` would need the `arrow.uuid` extension registered; it is not adopted.
- Python reads a Go-written UUID column with PyArrow and gets `pa.uuid()`. The
  Parquet logical type is enough; no `ARROW:schema` metadata is needed. The floor
  is PyArrow 25.0.0, where `read_schema` started preserving extension types
  (`apache/arrow#48254`).
- Polars has no UUID type (`pola-rs/polars#7175`, open). It reads the column as
  `Binary` and writes it back as `BYTE_ARRAY`, dropping both the physical type and
  the logical type. No Python stage rewrites a graph table.
- Read graph tables in batches, not whole. On the 6.39M-relation table, Go
  materializing every row costs 4.96 s and 2.16 GB, while streaming and keeping
  one program costs 3.27 s and 218 MB.

## Prompt text

All LLM-facing prompt text is data in `prompts.yaml`, not code:

- dataset question, clue, choice, and answer-instruction templates;
- evaluation-harness instructions.

Go and Python select template IDs and fill typed placeholders. Neither language
hardcodes prompt copy. The dataset and evaluation sections are separate
namespaces in the same file. Template changes bump the prompt version and hash.
The file's schema is in [`prompt-templates.md`](prompt-templates.md).

## Parallelism

The Go entry point owns orchestration and worker pools. Python work runs in
separate processes; it is never loaded into the Go process.

Clearly parallel per program:

- `01c` fetch;
- `01d` normalize;
- `02a` AST extraction;
- `02b` CadQuery execution, bounded by OCP memory;
- `02c` graph construction;
- `03b` task-definition construction;
- `04` prompt and choice rendering.

Global or mostly serial:

- `01b` selection, because quotas and caps are global;
- `01e` external manifest writing;
- `03a` task quota planning;
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

## Worker protocol

The Go orchestrator starts a Python worker as
`<python> -m cadqa_dataset_generator.cli <pipeline_stage>`, writes one JSON
request document to standard input, and reads one JSON response document from
standard output. The wire name is the snake-case pipeline stage name used by the
failure record, such as `01d_normalize_programs`; the worker maps it to the
`s<pipeline_stage>` module.

A response is either `{"ok": true, "result": ...}` or
`{"ok": false, "error": {"code": "...", "message": "..."}}`. Exit code 0 means
the worker handled the request, including a pipeline stage rejection returned as
data. Exit code 1 means the request could not be handled. A crash writes a
traceback to standard error and no response. Logs go to standard error so
standard output stays one JSON document.
