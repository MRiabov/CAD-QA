# Pipeline test contracts

One test contract per pipeline stage, named with the file stem of the doc it
tests. Contract text stays in its pipeline stage doc; the test doc says what the
test does and what it must not accept.

The shared rules — the integration level, what is real and what is mocked, the
assert-from-the-artifact rule, and the test-first order — are in
[`00-testing-strategy.md`](00-testing-strategy.md).

## Mirror rule

This folder mirrors the authoritative `../` folder structure exactly, and
mirrors [`../streamlined/`](../streamlined/) one-for-one. A pipeline stage that
is a folder there is a folder here, and its lettered sub-documents have the same
names:

```text
pipeline/03-task-generation/03a-allocate-task-quotas/README.md
pipeline/03-task-generation/03a-allocate-task-quotas/a-support-derivation.md
testing/03-task-generation/03a-allocate-task-quotas/README.md
testing/03-task-generation/03a-allocate-task-quotas/a-support-derivation.md
```

`tools/ci_cd/check-doc-mirror` enforces the rule for both `testing/` and
`streamlined/`. `decisions.md`, `algorithm/`, and `extraction/` are excluded:
they own rationale and field mechanics, not a pipeline stage contract. `fixtures/`,
`golden/`, and `oracles/` are additions; the test docs own their paths.

## Contracts

| Test doc | Pipeline stage | Status |
|---|---|---|
| [`00-testing-strategy.md`](00-testing-strategy.md) | The shared rules and the inventory. | draft |
| [`00-end-to-end.md`](00-end-to-end.md) | The whole chain, `01a` to `05`. | draft |
| [`00-run-contract.md`](00-run-contract.md) | The run manifest, Parquet parts, resume, cache, and exit codes, a cross-cutting contract. | draft |
| [`00-support-tables.md`](00-support-tables.md) | The support tables, a cross-cutting observation. | draft |
| [Typed model declarations](00-declaration-audit.md) | The typed model index, field resolution, and pipeline stage boundary audit. | draft |
| [`01a-read-cadevolve-metadata.md`](01a-read-cadevolve-metadata.md) | `01a` read CADEvolve metadata. | draft |
| [`01b-select-program-pool.md`](01b-select-program-pool.md) | `01b` select program pool. | draft |
| [`01c-fetch-program-pool.md`](01c-fetch-program-pool.md) | `01c` fetch program pool. | draft |
| [`01d-normalize-programs.md`](01d-normalize-programs.md) | `01d` normalize programs. | draft |
| [`01e-write-external-dataset-manifest.md`](01e-write-external-dataset-manifest.md) | `01e` write external dataset manifest. | draft |
| [`02a-extract-cadquery-ast.md`](02a-extract-cadquery-ast.md) | `02a` extract CadQuery AST. | draft |
| [`02b-execute-cadquery.md`](02b-execute-cadquery.md) | `02b` execute CadQuery. | draft |
| [`02c-build-cad-graph.md`](02c-build-cad-graph.md) | `02c` build CAD graph. | draft |
| [`03-task-generation/03a-allocate-task-quotas/README.md`](03-task-generation/03a-allocate-task-quotas/README.md) | `03a` allocate task quotas. | draft |
| [`03-task-generation/03b-construct-task-definitions/README.md`](03-task-generation/03b-construct-task-definitions/README.md) | `03b` construct task definitions. | draft |
| [`03-task-generation/03c-resolve-deficits.md`](03-task-generation/03c-resolve-deficits.md) | `03c` resolve deficits. | draft |
| [`04-render-prompt-and-choices.md`](04-render-prompt-and-choices.md) | `04` render prompt and choices. | draft |
| [`05-validate-and-export-release.md`](05-validate-and-export-release.md) | `05` validate and export release. | draft |

`draft` means the contract is written and no test enforces it yet. It becomes
`enforced` when a test in the repository pins it. The group docs (`01`, `02`,
`03`) are overviews; the tests pin the sub-steps.

## Typed model declarations

The typed models every test asserts are declared once in
[`../streamlined/models/`](../streamlined/models/README.md). A test that reads a
field the declaration does not carry is a missing contract, not a test detail.

The declarations are hand-checked against pipeline stage docs today. The
[`00-testing-strategy.md`](00-testing-strategy.md#typed-model-and-structure-checks)
section records what is automated and what is not.

## Fixtures and records

| Path | Holds |
|---|---|
| [`fixtures/`](fixtures/) | Coverage fixtures and rejection fixtures: programs plus their `program_sha256`. |
| [`golden/`](golden/) | Golden records: the record format and one pinned construction result. |
| [`oracles/`](oracles/) | Oracles: pinned pipeline stage outputs, one directory per oracle kind. |
