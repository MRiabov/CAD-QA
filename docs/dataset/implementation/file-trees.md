# Implementation file trees

**Status:** draft, 2026-11-23. Reconciled with the 2026-11-21 run contract, the
2026-11-21 architecture audit, and the review-pack plan. This document owns
where the replacement dataset generator's code, tests, fixtures, and
owner-facing tools live. Pipeline stage docs own what the code does;
[`python-and-golang.md`](python-and-golang.md) owns the language boundary;
[`../requirements/terminology.md`](../requirements/terminology.md) owns the
terms every code name spells out.

## Scope

This document covers the dataset generator and the tools a person runs against
its output. It does not cover the training and evaluation stack
([`../../train-and-eval/`](../../train-and-eval/)), the evaluation harness and
grader, or repository CI tools
([`../../general-architecture/ci-cd.md`](../../general-architecture/ci-cd.md)).
Those are separate trees with separate owners.

## Rules

1. **A folder exists only when the language needs one.** A Go package needs a
   folder; a Python module does not. A Python pipeline stage is one module until
   it needs a second file, then it becomes a folder with the same name.
2. **One folder per Go package, named after its pipeline stage doc stem.** A
   pipeline stage package sits under `internal/stages/`. A pipeline stage with
   several Go sub-steps gets a group folder named after its pipeline stage doc
   stem; the group keeps `internal/stages/` within the fanout limit.
3. **A shared package is a folder only when two pipeline stages import it.** It
   spells the whole glossary term: `program-capability-census`, not `census`.
4. **A Python module for a pipeline stage keeps its pipeline stage number with
   an `s` prefix**, because a Python module name must be an identifier:
   `s01d_normalize_programs`.
