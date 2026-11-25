# Pipeline testing strategy

**Parent:** [`README.md`](README.md).

One test contract per pipeline stage doc, in this directory, with the same file
stem. A pipeline stage doc owns its contract; a test doc says what the test does
and what it must not accept.

## The rule

Every pipeline stage has one adversarial integration test on its happy path, and
its failure-mode tests. The whole chain has one end-to-end test. No pipeline stage
is accepted without both.

The tests are integration-level, not unit tests. Everything except the external
inputs is real: CadQuery and OCP, the Parquet files, the Go and Python code, the
typed models, and the graph.

| Real | Mocked |
|---|---|
| CadQuery and OCP execution | The CADEvolve dataset download in `01c` fetch program pool. |
| Parquet read and write | The pinned external benchmark program set (`P1-W2`). |
| The code of every pipeline stage | — |
| The CAD graph and the release table | — |

A unit test on an internal function is not a substitute. If a pipeline stage can
only be tested by mocking its own storage, the storage contract is wrong.

## Test homes

The language boundary decides the home
([`../../python-and-golang.md#tests`](../../python-and-golang.md#tests)). In
short: a Go test sits beside its package and owns every Go pipeline stage,
Parquet table, oracle, golden record, release contract, and the `prompts.yaml`
contract; `generator/python/tests/` covers the worker; root `tests/ci_cd/` and
`tests/manual_verification/` cover the Python repo tooling. A Go test that needs
CadQuery or OCP starts the Python worker or tool and asserts on its output.

## Assert from the artifact

Every test reads its result back the way the next pipeline stage reads it: the Parquet
table through the same reader, not the in-memory struct. A test that checks the
in-memory value can pass while the production read path is broken.

- The in-memory value may be checked **in addition**, never instead.
- Counts, dedupe rules, and coverage are asserted on persisted rows.
- A re-run asserts byte-identical output.
- A test-specific query that bypasses the reader is banned: it hides a broken
  reader.

## Test-first

The test contract is written before the code exists, from
[`../io-contracts.md`](../io-contracts.md) and the doc it tests. It names the
fixture, the invocation, and the assertion.

A test that cannot be written from the contract is a missing contract, not a
testing problem. Name the sentence that is missing.

## One doc per pipeline stage

The group docs (`01`, `02`, `03`) are overviews. Tests pin the sub-steps, which
are the executable units.

| Test doc | Pipeline stage contract |
|---|---|
| [`00-end-to-end.md`](00-end-to-end.md) | [`../00-end-to-end.md`](../00-end-to-end.md) |
| [`00-run-contract.md`](00-run-contract.md) | cross-cutting; [`../../run-contract.md`](../../run-contract.md) |
| [`00-support-tables.md`](00-support-tables.md) | cross-cutting; [`../../task-step-support.md`](../../task-step-support.md) |
| [`01a-read-cadevolve-metadata.md`](01a-read-cadevolve-metadata.md) | [`../01a-read-cadevolve-metadata.md`](../01a-read-cadevolve-metadata.md) |
| [`01b-select-program-pool.md`](01b-select-program-pool.md) | [`../01b-select-program-pool.md`](../01b-select-program-pool.md) |
| [`01c-fetch-program-pool.md`](01c-fetch-program-pool.md) | [`../01c-fetch-program-pool.md`](../01c-fetch-program-pool.md) |
| [`01d-normalize-programs.md`](01d-normalize-programs.md) | [`../01d-normalize-programs.md`](../01d-normalize-programs.md) |
| [`01e-write-external-dataset-manifest.md`](01e-write-external-dataset-manifest.md) | [`../01e-write-external-dataset-manifest.md`](../01e-write-external-dataset-manifest.md) |
| [`02a-extract-cadquery-ast.md`](02a-extract-cadquery-ast.md) | [`../02a-extract-cadquery-ast.md`](../02a-extract-cadquery-ast.md) |
| [`02b-execute-cadquery.md`](02b-execute-cadquery.md) | [`../02b-execute-cadquery.md`](../02b-execute-cadquery.md) |
| [`02c-build-cad-graph.md`](02c-build-cad-graph.md) | [`../02c-build-cad-graph.md`](../02c-build-cad-graph.md) |
| [`03-task-generation/03a-allocate-task-quotas/README.md`](03-task-generation/03a-allocate-task-quotas/README.md) | [`../03-task-generation/03a-allocate-task-quotas/README.md`](../03-task-generation/03a-allocate-task-quotas/README.md) |
| [`03-task-generation/03b-construct-task-definitions/README.md`](03-task-generation/03b-construct-task-definitions/README.md) | [`../03-task-generation/03b-construct-task-definitions/README.md`](../03-task-generation/03b-construct-task-definitions/README.md) |
| [`03-task-generation/03c-resolve-deficits.md`](03-task-generation/03c-resolve-deficits.md) | [`../03-task-generation/03c-resolve-deficits.md`](../03-task-generation/03c-resolve-deficits.md) |
| [`04-render-prompt-and-choices.md`](04-render-prompt-and-choices.md) | [`../04-render-prompt-and-choices.md`](../04-render-prompt-and-choices.md) |
| [`05-validate-and-export-release.md`](05-validate-and-export-release.md) | [`../05-validate-and-export-release.md`](../05-validate-and-export-release.md) |

Every doc in this table is written. A missing row would be a missing test, not a
pipeline stage without tests.

`00-support-tables.md` is one cross-cutting test: the support tables are an
observation over the fixture set, not a pipeline stage output. `00-run-contract.md`
is the other: the run manifest, Parquet parts, resume rule, and exit codes span
every pipeline stage.

## Typed model and structure checks

Two contracts are checked outside pytest, because they read the whole docs tree
rather than a changed test:

- **Folder mirror.** `tools/ci_cd/check-doc-mirror` requires the same relative
  path under `streamlined/` and `testing/` for every pipeline stage and sub-step
  contract doc. `decisions.md`, `algorithm/`, and `extraction/` are exempt. It
  runs in the `quality-and-plan` CI job and as a pre-commit hook.
- **Typed model declarations.** Every typed model is declared once in
  [`../streamlined/models/`](../streamlined/models/README.md). The declaration is
  hand-checked against pipeline stage docs and the streamlined READ/WRITE
  blocks; the result is in
  [`../streamlined/models/README.md#audit-result`](../streamlined/models/README.md#audit-result).
  The mechanical check is [the declaration test](00-declaration-audit.md),
  `draft`. The declaration files are fenced `go` or `python`, so the check can
  parse the fields.

A test that needs a field the declaration does not carry is a missing contract,
not a test problem.

## Fixtures

- [`fixtures/`](fixtures/) holds coverage fixtures: representative programs, one
  or more per capability, and rejection fixtures that must be rejected.
- [`golden/`](golden/) holds golden records: one JSON file per pinned
  construction result.
- A fixture is a program plus its `program_sha256`, not a Parquet graph. The
  graph is derived in a temporary directory, so no derived table enters the
  repository and no cache is keyed.

Fixtures unlock parallel debugging: any pipeline stage can start from its typed
input fixture instead of running every earlier one. The end-to-end test still runs
the real chain.

## What a test doc contains

1. One happy-path test with **Given**, **When**, and **Then**.
2. The failure-mode tests.
3. A **TDD pin** naming what the test fixes before the code exists.

## Running

The Go module and the Python worker package exist. Run both suites from the
repository root:

```bash
cd generator && go test -count=1 ./...
uv run pytest -q
```

`go test -count=1` disables the Go test cache because tests read the policy files
in `generator/config/` by path. A pipeline stage is accepted only when its contract test and the
end-to-end test pass; both are Go tests.

`uv run pytest -q` discovers the two Python roots through `testpaths`: root
`tests/` for the repo tooling suites and `generator/python/tests/` for the
worker. Root policy data is checked where its loader lives, so `release-checks.yaml`,
`balance.yaml`, `tolerance.yaml`, and `prompts.yaml` are Go tests; the golden
records are a `03b` Go test.

## What this does not prove

- That the release is balanced. That is the check policy in
  [`../05-validate-and-export-release/release-checks.md`](../05-validate-and-export-release/release-checks.md).
- That a task is natural or well worded. That is the review gate.
- That a value is supported. That is the support-table observation in
  [`00-support-tables.md`](00-support-tables.md).
