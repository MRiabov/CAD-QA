# Implementation file trees

**Status:** draft, 2026-11-20. This document owns where the replacement
generator's code lives. Pipeline stage docs own what the code does;
[`python-and-golang.md`](python-and-golang.md) owns the language boundary.

## Rules

1. One folder per sub-step, named after its pipeline stage doc stem. A group
   (`01`, `02`, `03`) is a parent folder; its sub-steps fan out inside it.
2. The language of a folder is the language
   [`python-and-golang.md`](python-and-golang.md) assigns to that sub-step.
3. A Go folder keeps the stem exactly. A Python folder drops the numeric prefix,
   because a Python module name must be an identifier; the module docstring names
   its pipeline stage, and the map below is the binding.
4. New generator code never imports `dataset/`. `dataset/` never imports
   `cadqa_gen/` or the Go module. See [Old generator](#old-generator).
5. Tests sit with the code: a `_test.go` file in the Go folder, a
   `tests/cadqa_gen/` file for Python.
6. Artifacts are written under a run directory given on the command line.
   `data/` and `runs/` are gitignored; no artifact is committed.

## Go module

Module path `github.com/MRiabov/CAD-QA/generator`. The module root is
`generator/`; the repository root is not a Go module.

```text
generator/
  go.mod
  go.sum
  cmd/
    cadqa-gen/
      main.go                              the only entry point
  internal/
    shared/
      artifact/                            typed Parquet tables, identity, atomic write
      failure/                             failure row and partition merge
      policy/                              balance.yaml and checks.yaml loaders
      worker/                              Python worker process bridge
    01-external-dataset-etl/               group folder
      01a-read-cadevolve-metadata/         package metadata
        01a_read_cadevolve_metadata_test.go
      01b-select-program-pool/             package selection
        01b_select_program_pool_test.go
      01c-fetch-program-pool/              package fetch
        01c_fetch_program_pool_test.go
      01e-write-external-dataset-manifest/ package manifest
        01e_write_external_dataset_manifest_test.go
    02-execute-cadquery-and-build-graph/   group folder
      02c-build-cad-graph/                 package graph
        02c_build_cad_graph_test.go
    03-task-generation/                    group folder
      census/                              program capability census, shared by 03a and 03b
        census_test.go
      support/                             support-table derivation, called by 03a and the witness test
        support_test.go
      03a-allocate-task-quotas/            package quotas
        03a_allocate_task_quotas_test.go
      03b-construct-task-definitions/      package construction
        03b_construct_task_definitions_test.go
      03c-resolve-deficits/                package deficits
        03c_resolve_deficits_test.go
    04-render-prompt-and-choices/          package render
      04_render_prompt_and_choices_test.go
    05-validate-and-export-release/        package release
      05_validate_and_export_release_test.go
    e2e/                                   package e2e
      pipeline_test.go
```

A group folder holds only the sub-step folders and a doc comment; it is not a
package of its own. `census/` and `support/` are the two shared packages inside a
group. Neither is a pipeline stage: the census is one function of a graph, and
the support tables are an observation over the fixture set.

## Python worker

Package `cadqa_gen/` at the repository root, imported with
`pythonpath = ["."]` and listed in
`[tool.hatch.build.targets.wheel] packages`. It is a worker, not an
orchestrator: the Go entry point starts it as a child process and passes typed
Parquet paths and a small JSON request.

```text
cadqa_gen/
  __init__.py
  cli.py                                   worker entry point, one subcommand per stage
  normalize_programs/                      01d normalize programs
    __init__.py
    canonical.py                           ast.unparse, ruff format, hashes
  extract_cadquery_ast/                    02a extract CadQuery AST
    __init__.py
    passes.py                              the pass order
    expressions.py
  execute_cadquery/                        02b execute CadQuery
    __init__.py
    runner.py                              child process, limits, cache key
    snapshots.py
    entities.py
    probes.py
```

## Tests

```text
tests/
  cadqa_gen/
    test_01d_normalize_programs.py
    test_02a_extract_cadquery_ast.py
    test_02b_execute_cadquery.py
```

A Go test function is the contract name in CamelCase:
`test_01a_metadata_happy_path_adversarial` becomes
`Test01aMetadataHappyPathAdversarial`.

## Fixtures and config

| Path | Holds | Owner |
|---|---|---|
| `docs/dataset/implementation/pipeline/testing/fixtures/` | Coverage and rejection programs with `program_sha256`. | The test contract. |
| `docs/dataset/implementation/pipeline/testing/golden/` | Golden records. | The record format. |
| `balance.yaml`, `checks.yaml`, `prompts.yaml` | Release policy, check policy, prompt copy. | The docs that define each. |
| `data/`, `runs/` | Run output. Gitignored. | The run. |

Fixtures stay in the docs tree because they are reviewed like code and the test
contract owns their path. A test reads them by path; it does not copy them.

## Naming map

| Pipeline stage doc | Go folder | Python module | Test |
|---|---|---|---|
| `01a-read-cadevolve-metadata` | `01a-read-cadevolve-metadata` | — | `01a_read_cadevolve_metadata_test.go` |
| `01b-select-program-pool` | `01b-select-program-pool` | — | `01b_select_program_pool_test.go` |
| `01c-fetch-program-pool` | `01c-fetch-program-pool` | — | `01c_fetch_program_pool_test.go` |
| `01d-normalize-programs` | — | `normalize_programs/` | `test_01d_normalize_programs.py` |
| `01e-write-external-dataset-manifest` | `01e-write-external-dataset-manifest` | — | `01e_write_external_dataset_manifest_test.go` |
| `02a-extract-cadquery-ast` | — | `extract_cadquery_ast/` | `test_02a_extract_cadquery_ast.py` |
| `02b-execute-cadquery` | — | `execute_cadquery/` | `test_02b_execute_cadquery.py` |
| `02c-build-cad-graph` | `02c-build-cad-graph` | — | `02c_build_cad_graph_test.go` |
| `03a-allocate-task-quotas` | `03a-allocate-task-quotas` | — | `03a_allocate_task_quotas_test.go` |
| `03b-construct-task-definitions` | `03b-construct-task-definitions` | — | `03b_construct_task_definitions_test.go` |
| `03c-resolve-deficits` | `03c-resolve-deficits` | — | `03c_resolve_deficits_test.go` |
| `04-render-prompt-and-choices` | `04-render-prompt-and-choices` | — | `04_render_prompt_and_choices_test.go` |
| `05-validate-and-export-release` | `05-validate-and-export-release` | — | `05_validate_and_export_release_test.go` |

## Bootstrap order

The tree is created in dependency order, so every folder has a test before its
implementation:

1. `generator/go.mod`, `cmd/cadqa-gen/`, `shared/artifact/`, `shared/failure/`,
   `shared/policy/`, `shared/worker/`.
2. `01a`, `01b`, `01c`, the Python worker's `cli.py` plus `normalize_programs/`
   (`01d`), then `01e`.
3. `02a`, `02b`, then `02c`.
4. `03-task-generation/census/`, `03b`, and `03-task-generation/support/`,
   because the support tables are what `03a` reads.
5. `03a`, `03c`, `04`, `05`, `e2e`.

## Old generator

`dataset/` is the pre-rebuild generator. It is kept for now, and the tag
`before-throwing-out-the-existing-dataset-generator` preserves it in history.

It cannot be deleted yet: `train_and_eval/` imports `dataset.cli`, `dataset.io`,
`dataset.release.*`, `dataset.query.*`, `dataset.ontology.*`, and
`dataset.source`; two scripts under `tools/` import a subset of them; and
`tests/test_graph_first_pipeline.py` imports `dataset.harbor` and
`dataset.prompts.*` as well. Deleting the package breaks the training and
evaluation harness before the replacement can produce a release.

The package is deleted when all of these hold:

- the replacement writes a release with `05`;
- `train_and_eval/` imports no `dataset.*` module;
- `tools/analyze_release_gate_feasibility.py` and
  `tools/verify_cadevolve_parquet_parity.py` are migrated or removed.

Until then, `dataset/` is not extended: no new feature work, only fixes that keep
the existing release reproducible.