5. The pre-rebuild generator and harness are deleted; see
   [Deleted generator](#deleted-generator). New code does not resurrect their
   modules.
6. Artifacts are written under a run directory given on the command line.
   `data/` and `runs/` are gitignored; no artifact is committed.
7. **Cross-pipeline-stage typed models live in `internal/iocontracts/`**, a
   sibling of `internal/shared/`, not a subpackage of it. A pipeline stage
   package may import `iocontracts` and `shared`; it never imports another
   pipeline stage package to obtain a typed model. Control records that flow backwards
   (`ProgramReassignmentRequest`, `ProgramRequest`, `AcceptedMiss`) live there
   too.
8. **A pipeline stage with sub-documents gets at least one Go file per
   sub-document**, named after the sub-document stem. A file that reaches the
   800-line warning splits by responsibility; the split files keep the
   sub-document prefix or a responsibility name. The doc-to-file map is a
   minimum, not a ceiling.
9. **A tracked directory has at most 10 immediate subdirectories.** The
   repository root has at most 15. An explicit exception names a path, a limit
   above 10 and at most 15, and a reason. Only subdirectories that contain a
   tracked file count; files do not. The check is
   `tools/ci_cd/check_fanout.py`.

There is no code `pipeline/` folder. `docs/dataset/implementation/pipeline/` is
the contract tree; Go pipeline stage packages sit under
`generator/internal/stages/`. A pipeline stage with several Go sub-steps gets a
group folder named after its pipeline stage doc stem
(`01-external-dataset-etl/`, `03-task-generation/`); a pipeline stage with one
Go sub-step is the package itself (`02c-build-cad-graph/`,
`04-render-prompt-and-choices/`, `05-validate-and-export-release/`). A
`generator/internal/pipeline/` folder is not part of this layout.

## File length

A file stays under 800 lines. A file over 800 lines is a warning: split it by
responsibility. A file over 1,200 lines fails the `file-length` pre-commit hook.
The hook scans `.go`, `.md`, `.py`, `.yaml`, and `.yml` files across the
repository and counts physical lines; caches, `data/`, `runs/`, `dist/`,
`_archive/`, `.agents/`, and worktrees are skipped. Run it directly with
`tools/ci_cd/file-length`.

`tools/ci_cd/check_file_length.py` holds the exemption list. An entry names a
path or glob and a written reason, and it is for generated code only; a file
that grew past the ceiling is split, not exempted.

`internal/run/` is the orchestrator, not a pipeline stage package. It owns the
run lock, pipeline stage selection, the command-line interface, and the exit
codes, and it calls the shared cache, manifest, and writer. A pipeline stage
package never imports it. The orchestrator is already several concerns in one
command, so the package starts with the files below rather than one growing
`run.go`.

## Directory fanout

A tracked directory has at most 10 immediate subdirectories. The repository
root has at most 15. An explicit exception names a path, a limit above 10 and
at most 15, and a reason; the exception list is in
`tools/ci_cd/check_fanout.py`. Files do not count: the fanout is the number of
immediate subdirectories that contain at least one tracked file.

The check is `tools/ci_cd/check_fanout.py`, wired into the `fanout`
pre-commit hook and the `quality-and-plan` CI job. The planned tree below
fits: `internal/` has five children, `internal/stages/` has five, and
`internal/stages/03-task-generation/` has five. The repository root currently
has 11 tracked children, within its 15 limit.

## Go module

Module path `github.com/MRiabov/CAD-QA/generator`. The module root is
`generator/`; the repository root is not a Go module. There is one binary, so
`main.go` sits at the module root rather than under `cmd/`. The Python worker
lives under `generator/python/`; `go test ./...` ignores it because it contains
no Go packages.

```text
generator/
  go.mod
  go.sum
  main.go                                  package main
  config/                                  generator inputs, read by path
    balance.yaml
    release-checks.yaml
    tolerance.yaml
    prompts.yaml
  internal/
    iocontracts/                           package iocontracts
      program.go                           ProgramMetadata, SelectionPolicy, ProgramSelection, ProgramPool, NormalizedProgram, ExternalDatasetManifest
      extraction.go                        CadQuery AST and runtime result models, FailureTombstone
      graph.go                             CadGraph, GraphCompletenessReport, graph entity, relation, and measurement models
      task.go                              TaskQuotaPlan, QuotaTarget, ProgramCapabilityCensus, TaskDefinition, DeficitLedger, control records
      release.go                           RenderConfig, PromptTemplateSet, ReleaseTable, ReleaseRow, ReleaseArtifacts, ReleaseManifest, CheckReport, SupportTable
      cross_cutting.go                     FailureRecord, RunManifest, StageCompletionMarker, TolerancePolicy, shared enums
      iocontracts_test.go
    run/                                   package run
      run.go                               orchestrator entry, pipeline stage selection, exit codes
      cli.go                               `run`, `status`, and `list` flag parsing
      resume.go                            resume, force, part scan, stale-part removal
      status.go                            `status` command
      list.go                              `list` command
      lock.go                              run lock and allocation lock
      cache.go                             shared cache lookup and write
      run_test.go
      resume_test.go
      status_test.go
      list_test.go
      lock_test.go
      cache_test.go
    shared/                                package shared
      dataset_artifact.go                  typed Parquet tables and identity
      parquet_writer.go                    async immutable Parquet part writer
      run_manifest.go                      RunRequest, RunManifest, run_id
      run_state.go                         run lock, pipeline stage marker, part scan
      cache_index.go                       content-addressed shared cache
      failure_record.go                    failure record row and partition merge
      balance_policy.go                    balance.yaml loader
      check_policy.go                      release-checks.yaml loader
      tolerance_policy.go                  tolerance.yaml loader and validation
      prompt_templates.go                  prompts.yaml loader and validation for 04
      selection_policy.go                  selection policy file loader
      python_worker.go                     Python worker process bridge
      generate.go                          go:generate for the worker contract structs
      s01d_normalize_programs_contract.go  generated 01d request and result structs
    stages/                                Go pipeline stage packages
      01-external-dataset-etl/
        01a-read-cadevolve-metadata/       package read_cadevolve_metadata
          read_cadevolve_metadata.go
          read_cadevolve_metadata_test.go
        01b-select-program-pool/           package select_program_pool
          select_program_pool.go
          select_program_pool_test.go
        01c-fetch-program-pool/            package fetch_program_pool
          fetch_program_pool.go
          fetch_program_pool_test.go
        01e-write-external-dataset-manifest/  package write_external_dataset_manifest
          write_external_dataset_manifest.go
          write_external_dataset_manifest_test.go
      02c-build-cad-graph/                 package build_cad_graph
        build_cad_graph.go                 entry point
        graph_construction.go              a-construction.md
        graph_persistence.go               graph-persistence.md
        graph_completeness.go              graph-completeness.md
        build_cad_graph_test.go
      03-task-generation/
        program-capability-census/         package program_capability_census
          program_capability_census.go
          program_capability_census_test.go
        task-reasoning-step-support-table/ package task_reasoning_step_support_table
          task_reasoning_step_support_table.go
          reference_share.go               the conditional release share 03a and 05 both call
          task_reasoning_step_support_table_test.go
          witness_test.go
        03a-allocate-task-quotas/          package allocate_task_quotas
          allocate_task_quotas.go          entry point
          support_derivation.go            a-support-derivation.md
          balance.go                       b-balance.md
          quota_allocation.go              c-quota-allocation.md
          replan.go                        d-replan.md
          allocate_task_quotas_test.go
        03b-construct-task-definitions/    package construct_task_definitions
          construct_task_definitions.go    entry point
          construction.go                  a-construction.md
          answer_semantics.go              b-answer-semantics.md
          definition_identity.go           c-definition-identity.md
          shortcut_resistance.go           P1 quality gate; no stored chain
          construct_task_definitions_test.go
          shortcut_resistance_test.go      P1 gate unit test
        03c-resolve-deficits/              package resolve_deficits
          resolve_deficits.go
          resolve_deficits_test.go
      04-render-prompt-and-choices/        package render_prompt_and_choices
        render_prompt_and_choices.go
        render_prompt_and_choices_test.go
      05-validate-and-export-release/      package validate_and_export_release
        validate_and_export_release.go     entry point
        release_checks.go                  release-checks.md
        manifest.go                        release manifest and `release_id`
        dataset_card.go                    dataset card
        release_writer.go                  staged release directory and `current`
        failure_merge.go                   failure partition merge and reconciliation
        review_gate.go                     review ledger and sampling matrix
        validate_and_export_release_test.go
    end-to-end/                            package end_to_end
      end_to_end_test.go
  python/                                  Python worker package
    cadqa_dataset_generator/
      __init__.py
      contracts.py                         JSON worker protocol contracts
      models.py                            Pydantic artifact row models
      canonicalization.py                  numbers, JSON, hashes, and ordering
      worker.py                            worker entry point, one stage per process
      parquet_writer.py                    async immutable Parquet part writer
      s01d_normalize_programs.py           01d normalize programs
      s02a_extract_cadquery_ast.py         02a extract CadQuery AST
      s02b_execute_cadquery.py             02b execute CadQuery
```

A pipeline stage package starts as one file inside its group under
`internal/stages/` and grows files in the same folder; a new folder means a new
package, not a new file. `shared/` is one package with one file per concern,
not one package per file. `iocontracts/` is one package because every pipeline stage
imports it; it is a sibling of `shared/` because a subpackage would make
`shared/` a group folder.

`program-capability-census/` and `task-reasoning-step-support-table/` are
separate packages under `internal/stages/03-task-generation/` because two
pipeline stages import each: `03a` and `03b` share the program capability
census, and `03a` and the witness test share the support table.
`reference_share.go` is in the support-table package because the conditional
release share is a function of the supported value set; `05` calls it against
the persisted tables, and `03a` calls it in-process.

The `03a`, `03b`, `02c`, and `05` doc folders mirror the Go package folders
under `internal/stages/`.
Each doc sub-document has at least one same-named Go file:
`a-support-derivation.md` becomes `support_derivation.go`, `b-balance.md`
becomes `balance.go`, `graph-completeness.md` becomes `graph_completeness.go`,
and `release-checks.md` becomes `release_checks.go`. The folder `README.md` is
that pipeline stage's contract; the package entry file
(`allocate_task_quotas.go`, `construct_task_definitions.go`,
`build_cad_graph.go`, `validate_and_export_release.go`) is the code entry point.
`03` is Go-only, so these folders have no Python counterpart.

`internal/run/` is the only orchestrator. A pipeline stage package does not own
the run lock, pipeline stage completion markers, or the shared cache. The run
directory layout and the part, flush, and resume rules are in
[`run-contract.md`](run-contract.md).

## Python worker

Package `generator/python/cadqa_dataset_generator/` under the Go module root,
imported with `pythonpath = ["generator/python"]` and listed in
`[tool.hatch.build.targets.wheel] packages`. It is a worker, not an
orchestrator: the Go entry point starts it as a child process and passes typed
Parquet paths and a small JSON request. Python owns `01d`, `02a`, and `02b`
only; it does not write a release artifact or load `prompts.yaml`.

```text
generator/python/cadqa_dataset_generator/
  __init__.py
  contracts.py                             JSON worker protocol contracts
  models.py                                Pydantic artifact row models shared by the worker stages
  canonicalization.py                      numbers, JSON, hashes, and ordering shared by the worker stages
  worker.py                                worker entry point, one stage per process
  parquet_writer.py                        async immutable Parquet part writer
  s01d_normalize_programs.py               01d normalize programs
  s02a_extract_cadquery_ast.py             02a extract CadQuery AST
  s02b_execute_cadquery.py                 02b execute CadQuery
```

`contracts.py` holds only the JSON request and result documents from
[`python-and-golang.md`](python-and-golang.md#worker-contract-schema).
`models.py` holds the Parquet row models; `canonicalization.py` holds the rules
in
[`pipeline/extraction/canonicalization.md`](pipeline/extraction/canonicalization.md).
Both are shared modules, not pipeline stages, so they are not named `sNNx`.

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

Go tests sit in their package folder, because Go requires it. Python tests sit
in the suite that owns them: the worker beside its package, the repo tooling
under root `tests/`:

```text
generator/python/tests/
  test_worker.py
  test_worker_contracts.py
  test_s01d_normalize_programs.py
  test_s02a_extract_cadquery_ast.py
  test_s02b_execute_cadquery.py
```

```text
tests/                    repo tooling only; no files directly here
  ci_cd/
    test_check_doc_mirror.py
    test_check_dont_say.py
    test_check_file_length.py
    test_check_fanout.py
    test_check_test_ownership.py
    test_ci_plan.py
  manual_verification/
    test_task_browser.py
```

Root `tests/` mirrors the tooling under `tools/`: one subdirectory per tooling
family, and no file directly in `tests/`. A test for a Go pipeline stage, a
Parquet table, an oracle, a golden record, a release artifact, or the
prompt-template contract is a Go test in the owning package. When the check
needs CadQuery or OCP, the Go test starts the Python worker or tool and asserts
on its output.

`tools/ci_cd/check-test-ownership` enforces the layout: a Python test outside
these roots, any file directly in `tests/`, or a Go test with no non-test `.go`
sibling fails the check.

`prompts.yaml` has one loader, the Go `04` loader; its test is
`generator/internal/shared/prompt_templates_test.go` (`missing` until `04`
lands). There is no Python prompt validator.
`test_models_declaration.py` implements
[`pipeline/testing/00-declaration-audit.md`](pipeline/testing/00-declaration-audit.md)
and is a docs quality gate, not a pipeline test.

The cross-cutting test contracts have one home each:

| Test contract | Test home |
|---|---|
| [`00-run-contract.md`](pipeline/testing/00-run-contract.md) | `generator/internal/run/*_test.go` |
| [`00-support-tables.md`](pipeline/testing/00-support-tables.md) | `generator/internal/stages/03-task-generation/task-reasoning-step-support-table/witness_test.go` |
| [`00-declaration-audit.md`](pipeline/testing/00-declaration-audit.md) | `tests/test_models_declaration.py` |
| [`00-end-to-end.md`](pipeline/testing/00-end-to-end.md) | `generator/internal/end-to-end/end_to_end_test.go` |

A Go test function is the contract name in CamelCase:
`test_01a_metadata_happy_path_adversarial` becomes
`Test01aMetadataHappyPathAdversarial`.

## Contracts

The worker protocol contract is checked in as JSON Schema; the Go structs are
generated from it. Pipeline stage docs own the field meaning (`DS-ADR-13`).

```text
contracts/worker/v1/
  envelope.schema.json                 worker response envelope
  s01d_normalize_programs.schema.json  01d request and result
```

One schema file per typed pipeline stage. `02a` and `02b` add
`s02a_extract_cadquery_ast.schema.json` and
`s02b_execute_cadquery.schema.json` when their contracts land; a breaking wire
change creates `contracts/worker/v2/`. The generated Go structs stay in
`generator/internal/shared/` because they are JSON control documents, not
Parquet artifact models; `iocontracts/` holds the Parquet and in-memory models.

## Fixtures and config

| Path | Holds | Owner |
|---|---|---|
| `docs/dataset/implementation/pipeline/testing/fixtures/` | Coverage and rejection programs with `program_sha256`. | The test contract. |
| `docs/dataset/implementation/pipeline/testing/golden/` | Golden records. | The record format. |
| `docs/dataset/implementation/pipeline/testing/oracles/` | Oracles: pinned stage outputs, one directory per oracle kind. | The oracle format. |
| `docs/dataset/implementation/pipeline/testing/support-table.json` | Checked-in expected support table, one row per dimension value and task reasoning step count. | [`task-step-support.md`](task-step-support.md) and [`testing/00-support-tables.md`](pipeline/testing/00-support-tables.md). |
| `data/`, `runs/` | Run output: `runs/run<NNNN>/`, `runs/cache/`, and `runs/manual_verification/<tool>/`. Gitignored. | The run. |

Generator inputs (`balance.yaml`, `release-checks.yaml`, `tolerance.yaml`, and
`prompts.yaml`) live in `generator/config/`; see the Go module tree above. They
are read by path and recorded by hash, not embedded in the binary.

Fixtures stay in the docs tree because they are reviewed like code and the test
contract owns their path. A test reads them by path; it does not copy them.

The support table is a fixture, not a release artifact. The five files under a
release's `support/` are generated from the constructor over the coverage
fixture set; `05` copies them into the release and records their schema versions
and hashes in `manifest.json`.

## Tools and manual verification

Tools that are not pipeline stages are documented in
[`devtools/`](devtools/README.md). Their code is not part of the generator and is
not imported by it.

```text
tools/manual-verification/
  task_browser.py                          exists; local JSON API over one release table or one gold-oracle directory
  task_release.py                          exists; release rows, the shared row type, and program execution
  task_oracles.py                          exists; loads gold records as browser rows
  task_scene.py                            exists; typed scene payload and CadQuery tessellation
  task-browser/                            exists; Vite+ frontend: task list, 3D stage, detail panel
  build_extraction_oracle.py               exists; derives a proposed extraction-graph oracle from a program
  cadquery_method_specs.py                 exists; the method table the oracle builder diffs against the allowlist
  extraction_oracle_schema.py              exists; the Pydantic schema for an oracle record
  task_oracle_schema.py                    exists; the task-construction oracle schema
  task_oracle_runner.py                    exists; runs one oracle's gold query
  verify_task_oracles.py                   exists; verifies every task-construction oracle against its gold query
  render_task.py                           planned; one release row's render plus its printed card
  review_pack.py                           planned; `pack generate` and `pack record` from devtools/review-pack.md
  run_report.py                            planned; batch counts, distributions, timings, and pending review cells
  rejection_contact_sheet.py               planned; one oracle render and disposition per rejected program
  residual_sample.py                       planned; the `3/p` random pool sample
tools/contracts/
  export_worker_schemas.py                 exists; exports the worker JSON Schema from Pydantic
```

`task_browser.py`, `task_release.py`, `task_oracles.py`, `task_scene.py`, and
`task-browser/` exist; `build_extraction_oracle.py` exists and writes a
`proposed` oracle for a
human to verify. `verify_task_oracles.py` runs every task-construction oracle's
gold query and records the environment and the observed output; the records are
in
[`pipeline/testing/oracles/task-construction/`](pipeline/testing/oracles/task-construction/README.md).
`render_task.py` is the first-release fallback and the
`P0-W2`/`P0-W4` review tool. `review_pack.py` is the sampled matrix that gates
export. `run_report.py` is the report the
[manual-verification protocol](../../../plans/nov-21/manual-verification-protocol.md)
requires for the batch passes. `rejection_contact_sheet.py` and
`residual_sample.py` produce the absence and residual evidence.

A tool that becomes load-bearing moves into the package and gets a test
contract. The task browser is the first available manual verification tool; see
[`devtools/task-browser.md`](devtools/task-browser.md). The review pack and its
ledger are planned; see [`devtools/review-pack.md`](devtools/review-pack.md).

## Artifacts awaiting an owner

These are named in the plan or a pipeline stage doc but have no artifact row or
code home yet. A file path is not assigned until the owner document decides the
artifact.

| Artifact | Status | Owner decision |
|---|---|---|
| `family_split_registry` | `missing`; `DA-8` records that [`artifacts.md`](artifacts.md) has no row. | Add the artifact row first. `05` writes it after a release; `03a` reads the previous release's registry. Choose whether it is a release control document or a run-level artifact, and record its hash in the release manifest. |
| `run_report` | `missing`; the manual-verification protocol and [`graph-completeness.md`](pipeline/extraction/graph-completeness.md#8-report) both refer to it. | Choose `generator report` or `tools/manual-verification/run_report.py`. It is evidence, not a release file. |
| Review ledger | `exists` in [`artifacts.md`](artifacts.md); `tools/manual-verification/task_browser.py` writes it from `P0-W2`, and `review_pack.py` reuses the writer from `P0-W6`. | Both write `runs/manual_verification/review_pack/<release_id>/review-ledger.parquet`; `05` copies it into the release and records `review_ledger_sha256`. |
| Evaluation material and grader | Out of scope for this tree. | [`docs/train-and-eval/`](../../train-and-eval/) owns the harness, grader, prompt-only view, answer parsing, and scoring. `04` only renders the release prompt. |

`family_split_registry` is the durable
`cadevolve_program_family_id -> split` record. `03a` assigns splits by
deterministic greedy balancing over the current family set. A later cumulative
release adds families, and the same greedy pass can move an already released
family from `train` to `test`. The registry lets `03a` honour existing
assignments and assign only new families. It must exist before the first
release, or the first release becomes the migration.

## Naming map

| Pipeline stage doc | Go folder and package | Python module | Test |
|---|---|---|---|
| `01a-read-cadevolve-metadata` | `stages/01-external-dataset-etl/01a-read-cadevolve-metadata`, `read_cadevolve_metadata` | — | `01a_read_cadevolve_metadata_test.go` |
| `01b-select-program-pool` | `stages/01-external-dataset-etl/01b-select-program-pool`, `select_program_pool` | — | `01b_select_program_pool_test.go` |
| `01c-fetch-program-pool` | `stages/01-external-dataset-etl/01c-fetch-program-pool`, `fetch_program_pool` | — | `01c_fetch_program_pool_test.go` |
| `01d-normalize-programs` | — | `s01d_normalize_programs.py` | `test_s01d_normalize_programs.py` |
| `01e-write-external-dataset-manifest` | `stages/01-external-dataset-etl/01e-write-external-dataset-manifest`, `write_external_dataset_manifest` | — | `01e_write_external_dataset_manifest_test.go` |
| `02a-extract-cadquery-ast` | — | `s02a_extract_cadquery_ast.py` | `test_s02a_extract_cadquery_ast.py` |
| `02b-execute-cadquery` | — | `s02b_execute_cadquery.py` | `test_s02b_execute_cadquery.py` |
| `02c-build-cad-graph` | `stages/02c-build-cad-graph`, `build_cad_graph` | — | `02c_build_cad_graph_test.go` |
| `03a-allocate-task-quotas` | `stages/03-task-generation/03a-allocate-task-quotas`, `allocate_task_quotas` | — | `03a_allocate_task_quotas_test.go` |
| `03b-construct-task-definitions` | `stages/03-task-generation/03b-construct-task-definitions`, `construct_task_definitions` | — | `03b_construct_task_definitions_test.go` |
| `03c-resolve-deficits` | `stages/03-task-generation/03c-resolve-deficits`, `resolve_deficits` | — | `03c_resolve_deficits_test.go` |
| `04-render-prompt-and-choices` | `stages/04-render-prompt-and-choices`, `render_prompt_and_choices` | — | `04_render_prompt_and_choices_test.go` |
| `05-validate-and-export-release` | `stages/05-validate-and-export-release`, `validate_and_export_release` | — | `05_validate_and_export_release_test.go` |

The run contract is cross-cutting; its Go package is `internal/run`, and its
test contract is
[`pipeline/testing/00-run-contract.md`](pipeline/testing/00-run-contract.md).
`internal/iocontracts/` and `internal/shared/` are not pipeline stages, so they
have no row in this table.

## Bootstrap order

The work-item order is owned by
[`plans/nov-21/dataset-implementation-plan.md`](../../../plans/nov-21/dataset-implementation-plan.md).
This section is the file and package bootstrap order within those work items.

1. `go.mod`, `main.go`, `internal/run/`, `internal/shared/`, and
   `internal/iocontracts/`, including `run_manifest.go`, `run_state.go`,
   `cache_index.go`, `parquet_writer.go`, `tolerance_policy.go`,
   `prompt_templates.go`, and `selection_policy.go`.
2. `stages/01-external-dataset-etl/` with `01a`, `01b`, `01c`, `01e`;
   `s01d_normalize_programs.py` is the Python sub-step.
3. `s02a_extract_cadquery_ast.py`, `s02b_execute_cadquery.py`,
   `stages/02c-build-cad-graph/` with `graph_construction.go`,
   `graph_persistence.go`, and `graph_completeness.go`.
4. `stages/03-task-generation/program-capability-census/`, `03b`,
   `stages/03-task-generation/task-reasoning-step-support-table/` with
   `reference_share.go`, because the support table is what `03a` reads.
5. `03a`, `03c`, `04`, `05`, `end-to-end`, all under `internal/stages/` except
   `end-to-end`.
6. `render_task.py`, `run_report.py`, `review_pack.py`,
   `rejection_contact_sheet.py`, and `residual_sample.py`, as the owner
   verification points need them.

## Deleted generator

`dataset/` was the pre-rebuild generator, and `train_and_eval/` was its training
and evaluation stack. Both were deleted on 2026-11-21. The tag
`before-deleting-the-old-generator-and-harness` preserves them in history.

They were deleted rather than migrated for two reasons:

- their release validator rejected rows their own materializer produced, so the
  tests encoded a contract that no longer held;
- the release contract in
  [`../requirements/release-dataset-contract.md`](../requirements/release-dataset-contract.md)
  removed the two-file row views that the evaluation stack was built on, and the
  prompt no longer has a tool-call round trip.

The tests and tools that only served them were deleted with them:
`tests/test_graph_first_pipeline.py`, `tests/test_operation_extraction.py`,
`tests/test_void_region_policy.py`,
`tools/analyze_release_gate_feasibility.py`,
`tools/verify_cadevolve_parquet_parity.py`, `tools/dataset_explorer.py`, and
`tools/bench_graph_columnar.py`.

`docs/train-and-eval/` is kept for the training stack rewrite. It describes the
deleted stack and does not describe code that exists.

New generator code never imports the deleted modules, because they no longer
exist; a change that needs a helper from them reimplements it against the
current contract instead.

## Not here

- Evaluation harness, grader, prompt-only view, and scoring:
  [`../../train-and-eval/`](../../train-and-eval/).
- Training and evaluation code:
  [`../../train-and-eval/`](../../train-and-eval/).
- Repository CI and pre-commit tools:
  [`../../general-architecture/ci-cd.md`](../../general-architecture/ci-cd.md).
- Pipeline stage behaviour: [`pipeline/`](pipeline/00-end-to-end.md).
- Release columns and consumer rules:
  [`../requirements/release-dataset-contract.md`](../requirements/release-dataset-contract.md).
