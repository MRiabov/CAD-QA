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
| Parquet read and write | The pinned external benchmark program set, once `MC-49` lands. |
| The code of every pipeline stage | — |
| The CAD graph and the release table | — |

A unit test on an internal function is not a substitute. If a pipeline stage can
only be tested by mocking its own storage, the storage contract is wrong.

## Assert from the artifact

Every test reads its result back the way the next stage reads it: the Parquet
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

## One doc per stage

The group docs (`01`, `02`, `03`) are overviews. Tests pin the sub-stages, which
are the executable units.

| Test doc | Pipeline stage contract |
|---|---|
| [`00-end-to-end.md`](00-end-to-end.md) | [`../00-end-to-end.md`](../00-end-to-end.md) |
| [`00-support-tables.md`](00-support-tables.md) | cross-cutting; [`../../task-step-support.md`](../../task-step-support.md) |
| [`01a-read-cadevolve-metadata.md`](01a-read-cadevolve-metadata.md) | [`../01a-read-cadevolve-metadata.md`](../01a-read-cadevolve-metadata.md) |
| [`01b-select-program-pool.md`](01b-select-program-pool.md) | [`../01b-select-program-pool.md`](../01b-select-program-pool.md) |
| [`01c-fetch-program-pool.md`](01c-fetch-program-pool.md) | [`../01c-fetch-program-pool.md`](../01c-fetch-program-pool.md) |
| `01d-normalize-programs.md` | [`../01d-normalize-programs.md`](../01d-normalize-programs.md) |
| `01e-write-external-dataset-manifest.md` | [`../01e-write-external-dataset-manifest.md`](../01e-write-external-dataset-manifest.md) |
| `02a-extract-cadquery-ast.md` | [`../02a-extract-cadquery-ast.md`](../02a-extract-cadquery-ast.md) |
| [`02b-execute-cadquery.md`](02b-execute-cadquery.md) | [`../02b-execute-cadquery.md`](../02b-execute-cadquery.md) |
| [`02c-build-cad-graph.md`](02c-build-cad-graph.md) | [`../02c-build-cad-graph.md`](../02c-build-cad-graph.md) |
| `03a-allocate-task-quotas.md` | [`../03-task-generation/03a-allocate-task-quotas.md`](../03-task-generation/03a-allocate-task-quotas.md) |
| [`03b-construct-task-definitions.md`](03b-construct-task-definitions.md) | [`../03-task-generation/03b-construct-task-definitions.md`](../03-task-generation/03b-construct-task-definitions.md) |
| `03c-resolve-deficits.md` | [`../03-task-generation/03c-resolve-deficits.md`](../03-task-generation/03c-resolve-deficits.md) |
| `04-render-prompt-and-choices.md` | [`../04-render-prompt-and-choices.md`](../04-render-prompt-and-choices.md) |
| `05-validate-and-export-release.md` | [`../05-validate-and-export-release.md`](../05-validate-and-export-release.md) |

A name in backticks is a test doc that is not written yet. That is a missing
test, not a pipeline stage without tests.

`00-support-tables.md` is the one cross-cutting test: the support tables are an
observation over the fixture set, not a pipeline stage output.

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

No harness exists yet: there is no Go module and no test runner. The first
pipeline stage implementation brings one. Until then a test doc is a contract,
and no pipeline stage is accepted without a passing test.

## What this does not prove

- That the release is balanced. That is the check policy in
  [`../05-validate-and-export-release/release-checks.md`](../05-validate-and-export-release/release-checks.md).
- That a task is natural or well worded. That is the review gate.
- That a value is supported. That is the support-table observation in
  [`00-support-tables.md`](00-support-tables.md).
