# Pipeline test contracts

One test contract per pipeline stage, named with the file stem of the doc it
tests. Contract text stays in its pipeline stage doc; the test doc says what the
test does and what it must not accept.

The shared rules — the integration level, what is real and what is mocked, the
assert-from-the-artifact rule, and the test-first order — are in
[`00-testing-strategy.md`](00-testing-strategy.md).

## Contracts

| Test doc | Pipeline stage | Status |
|---|---|---|
| [`00-testing-strategy.md`](00-testing-strategy.md) | The shared rules and the inventory. | draft |
| [`00-end-to-end.md`](00-end-to-end.md) | The whole chain, `01a` to `05`. | draft |
| [`00-support-tables.md`](00-support-tables.md) | The support tables, a cross-cutting observation. | draft |
| [`01a-read-cadevolve-metadata.md`](01a-read-cadevolve-metadata.md) | `01a` read CADEvolve metadata. | draft |
| [`01b-select-program-pool.md`](01b-select-program-pool.md) | `01b` select program pool. | draft |
| [`01c-fetch-program-pool.md`](01c-fetch-program-pool.md) | `01c` fetch program pool. | draft |
| [`01d-normalize-programs.md`](01d-normalize-programs.md) | `01d` normalize programs. | draft |
| [`01e-write-external-dataset-manifest.md`](01e-write-external-dataset-manifest.md) | `01e` write external dataset manifest. | draft |
| [`02a-extract-cadquery-ast.md`](02a-extract-cadquery-ast.md) | `02a` extract CadQuery AST. | draft |
| [`02b-execute-cadquery.md`](02b-execute-cadquery.md) | `02b` execute CadQuery. | draft |
| [`02c-build-cad-graph.md`](02c-build-cad-graph.md) | `02c` build CAD graph. | draft |
| [`03a-allocate-task-quotas.md`](03a-allocate-task-quotas.md) | `03a` allocate task quotas. | draft |
| [`03b-construct-task-definitions.md`](03b-construct-task-definitions.md) | `03b` construct task definitions. | draft |
| [`03c-resolve-deficits.md`](03c-resolve-deficits.md) | `03c` resolve deficits. | draft |
| [`04-render-prompt-and-choices.md`](04-render-prompt-and-choices.md) | `04` render prompt and choices. | draft |
| [`05-validate-and-export-release.md`](05-validate-and-export-release.md) | `05` validate and export release. | draft |

A name in backticks is a test doc that is not written yet. That is a missing
test, not a pipeline stage without tests. The group docs (`01`, `02`, `03`) are
overviews; the tests pin the sub-stages.

## Fixtures and records

| Path | Holds |
|---|---|
| [`fixtures/`](fixtures/) | Coverage fixtures and rejection fixtures: programs plus their `program_sha256`. |
| [`golden/`](golden/) | Golden records: the record format and one pinned construction result. |
