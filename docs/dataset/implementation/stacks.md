# Stacks

**Status:** draft, 2026-11-20; reconciled with `main` 2026-11-21. This document
declares the Python and Go stacks for the dataset generator. Which language owns
which work is in [`python-and-golang.md`](python-and-golang.md); implementation
decisions that span pipeline stages are in [`decisions.md`](decisions.md). The toolchain decisions this file
declares are under [`## Local decisions`](#local-decisions).

## Rule

One library per job. A second Parquet, UUID, YAML, or CLI library is a defect,
not a preference. A row marked `open` has no chosen library; code must not pick
one by import. Choose a library by recording a decision under
[`## Local decisions`](#local-decisions), then update this document. Standard-library
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
| Repository | `file-length` (warn above 800 lines, fail above 1,200) | wired |
| Go | `gofumpt` | `missing` — TODO; `generator/` exists, so this can be wired |
| Go | `goimports` | `missing` — TODO; `generator/` exists, so this can be wired |
| Go | `golangci-lint` | `missing` — TODO; `generator/` exists, so this can be wired |

`pytest` is not a pre-commit hook. It stays the test gate, because running the
full suite on every commit is slower than the commit cycle allows.

The file-length hook is a whole-repository scan, so it runs when a `.go` or
`.py` file changes. Its policy is in
[`file-trees.md`](file-trees.md#file-length).

Run the hooks through `uv run pre-commit`. The pyrefly hook uses
`language: system`, so it resolves the project environment instead of installing
a second copy of the checker.

## Go

**Toolchain:** Go 1.27.4, the latest stable release at 2026-11-20, and module
`github.com/MRiabov/CAD-QA/generator`. `go.mod` lives at `generator/go.mod`. The
`go` command owns builds and tests; formatting and linting are in the table. A
host `go` older than the `go` directive downloads the declared toolchain, so
`GOTOOLCHAIN=local` requires 1.27.4 to be installed.

| Need | Choice | Status |
|---|---|---|
| Parquet read and write | `github.com/parquet-go/parquet-go` | decided, `STK-1` |
| Graph-local IDs | `github.com/google/uuid` | decided, `STK-1`; stdlib `uuid` not adopted |
| JSON | `encoding/json` | standard library v1 API; HTML escaping disabled |
| Logging | `log/slog` | standard library |
| Processes and cancellation | `os/exec`, `context` | standard library |
| CLI parsing and subcommands | `flag` | standard library; no third-party framework |
| YAML policy files (`balance.yaml`, `release-checks.yaml`, `tolerance.yaml`) | `gopkg.in/yaml.v3` | decided, `STK-2` |
| Worker contract structs | `github.com/atombender/go-jsonschema` | generated from `contracts/worker/v1/`, `DS-ADR-13` |
| Formatting | `gofumpt`, `goimports` | decided, `STK-3` |
| Linting and static analysis | `golangci-lint` | decided, `STK-3` |
| Tests | `testing` | standard library |

`parquet-go` is the only Parquet library. `arrow-go` is not adopted; `STK-1`
records the UUID reason. Graph tables are read by streaming through
`parquet.GenericReader`; `parquet.ReadFile` is not used on them.

The standard-library `uuid` added in Go 1.27 is not adopted. `parquet-go` maps
only `github.com/google/uuid.UUID` to the Parquet UUID logical type, so the
standard type would silently lose the annotation `DS-ADR-05` protects. The standard
package also has no name-based (v5) constructor, and `failure_id` is
`uuid5(namespace, key)` per `failure-record.md`.

`encoding/json` stays on the v1 API. On Go 1.27 the v1 package is backed by the
v2 implementation with v1 semantics, so existing behavior is preserved.
`encoding/json/v2` sorts object keys only when `Deterministic(true)` is set,
while the canonical JSON rule in `python-and-golang.md` relies on sorted keys by
default; migrating would require that option at every encoder call.

`flag` is enough for one subcommand per pipeline stage plus a few global flags.
A third-party CLI framework would add help and completion machinery the
generator does not use. `gopkg.in/yaml.v3` is the only YAML library in the Go
module (`STK-2`); the policy loaders call `KnownFields(true)` so an unknown key
is a load error, then validate the typed policy. Python keeps `PyYAML` for the
evaluation namespace; the dataset namespace and the prompt-template contract are Go-owned.
`golangci-lint` is the single lint entry point and includes
`staticcheck`, `govet`, `errcheck`, `revive`, `gocritic`, and the other strict
checks listed in `STK-3`; `--fix` applies the auto-fixable findings. `gofumpt`
and `goimports` are the formatters. On Go 1.27, `go test` also runs the
`stdversion` vet check, which reports standard-library symbols newer than the
`go` directive; it complements `golangci-lint` rather than replacing it.

`go-jsonschema` is the only code generator. It reads the checked-in worker JSON
Schema and writes the Go structs; the generator version is pinned in
`generator/internal/shared/generate.go`, and the output is checked in, so a
normal build does not run the generator. `DS-ADR-13` owns the contract rule.

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
| Columnar analysis | `polars` (`>=2.1.0`) | in use, never on the graph path (`DS-ADR-05`) |
| Typed models | `pydantic` (`>=2.14`) | in use in `cadqa_dataset_generator` and `tools` |
| JSON | `orjson` with `OPT_SORT_KEYS` | in use in `generator/python/cadqa_dataset_generator/worker.py` |
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
(`DS-ADR-05`). `pyarrow` reads a Go-written UUID column as `pa.uuid()` from the
Parquet logical type.

## Frontend devtool

**Toolchain:** `Node.js` 24 and pnpm, driven through Vite+ (`vp`). The task
browser is the only browser app: React and TypeScript for the UI, three.js for
the 3D view.
`pnpm-lock.yaml` is committed; `node_modules/` and `dist/` are ignored. The app
lives in `tools/manual-verification/task-browser/`; the generator does not import
it. The contract is [`devtools/task-browser.md`](devtools/task-browser.md), and
the workflow is the `vite-plus` skill.

| Need | Choice | Status |
|---|---|---|
| Dev server, check, build | Vite+ (`vp`) | in use in `task-browser/` |
| UI | React (`>=19`) with TypeScript | in use |
| 3D view | three.js | in use |
| Package manager | pnpm | in use; `pnpm-lock.yaml` is committed |

## Current gaps

- The Go hooks (`gofumpt`, `goimports`, `golangci-lint`) are declared here but
  not wired in `.pre-commit-config.yaml`; `generator/` exists, so they can be
  enabled.
- `golangci-lint` has no configuration file yet; the check set in `STK-3` is the
  intended one.

## Local decisions

### STK-1 — Go reads and writes Parquet with parquet-go

- **Status:** accepted (2026-11-20).
- **Context:** `DS-ADR-02` makes Go the default implementation language, and
  `graph-persistence.md` requires graph-local IDs to be the native Parquet UUID
  logical type, read and written directly. `02c` writes the three graph tables in
  Go and `03` reads them in Go, so the Parquet library decides whether that
  requirement is cheap or a trap. Two pure-Go libraries are viable. In
  `apache/arrow-go`, `parquet/pqarrow/schema.go` maps the Parquet UUID logical
  column type to the `arrow.uuid` extension only when that extension is registered, and
  otherwise falls back to `FixedSizeBinary(16)`; on write it maps
  `FIXED_SIZE_BINARY` to `FIXED_LEN_BYTE_ARRAY` with no logical type. The
  extension type exists in `arrow/extensions`, but nothing registers it, so the
  annotation is lost silently. `parquet-go` maps `uuid.UUID` from
  `github.com/google/uuid` to the UUID logical type with no tag and no
  registration. Both were measured on the 6.39M-relation table: materializing
  every row costs 4.96 s and 2.16 GB, streaming in batches and keeping one
  program costs 3.27 s and 218 MB.
- **Decision:** Go reads and writes Parquet with
  `github.com/parquet-go/parquet-go`, and carries graph-local IDs as `uuid.UUID`
  from `github.com/google/uuid`. `arrow-go` is not adopted. It returns only if a
  measured need for Arrow compute appears, and then the UUID extension must be
  registered and every UUID field typed as that extension. The
  standard-library `uuid` added in Go 1.27 is not a substitute: `parquet-go`
  maps only `github.com/google/uuid.UUID` to the Parquet UUID logical type, and
  the standard package has no name-based (v5) constructor for the deterministic
  `failure_id` in `failure-record.md`.
- **Consequences:** The Go schema is a struct with `parquet` tags, where `dict`,
  `optional`, `zstd`, and `list` express the encoding requirements in
  `graph-persistence.md`. Graph tables are read by streaming through
  `parquet.GenericReader` in batches; `parquet.ReadFile` materializes the whole
  table and is not used on them. A schema mismatch is an error at the boundary,
  which is where `graph_schema_version` is enforced.

### STK-2 — Go reads YAML policy files with gopkg.in/yaml.v3

- **Status:** accepted (2026-11-21).
- **Context:** `balance.yaml`, `release-checks.yaml`, and `tolerance.yaml` are YAML and
  are read by Go pipeline stages. Go has no standard-library YAML decoder, and
  `python-and-golang.md` requires a decision before adding a Go dependency.
- **Decision:** Go reads and validates the YAML policy files in
  `generator/config/` with `gopkg.in/yaml.v3`. It is the only YAML library in the Go module. A loader
  rejects unknown fields, then validates the typed policy.
- **Consequences:** A policy file with an unknown key is a load error, not a
  silently ignored setting. Python keeps `PyYAML` for the evaluation namespace;
  the dataset namespace and the prompt-template contract are Go-owned, so the two languages
  do not share a YAML loader or a second prompt-template contract.

### STK-3 — Go uses the standard CLI and a strict lint stack

- **Status:** accepted (2026-11-20; renumbered 2026-11-21 when `main` claimed
  `DS-ADR-06` and `DS-REQ-26`).
- **Context:** `DS-ADR-02` makes Go the default and `stacks.md` declares its
  libraries. The generator has one command with one subcommand per pipeline stage
  and a few global flags; it does not need generated shell completion or a nested
  command tree. YAML decoding is decided separately in `STK-2`, which `main`
  accepted with the first Go package, so this decision does not restate it. The
  owner prefers the strictest linters that are fast and can rewrite files, as
  `ruff` and `rumdl` do for Python and Markdown.
- **Decision:** The Go module is `github.com/MRiabov/CAD-QA/generator` on Go
  1.27.4, the latest stable release. The CLI uses the standard `flag` package with
  one `flag.FlagSet` per pipeline stage and no third-party CLI framework.
  Formatting is `gofumpt` and `goimports`; linting and static analysis are
  `golangci-lint`, configured with `staticcheck`, `govet`, `errcheck`, `revive`,
  `gocritic`, `errorlint`, `nilerr`, `exhaustive`, `prealloc`, `unparam`,
  `unused`, `ineffassign`, `misspell`, `forbidigo`, and `depguard`.
- **Consequences:** A CLI framework returns only if nested subcommands or
  generated completion become a real requirement. `go vet` runs through
  `golangci-lint`, so a separate vet invocation is optional; `go test` also runs
  the `stdversion` vet check on Go 1.27, so a standard-library symbol newer than
  the `go` directive fails both gates. Tool versions are pinned with `go.mod`
  `tool` directives. The Go hooks are declared in
  `stacks.md` but not yet wired in `.pre-commit-config.yaml`; that is a recorded
  gap, not a decision.

### STK-4 — Python type checking uses Pyrefly

- **Status:** accepted (2026-11-20; renumbered 2026-11-21 when `main` claimed
  `DS-ADR-06` and `DS-REQ-26`).
- **Context:** `pyproject.toml` declared mypy, but no mypy configuration or hook
  existed, and the owner prefers the fast Rust type checkers. `ty` is still beta
  and uses `0.0.x` versioning; `pyrefly` is stable at 1.x, understands Pydantic,
  and ships an official pre-commit hook. Pyrefly recommends `preset = "strict"`
  for most projects. `preset = "all"` enables every error kind, including new and
  low-signal checks, and is an audit mode rather than a default; on the old tree
  it reports 7,750 findings against 379 under `strict`. The old tree is
  superseded, but that is not a reason to adopt an unrecommended preset.
- **Decision:** Python type checking uses `pyrefly` with `preset = "strict"` and
  `python-version = "3.12"` in `pyproject.toml`. Mypy is removed from the dev
  dependencies. The pre-commit hook is installed on the manual stage until the
  old tree is removed; removing its `stages` line promotes it to a blocking
  hook.
- **Consequences:** `uv run pyrefly check` is the static-check command. New
  Python code is checked against the strict preset when the hook runs, but a
  finding does not block a commit until the manual stage is promoted.
  `preset = "all"` remains available as a one-off audit, not the project setting.
  `ty` returns if Pyrefly's diagnostics or performance become a measured
  problem.

### STK-5 — The task browser uses Vite+ with React and three.js

- **Status:** accepted (2026-11-23).
- **Context:** the task browser is the only browser app. It needs a task list,
  filters, a detail panel, and an interactive 3D view over a release table. The
  generator never imports it, so the choice is a devtool decision, not a pipeline
  stack decision.
- **Decision:** use Vite+ (`vp`) for dev, check, and build; React and TypeScript
  for the UI; three.js for the 3D view. The app lives in
  `tools/manual-verification/task-browser/`; `pnpm-lock.yaml` is committed and
  `node_modules/` and `dist/` are ignored. The API stays on the Python
  standard-library HTTP server, so the devtool adds no Python dependency.
- **Consequences:** `vp check` and `vp build` are the app's gates; the Vite+
  workflow is the `vite-plus` skill. The API serves the built `dist/` at its own
  origin, and the Vite dev server proxies `/api` to it. The three.js chunk is
  large; code-splitting the 3D view is optional.

## Open questions

None. The Go toolchain, CLI, YAML decoder, and lint stack are decided in
`STK-2` and `STK-3`.

## Resolved questions

- **Q1.** Which Go version and module path does the generator declare in
  `go.mod`? Resolved 2026-11-20: Go 1.27.4, the latest stable release, and module
  `github.com/MRiabov/CAD-QA/generator`.
- **Q2.** Which CLI library does the Go entry point use? Resolved 2026-11-20: the
  standard `flag` package with one `flag.FlagSet` per pipeline stage. No
  third-party CLI framework.
- **Q3.** Which Go YAML decoder reads the policy files? Resolved 2026-11-21:
  `gopkg.in/yaml.v3` in `STK-2`, with `KnownFields(true)` in the loader.
- **Q4.** Is `go vet` enough static analysis, or does the Go code adopt
  `golangci-lint`? Resolved 2026-11-20: `golangci-lint` with the strict check
  set in `STK-3`, plus `gofumpt` and `goimports` for formatting.
