# Python and Go

**Status:** draft, 2026-10-21. This document defines the language boundary for
the dataset generator. The decision is recorded in
[`decisions.md`](decisions.md) DS-ADR-02.

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

`DS-ADR-02` limits Python to work that needs Python execution semantics. The stack
document lists what that work may import; it is not a general permission for new
Python code.

The Go module and its shared package exist under `generator/`; pipeline stage
code lands one pipeline stage at a time. Go reads the YAML policy files
(`balance.yaml`, `checks.yaml`, `tolerance.yaml`) with `gopkg.in/yaml.v3`
(`STK-2`); Python keeps `PyYAML` for `prompts.yaml`.

## JSON at the boundary

The encoders are `orjson` in Python and `encoding/json` in Go; both are declared
in [`stacks.md`](stacks.md). Both languages produce the same canonical
definition bytes for `03b` construct task definitions: sorted keys, raw UTF-8, no
HTML escaping, and no binary floats. `03b` owns the exact serialization rule. Go
stays on the `encoding/json` v1 API: the `encoding/json/v2` package sorts object
keys only when `Deterministic(true)` is set, so the sorted-key rule would become
an option every encoder call must remember.

## Parquet at the boundary

Both languages write the same typed tables. `DS-ADR-03` forbids JSON columns, and
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

The concurrency contract for pipeline stages — which pipeline stages run in
parallel, the pass for each, and the `--jobs` bound — is in
[`run-contract.md`](run-contract.md#45-concurrency). This section records only
the language boundary; it does not repeat that table.

## Process boundary

The Go entry point invokes Python workers. Bulk data crosses the boundary as
versioned Parquet tables; small control documents may use JSON. Go and Python do
not share process memory. Go code
does not import CadQuery or OCP. Python code does not own release state. New
Python code outside this list needs a decision.

## Worker protocol

The Go orchestrator starts a bounded pool of Python workers once per
pipeline stage, not one process per request. The pool size is a pipeline stage's
concurrency bound from [`run-contract.md`](run-contract.md#45-concurrency). Each
worker is started as
`<python> -m cadqa_dataset_generator.worker <pipeline_stage>` and stays alive
until the orchestrator closes the pool, the worker crashes, or it reaches
`worker_request_limit` requests.

The worker imports its pipeline stage module and calls the module's optional
`preload()` hook before it accepts requests. It then writes one ready document
to standard output:

```json
{"ok": true, "protocol_version": 1, "result": {"ready": true}}
```

The orchestrator waits for the ready document before it sends the first request.
For `02b`, `preload()` imports CadQuery and OCP once; the 30-second execution
clock starts at the child's ready signal, not at worker start. The child is a
fresh address space; the preload is not repeated. A worker has one child in
flight at a time; with a shard pass, the number of concurrent children is the
number of active shards.

After the ready document, the worker serves newline-delimited JSON: one request
document per line on standard input, one response document per line on standard
output, one request at a time. A response is either
`{"ok": true, "protocol_version": 1, "result": ...}` or
`{"ok": false, "protocol_version": 1, "error": {"code": "...", "message": "..."}}`.
A handled
pipeline stage rejection is data and does not stop the worker. A crash writes a traceback
to standard error and no response; the orchestrator replaces the worker. Logs go
to standard error so standard output stays one JSON document per line.

A worker is replaced after a crash, a request timeout, or `worker_request_limit`
requests, whichever comes first. `worker_request_limit` is a pipeline-stage
constant; it bounds the damage from a leaked kernel object or slow memory growth
without paying an interpreter start per program. A worker that cannot start or
cannot import its pipeline stage's libraries is a pipeline stage failure, not a
per-program rejection.

The wire name is the snake-case pipeline stage name used by the failure record,
such as `01d_normalize_programs`; the worker maps it to the
`s<pipeline_stage>` module. `--list-stages` is a one-shot discovery command and
returns `{"protocol_version": 1, "stages": [...]}`; the orchestrator rejects a
worker whose version differs.

### Worker contract schema

The JSON documents are defined once, in JSON Schema 2020-12 under
`contracts/worker/v1/`. The envelope is `envelope.schema.json`; each typed
pipeline stage has one `<pipeline-stage>.schema.json` holding its request and
result definitions.

- `generator/python/cadqa_dataset_generator/contracts.py` is the executable authoring form. The
  Pydantic classes validate a request before a pipeline stage runs and a result
  before the worker writes it.
- `tools/contracts/export_worker_schemas.py` exports the checked-in schemas from
  those classes. `--check` fails when a schema is stale.
- `go-jsonschema` generates the Go structs from the same schema. The generator
  command is pinned in `generator/internal/shared/generate.go`; the output is
  checked in, so a normal build does not run the generator.
- `tools/ci_cd/check-worker-contracts` runs the exporter check and the Go
  generation, and fails when either output differs from the checked-in file.
- The envelope stays hand-written in both languages because it is small and
  stable; the per-pipeline-stage payloads are generated.

`01d` normalize programs is the first typed pipeline stage. `02a` and `02b`
keep the free-form dict path until their contracts land. Adding a
pipeline stage contract is a schema file, an exporter entry, a generation
line, and a fixture; it does not change the Parquet boundary (`DS-ADR-03`). A
breaking wire change creates `contracts/worker/v2/` and bumps
`WORKER_PROTOCOL_VERSION`.
