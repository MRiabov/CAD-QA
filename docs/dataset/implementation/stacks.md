# Stacks

**Status:** draft, 2026-11-20; reconciled with `main` 2026-11-21. This document
declares the Python and Go stacks for the dataset generator. Which language owns
which work is in [`python-and-golang.md`](python-and-golang.md); feature-wide
decisions are in [`../decisions.md`](../decisions.md).

## Rule

One library per job. A second Parquet, UUID, YAML, or CLI library is a defect,
not a preference. A row marked `open` has no chosen library; code must not pick
one by import. Choose a library by recording a decision in
[`../decisions.md`](../decisions.md), then update this document. Standard-library
packages are listed too, so replacing one with a third-party package is a visible
change.

## Pre-commit

`.pre-commit-config.yaml` is the executable hook list; this table records what is
wired and what is still a TODO.

| Scope | Hook | Status |
|---|---|---|
| Docs | `rumdl` | wired |
| Python | `ruff format` | wired |
| Python | `ruff check --fix` | wired |
| Python | `pyrefly check` | wired on the manual stage; promote to pre-commit when the old tree is removed |
| Lockfile | `uv lock --check` | wired |
| Go | `gofumpt` | `missing` — TODO; `generator/` exists, so this can be wired |
| Go | `goimports` | `missing` — TODO; `generator/` exists, so this can be wired |
| Go | `golangci-lint` | `missing` — TODO; `generator/` exists, so this can be wired |

`pytest` is not a pre-commit hook. It stays the test gate, because running the
full suite on every commit is slower than the commit cycle allows.

Run the hooks through `uv run pre-commit`. The pyrefly hook uses
`language: system`, so it resolves the project environment instead of installing
a second copy of the checker.

## Go

**Toolchain:** Go 1.27.4, the latest stable release at 2026-11-20, and module
`github.com/MRiabov/CAD-QA/generator`. `go.mod` lives at `generator/go.mod`. The
`go` command owns builds and tests; formatting and linting are in the table.

| Need | Choice | Status |
|---|---|---|
| Parquet read and write | `github.com/parquet-go/parquet-go` | decided, `DS-40` |
| Graph-local IDs | `github.com/google/uuid` | decided, `DS-40` |
| JSON | `encoding/json` | standard library; HTML escaping disabled |
| Logging | `log/slog` | standard library |
| Processes and cancellation | `os/exec`, `context` | standard library |
| CLI parsing and subcommands | `flag` | standard library; no third-party framework |
| YAML policy files (`balance.yaml`, `checks.yaml`, `tolerance.yaml`) | `gopkg.in/yaml.v3` | decided, `DS-46` |
| Formatting | `gofumpt`, `goimports` | decided, `DS-47` |
| Linting and static analysis | `golangci-lint` | decided, `DS-47` |
| Tests | `testing` | standard library |

`parquet-go` is the only Parquet library. `arrow-go` is not adopted; `DS-40`
records the UUID reason. Graph tables are read by streaming through
`parquet.GenericReader`; `parquet.ReadFile` is not used on them.

`flag` is enough for one subcommand per pipeline stage plus a few global flags.
A third-party CLI framework would add help and completion machinery the
generator does not use. `gopkg.in/yaml.v3` is the only YAML library in the Go
module (`DS-46`); the policy loaders call `KnownFields(true)` so an unknown key
is a load error, then validate the typed policy. Python keeps `PyYAML` for
`prompts.yaml`. `golangci-lint` is the single lint entry point and includes
`staticcheck`, `govet`, `errcheck`, `revive`, `gocritic`, and the other strict
checks listed in `DS-47`; `--fix` applies the auto-fixable findings. `gofumpt`
and `goimports` are the formatters.

The Go entry point is the only CLI. Python workers run as subprocesses, so Python
needs no CLI framework.

## Python

**Toolchain:** CPython 3.12 in `uv.lock`; `pyproject.toml` requires 3.11 or newer.
Packages are managed with `uv`. Formatting and linting use `ruff`; static
analysis uses `pyrefly` with `preset = "strict"`; tests use `pytest`, with
`pytest-xdist` for parallel runs and `hypothesis` for property tests. Docs are
formatted with `rumdl`; pre-commit runs the checks.

| Need | Choice | Status |
|---|---|---|
| Parquet read and write | `pyarrow` (`>=25.0`) | in use |
| Columnar analysis | `polars` (`>=2.1.0`) | in use, never on the graph path (`DS-41`) |
| Typed models | `pydantic` (`>=2.14`) | in use in `cadqa_dataset_generator` and `tools` |
| JSON | `orjson` with `OPT_SORT_KEYS` | in use in `cadqa_dataset_generator/cli.py` |
| YAML | `PyYAML` (`>=6.0`) | in use |
| CAD execution | `cadquery` (`>=2.8.0`), `OCP` | `02b` only |
| Program AST and tokens | `ast`, `tokenize` | `01d` and `02a` only |

`orjson` is chosen over `msgspec` because Pydantic is already the one
typed-record system; `msgspec` would add a second. `orjson` also returns bytes
and sorts keys with `OPT_SORT_KEYS`, which the canonical definition
serialization in `03b` construct task definitions depends on. JSON is not on the
bulk path — the graph and the release are Parquet — so this is an API decision,
not a performance one. `orjson` has no `default` hook, so a caller cannot encode
a typed record without dumping it through the schema first.

`polars` never rewrites a graph table because it drops the UUID logical type
(`DS-41`). `pyarrow` reads a Go-written UUID column as `pa.uuid()` from the
Parquet logical type.

## Current gaps

- The Go hooks (`gofumpt`, `goimports`, `golangci-lint`) are declared here but
  not wired in `.pre-commit-config.yaml`; `generator/` exists, so they can be
  enabled.
- `golangci-lint` has no configuration file yet; the check set in `DS-47` is the
  intended one.

## Open questions

None. The Go toolchain, CLI, YAML decoder, and lint stack are decided in
`DS-46` and `DS-47`.

## Resolved questions

- **Q1.** Which Go version and module path does the generator declare in
  `go.mod`? Resolved 2026-11-20: Go 1.27.4, the latest stable release, and module
  `github.com/MRiabov/CAD-QA/generator`.
- **Q2.** Which CLI library does the Go entry point use? Resolved 2026-11-20: the
  standard `flag` package with one `flag.FlagSet` per pipeline stage. No
  third-party CLI framework.
- **Q3.** Which Go YAML decoder reads the policy files? Resolved 2026-11-21:
  `gopkg.in/yaml.v3` in `DS-46`, with `KnownFields(true)` in the loader.
- **Q4.** Is `go vet` enough static analysis, or does the Go code adopt
  `golangci-lint`? Resolved 2026-11-20: `golangci-lint` with the strict check
  set in `DS-47`, plus `gofumpt` and `goimports` for formatting.
