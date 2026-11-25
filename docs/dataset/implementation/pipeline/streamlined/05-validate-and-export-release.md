# 05 validate and export release — consumer artifacts

> Authoritative: `../05-validate-and-export-release.md`
> Models: `models/05-validate-and-export-release.md`
> Templates: `../../prompt-templates.md`
> Run contract: `../../run-contract.md`

This pipeline stage mirrors the authoritative `05` file and folder. The flow for this pipeline stage is here; the
coverage and balance arithmetic is in [`release-checks.md`](05-validate-and-export-release/release-checks.md).

READ:

- `ReleaseTable` from `04`
- `RenderConfig` passed to `04` and `05` → `PromptTemplateSet`, `release_seed`
- five task reasoning step support tables
- `balance.yaml` and `checks.yaml`
- `ExternalDatasetManifest` from `01e`
- `GraphCompletenessReport` per program from `02c` → `disposition`, missing, orphan, and unclassified counts
- pinned external benchmark program set
- failure partitions for each pipeline stage
- the run manifest and the review ledger

WRITE:

- `release.parquet`, `failures.parquet`, `manifest.json`, `dataset-card.md`, `support/target-category-by-step.json`, `support/clue-type-by-step.json`, `support/clue-reduction-form-by-step.json`, `support/answer-meaning-by-step.json`, `support/answer-format-by-step.json`
- `ReleaseArtifacts` `(release_id)`
- write the release into `release/.tmp-<release_id>/` and rename it to `release/<release_id>/`; replace `release/current` by an atomic symlink rename
- failure partition `05_validate_and_export_release`

## 1 — Validate the release table

TRANSFORM:

- validate the release table schema and row counts
- the prompt is answer-free; a multiple-choice label is not answer data, because the prompt lists every label
- `task_id` is unique; exactly one answer set per row
- recompute `prompt_sha256` from the `prompt` bytes
- `clue_types` has one entry per `clue_reduction_form_profile` entry, same order and same clue type
- check `gold_answer` against `answer_format`; require `tolerance` for every non-exact answer
- for a multiple-choice row, recheck `choices`: at least five entries, labels contiguous from `A` with no repeat, answer values distinct under `same_answer`, `gold_answer.label` one of the labels, and that label's answer value equal to `answer_evidence.answer_equivalent_answer`; every other row has an empty `choices` pool
- do not recompute `answer_sha256`; `release_table_sha256` covers the answer columns
- recheck split isolation by `cadevolve_program_family_id` on the final table

WRITE:

- (none)

## 2 — Coverage and balance

TRANSFORM:

- validate `balance.yaml` with the `03a` rules; `release.share_tolerance` is in `[0, 1)`
- `release.distinct_answer_min` is read only here, for the P1 distinct-answer check
- validate `checks.yaml`: an unknown field, an unknown `arithmetic`, a duplicate `id`, or a bound reference that does not resolve in `balance.yaml` stops the export before any check runs
- aggregate the `GraphCompletenessReport` set into one `graph_completeness` check row; a non-zero missing, orphan, or unclassified count is an enforced miss
- run every check listed in `checks.yaml` with the arithmetic semantics in [`release-checks.md`](05-validate-and-export-release/release-checks.md); a check not in the file is not run, and a report row whose check is not in the file is a defect
- `05` holds no share of its own
- never drop a task to make a share fit

WRITE:

- (none)

## 3 — Failures and reconciliation

TRANSFORM:

- merge failure partitions: group by `failure_id`, sum `occurrence_count`, require every other column to agree, sort by `pipeline_stage`, `program_id`, `task_id` (nulls first), `reason_code`
- a disagreement on a non-key column blocks the export
- reconcile each chain: entering count = leaving count + failures at that step; programs = selected, fetched, normalized, AST accepted, runtime accepted, graphed; tasks = attempted, constructed, rendered, exported
- a mismatch blocks the export and names the step and counts
- aggregate rejection counts from `failures.parquet` by pipeline stage and reason, separately for programs and tasks

WRITE:

- (none)

## 4 — Review gate

TRANSFORM:

- require a current `pass` in the review ledger for every required sampling cell; a `defect` or a missing cell blocks the export
- the sample covers every clue type, every answer meaning, every answer format, and every task reasoning step count in the release, up to 10; for 6–10, review at least 30 tasks per tier or every task if fewer
- each sampled task carries the prompt, one render of the final solid state with the target and every clue-bound entity highlighted in a distinct colour and labelled with its clue number, and the gold answer
- the pack is internal and is not a release file

WRITE:

- (none)

## 5 — Export

TRANSFORM:

- re-validate `prompts.yaml` against the template sub-document; a missing, extra, or untyped placeholder blocks the export before any file is written
- `release_id = cadqarel:<sha256>` over the canonical JSON of `generator_version, implementation_scope, external_dataset_manifest_sha256, balance_policy_sha256, prompt_template_version, prompts_yaml_sha256, release_seed`; computed once, never patched, and `created_at` is not an input
- `release_table_sha256` from the finished `release.parquet`
- `generator_version` from the declared version constant; not derived from git
- copy `upstream_dataset_version` and `external_dataset_manifest_sha256` from the external dataset manifest
- record `balance_policy_version`, `balance_policy_sha256`, `checks_policy_version`, and `checks_policy_sha256`
- record prompt template version, `prompts.yaml` SHA-256, and `RenderConfig.release_seed`
- copy the five support JSON files and record their schema versions and hashes
- transfer overlap: exact normalized program text at P0; record the benchmark identity and revision
- write the dataset card from the manifest; every number is copied
- write `manifest.json` last, after the checks and the review gate pass
- `manifest.json` fields, per the release contract section 7: `release_id`, `schema_version`, `created_at`, `implementation_scope`, `generator_version`, `upstream_dataset_version`, `external_dataset_manifest_sha256`, `release_table_sha256`, `external_benchmark_id`, `external_benchmark_revision`, `task_count`, `split_counts`, `program_family_count`, `program_family_split_counts`, `task_reasoning_step_counts`, `warmup_task_count`, `distinct_cad_model_count`, `answer_set_sha256`, `prompt_template_version`, `prompts_yaml_sha256`, `release_seed`, `balance_policy_version`, `balance_policy_sha256`, `checks_policy_version`, `checks_policy_sha256`, `support_table_versions`, `support_table_sha256`, `checks`, `known_misses`, `failure_count`

WRITE:

- `ReleaseArtifacts` `(release_id)` → `release.parquet`, `failures.parquet`, `manifest.json`, `dataset-card.md`, `support/`
- `ReleaseManifest` → the fields above
- the release directory is staged and renamed; `release/current` is replaced atomically
