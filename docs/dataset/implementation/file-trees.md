# Implementation file trees

**Status:** draft, 2026-11-20. This document owns where the replacement dataset
generator's code lives. Pipeline stage docs own what the code does;
[`python-and-golang.md`](python-and-golang.md) owns the language boundary;
[`../requirements/terminology.md`](../requirements/terminology.md) owns the
terms every code name spells out.

## Rules

1. **A folder exists only when the language needs one.** A Go package needs a
   folder; a Python module does not. A Python pipeline stage is one module until
   it needs a second file, then it becomes a folder with the same name.
2. **One folder per Go package, named after its pipeline stage doc stem.** No
   group folders: pipeline stage folders sit flat under `internal/`.
3. **A shared package is a folder only when two pipeline stages import it.** It
   spells the whole glossary term: `program-capability-census`, not `census`.
4. **A Python module for a pipeline stage keeps its pipeline stage number with
   an `s` prefix**, because a Python module name must be an identifier:
   `s01d_normalize_programs`.
5. New generator code never imports `dataset/`. `dataset/` never imports
   `cadqa_dataset_generator` or the Go module. See [Old generator](#old-generator).
6. Artifacts are written under a run directory given on the command line.
   `data/` and `runs/` are gitignored; no artifact is committed.

`internal/run/` is the orchestrator, not a pipeline stage package; it is the one
exception to rule 2. It owns the run lock, pipeline stage selection, and the exit
codes, and it calls the shared cache, manifest, and writer. A pipeline stage
package never imports it.

## Go module

Module path `github.com/MRiabov/CAD-QA/generator`. The module root is
`generator/`; the repository root is not a Go module. There is one binary, so
`main.go` sits at the module root rather than under `cmd/`.

```text
generator/
  go.mod
  go.sum
  main.go                                  package main
  internal/
    run/                                   package run
      run.go                               orchestrator, run directory allocation, pipeline stage selection, exit codes
      run_test.go
    shared/                                package shared
      dataset_artifact.go                  typed Parquet tables and identity
      parquet_writer.go                    async immutable Parquet part writer
      run_manifest.go                      RunRequest, RunManifest, run_id
      run_state.go                         run lock, pipeline stage marker, part scan
      cache_index.go                       content-addressed shared cache
      failure_record.go                    failure record row and partition merge
      balance_policy.go                    balance.yaml loader
      check_policy.go                      checks.yaml loader
      python_worker.go                     Python worker process bridge
    01a-read-cadevolve-metadata/           package read_cadevolve_metadata
      read_cadevolve_metadata.go
      read_cadevolve_metadata_test.go
    01b-select-program-pool/               package select_program_pool
      select_program_pool.go
      select_program_pool_test.go
    01c-fetch-program-pool/                package fetch_program_pool
      fetch_program_pool.go
      fetch_program_pool_test.go
    01e-write-external-dataset-manifest/   package write_external_dataset_manifest
      write_external_dataset_manifest.go
      write_external_dataset_manifest_test.go
    02c-build-cad-graph/                   package build_cad_graph
      build_cad_graph.go
      build_cad_graph_test.go
    program-capability-census/             package program_capability_census
      program_capability_census.go
      program_capability_census_test.go
    task-reasoning-step-support-table/     package task_reasoning_step_support_table
      task_reasoning_step_support_table.go
      task_reasoning_step_support_table_test.go
    03a-allocate-task-quotas/              package allocate_task_quotas
      allocate_task_quotas.go
      allocate_task_quotas_test.go
    03b-construct-task-definitions/        package construct_task_definitions
      construct_task_definitions.go
      construct_task_definitions_test.go
    03c-resolve-deficits/                  package resolve_deficits
      resolve_deficits.go
      resolve_deficits_test.go
    04-render-prompt-and-choices/          package render_prompt_and_choices
      render_prompt_and_choices.go
      render_prompt_and_choices_test.go
    05-validate-and-export-release/        package validate_and_export_release
      validate_and_export_release.go
      validate_and_export_release_test.go
    end-to-end/                            package end_to_end
      end_to_end_test.go
```

A pipeline stage package starts as one file and grows files in the same folder;
a new folder means a new package, not a new file. `shared/` is one package with
one file per concern, not one package per file. `program-capability-census/` and
`task-reasoning-step-support-table/` are separate packages because two pipeline
stages import each: `03a` and `03b` share the census, and `03a` and the witness
test share the support table.

`internal/run/` is the only orchestrator. A pipeline stage package does not own
the run lock, pipeline stage completion markers, or the shared cache. The run
directory layout and the part, flush, and resume rules are in
[`run-contract.md`](run-contract.md).

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
  parquet_writer.py                        async immutable Parquet part writer
  s01d_normalize_programs.py               01d normalize programs
  s02a_extract_cadquery_ast.py             02a extract CadQuery AST
  s02b_execute_cadquery.py                 02b execute CadQuery
```

Each pipeline stage is one module. When one needs a second file, it becomes a
folder with the same name and an `__init__.py` that re-exports its entry point:

```text
  s02b_execute_cadquery/
    __init__.py
    child_process.py
    shape_snapshots.py
    cad_topology_entities.py
    point_probes.py
```

The split above is illustrative, not required. The rule is the trigger, not the
file names.

## Tests

Go tests sit in their package folder. Python tests sit flat in `tests/`, like the
existing suite:

```text
tests/
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
| `balance.yaml`, `checks.yaml`, `prompts.yaml`, `tolerance.yaml` | Balance policy, check policy, prompt copy, and measurement tolerance policy. | The docs that define each. |
| `data/`, `runs/` | Run output: `runs/run<NNNN>/` and `runs/cache/`. Gitignored. | The run. |

Fixtures stay in the docs tree because they are reviewed like code and the test
contract owns their path. A test reads them by path; it does not copy them.

## Naming map

| Pipeline stage doc | Go folder and package | Python module | Test |
|---|---|---|---|
| `01a-read-cadevolve-metadata` | `01a-read-cadevolve-metadata`, `read_cadevolve_metadata` | — | `01a_read_cadevolve_metadata_test.go` |
| `01b-select-program-pool` | `01b-select-program-pool`, `select_program_pool` | — | `01b_select_program_pool_test.go` |
| `01c-fetch-program-pool` | `01c-fetch-program-pool`, `fetch_program_pool` | — | `01c_fetch_program_pool_test.go` |
| `01d-normalize-programs` | — | `s01d_normalize_programs.py` | `test_s01d_normalize_programs.py` |
| `01e-write-external-dataset-manifest` | `01e-write-external-dataset-manifest`, `write_external_dataset_manifest` | — | `01e_write_external_dataset_manifest_test.go` |
| `02a-extract-cadquery-ast` | — | `s02a_extract_cadquery_ast.py` | `test_s02a_extract_cadquery_ast.py` |
| `02b-execute-cadquery` | — | `s02b_execute_cadquery.py` | `test_s02b_execute_cadquery.py` |
| `02c-build-cad-graph` | `02c-build-cad-graph`, `build_cad_graph` | — | `02c_build_cad_graph_test.go` |
| `03a-allocate-task-quotas` | `03a-allocate-task-quotas`, `allocate_task_quotas` | — | `03a_allocate_task_quotas_test.go` |
| `03b-construct-task-definitions` | `03b-construct-task-definitions`, `construct_task_definitions` | — | `03b_construct_task_definitions_test.go` |
| `03c-resolve-deficits` | `03c-resolve-deficits`, `resolve_deficits` | — | `03c_resolve_deficits_test.go` |
| `04-render-prompt-and-choices` | `04-render-prompt-and-choices`, `render_prompt_and_choices` | — | `04_render_prompt_and_choices_test.go` |
| `05-validate-and-export-release` | `05-validate-and-export-release`, `validate_and_export_release` | — | `05_validate_and_export_release_test.go` |

The run contract is cross-cutting; its Go package is `internal/run`, and its
test contract is
[`pipeline/testing/00-run-contract.md`](pipeline/testing/00-run-contract.md).

## Bootstrap order

1. `go.mod`, `main.go`, `internal/run/`, and `internal/shared/`, including
   `run_manifest.go`, `run_state.go`, `cache_index.go`, and
   `parquet_writer.go`.
2. `01a`, `01b`, `01c`, `s01d_normalize_programs.py`, `01e`.
3. `s02a_extract_cadquery_ast.py`, `s02b_execute_cadquery.py`, `02c`.
4. `program-capability-census/`, `03b`, `task-reasoning-step-support-table/`,
   because the support table is what `03a` reads.
5. `03a`, `03c`, `04`, `05`, `end-to-end`.

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
