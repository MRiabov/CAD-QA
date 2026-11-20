# Implementation file trees

**Status:** draft, 2026-11-20. This document owns where the replacement dataset
generator's code lives. Pipeline stage docs own what the code does;
[`python-and-golang.md`](python-and-golang.md) owns the language boundary;
[`../requirements/terminology.md`](../requirements/terminology.md) owns the
terms every code name spells out.

## Rules

1. One folder per sub-step, named after its pipeline stage doc stem. A group
   (`01`, `02`, `03`) is a parent folder; its sub-steps fan out inside it.
2. The language of a folder is the language
   [`python-and-golang.md`](python-and-golang.md) assigns to that sub-step.
3. A Go folder keeps the stem exactly, and its package name is its pipeline stage
   title in snake case without the number: `03a-allocate-task-quotas` holds
   `package allocate_task_quotas`.
4. A Python folder keeps its pipeline stage number with an `s` prefix, because a
   Python module name must be an identifier: `s01d_normalize_programs`. The
   naming map below is the binding.
5. A shared package spells the whole glossary term: `program_capability_census`,
   not `census`; `failure_record`, not `failure`.
6. New generator code never imports `dataset/`. `dataset/` never imports
   `cadqa_dataset_generator/` or the Go module. See [Old generator](#old-generator).
7. Tests sit with the code: a `_test.go` file in the Go folder, a
   `tests/cadqa_dataset_generator/` file for Python.
8. Artifacts are written under a run directory given on the command line.
   `data/` and `runs/` are gitignored; no artifact is committed.

## Go module

Module path `github.com/MRiabov/CAD-QA/generator`. The module root is
`generator/`; the repository root is not a Go module.

```text
generator/
  go.mod
  go.sum
  cmd/
    cadqa-dataset-generator/
      main.go                              the only entry point
  internal/
    shared/
      dataset_artifact/                    typed Parquet tables, identity, atomic write
      failure_record/                      failure record row and partition merge
      balance_policy/                      balance.yaml loader
      check_policy/                        checks.yaml loader
      python_worker/                       Python worker process bridge
    01-external-dataset-etl/               group folder
      01a-read-cadevolve-metadata/         package read_cadevolve_metadata
        01a_read_cadevolve_metadata_test.go
      01b-select-program-pool/             package select_program_pool
        01b_select_program_pool_test.go
      01c-fetch-program-pool/              package fetch_program_pool
        01c_fetch_program_pool_test.go
      01e-write-external-dataset-manifest/ package write_external_dataset_manifest
        01e_write_external_dataset_manifest_test.go
    02-execute-cadquery-and-build-graph/   group folder
      02c-build-cad-graph/                 package build_cad_graph
        02c_build_cad_graph_test.go
    03-task-generation/                    group folder
      program_capability_census/           package program_capability_census
        program_capability_census_test.go
      task_reasoning_step_support_table/   package task_reasoning_step_support_table
        task_reasoning_step_support_table_test.go
      03a-allocate-task-quotas/            package allocate_task_quotas
        03a_allocate_task_quotas_test.go
      03b-construct-task-definitions/      package construct_task_definitions
        03b_construct_task_definitions_test.go
      03c-resolve-deficits/                package resolve_deficits
        03c_resolve_deficits_test.go
    04-render-prompt-and-choices/          package render_prompt_and_choices
      04_render_prompt_and_choices_test.go
    05-validate-and-export-release/        package validate_and_export_release
      05_validate_and_export_release_test.go
    end_to_end/                            package end_to_end
      end_to_end_test.go
```

A group folder holds only the sub-step folders and a doc comment; it is not a
package of its own. `program_capability_census/` and
`task_reasoning_step_support_table/` are the two shared packages inside a group.
Neither is a pipeline stage: the program capability census is one function of a
CAD graph, and the task reasoning step support table is an observation over the
fixture set.

## Python worker

Package `cadqa_dataset_generator/` at the repository root, imported with
`pythonpath = ["."]` and listed in
`[tool.hatch.build.targets.wheel] packages`. It is a worker, not an
orchestrator: the Go entry point starts it as a child process and passes typed
Parquet paths and a small JSON request.

```text
cadqa_dataset_generator/
  __init__.py
  cli.py                                   worker entry point, one subcommand per stage
  s01d_normalize_programs/                 01d normalize programs
    __init__.py
    canonical_text.py                      ast.unparse, ruff format, hashes
  s02a_extract_cadquery_ast/               02a extract CadQuery AST
    __init__.py
    pass_order.py                          the pass order
    ast_expression_tree.py
  s02b_execute_cadquery/                   02b execute CadQuery
    __init__.py
    child_process.py                       limits, timeout, cache key
    shape_snapshots.py
    cad_topology_entities.py
    point_probes.py
```

## Tests

```text
tests/
  cadqa_dataset_generator/
    test_s01d_normalize_programs.py
    test_s02a_extract_cadquery_ast.py
    test_s02b_execute_cadquery.py
```

A Go test function is the contract name in CamelCase:
`test_01a_metadata_happy_path_adversarial` becomes
`Test01aMetadataHappyPathAdversarial`.

## Fixtures and config

| Path | Holds | Owner |
|---|---|---|
| `docs/dataset/implementation/pipeline/testing/fixtures/` | Coverage and rejection programs with `program_sha256`. | The test contract. |
| `docs/dataset/implementation/pipeline/testing/golden/` | Golden records. | The record format. |
| `balance.yaml`, `checks.yaml`, `prompts.yaml` | Balance policy, check policy, prompt copy. | The docs that define each. |
| `data/`, `runs/` | Run output. Gitignored. | The run. |

Fixtures stay in the docs tree because they are reviewed like code and the test
contract owns their path. A test reads them by path; it does not copy them.

## Naming map

| Pipeline stage doc | Go folder and package | Python folder | Test |
|---|---|---|---|
| `01a-read-cadevolve-metadata` | `01a-read-cadevolve-metadata`, `read_cadevolve_metadata` | — | `01a_read_cadevolve_metadata_test.go` |
| `01b-select-program-pool` | `01b-select-program-pool`, `select_program_pool` | — | `01b_select_program_pool_test.go` |
| `01c-fetch-program-pool` | `01c-fetch-program-pool`, `fetch_program_pool` | — | `01c_fetch_program_pool_test.go` |
| `01d-normalize-programs` | — | `s01d_normalize_programs/` | `test_s01d_normalize_programs.py` |
| `01e-write-external-dataset-manifest` | `01e-write-external-dataset-manifest`, `write_external_dataset_manifest` | — | `01e_write_external_dataset_manifest_test.go` |
| `02a-extract-cadquery-ast` | — | `s02a_extract_cadquery_ast/` | `test_s02a_extract_cadquery_ast.py` |
| `02b-execute-cadquery` | — | `s02b_execute_cadquery/` | `test_s02b_execute_cadquery.py` |
| `02c-build-cad-graph` | `02c-build-cad-graph`, `build_cad_graph` | — | `02c_build_cad_graph_test.go` |
| `03a-allocate-task-quotas` | `03a-allocate-task-quotas`, `allocate_task_quotas` | — | `03a_allocate_task_quotas_test.go` |
| `03b-construct-task-definitions` | `03b-construct-task-definitions`, `construct_task_definitions` | — | `03b_construct_task_definitions_test.go` |
| `03c-resolve-deficits` | `03c-resolve-deficits`, `resolve_deficits` | — | `03c_resolve_deficits_test.go` |
| `04-render-prompt-and-choices` | `04-render-prompt-and-choices`, `render_prompt_and_choices` | — | `04_render_prompt_and_choices_test.go` |
| `05-validate-and-export-release` | `05-validate-and-export-release`, `validate_and_export_release` | — | `05_validate_and_export_release_test.go` |

## Bootstrap order

The tree is created in dependency order, so every folder has a test before its
implementation:

1. `generator/go.mod`, `cmd/cadqa-dataset-generator/`, `shared/dataset_artifact/`,
   `shared/failure_record/`, `shared/balance_policy/`, `shared/check_policy/`,
   `shared/python_worker/`.
2. `01a`, `01b`, `01c`, the Python worker's `cli.py` plus
   `s01d_normalize_programs/` (`01d`), then `01e`.
3. `02a`, `02b`, then `02c`.
4. `program_capability_census/`, `03b`, and
   `task_reasoning_step_support_table/`, because the support table is what `03a`
   reads.
5. `03a`, `03c`, `04`, `05`, `end_to_end`.

## Old generator

`dataset/` is the pre-rebuild generator. It is kept for now, and the tag
`before-throwing-out-the-existing-dataset-generator` preserves it in history.

It cannot be deleted yet: `train_and_eval/` imports `dataset.cli`, `dataset.io`,
`dataset.release.*`, `dataset.query.*`, `dataset.ontology.*`, and
`dataset.source`; two scripts under `tools/` import a subset of them; and
`tests/test_graph_first_pipeline.py` imports `dataset.harbor` and
`dataset.prompts.*` as well. Deleting the package breaks the training and
evaluation harness before the replacement can produce a dataset release.

The package is deleted when all of these hold:

- the replacement writes a dataset release with `05`;
- `train_and_eval/` imports no `dataset.*` module;
- `tools/analyze_release_gate_feasibility.py` and
  `tools/verify_cadevolve_parquet_parity.py` are migrated or removed.

Until then, `dataset/` is not extended: no new feature work, only fixes that keep
the existing dataset release reproducible.
