# 05 validate and export release — consumer artifacts

> Authoritative: `../05-validate-and-export-release.md`
> Checks: `../05-validate-and-export-release/release-checks.md`

READ:
- `ReleaseTable` from `04`
- `RenderConfig` from `04` → `PromptTemplateSet`, `release_seed`
- five task reasoning step support tables
- `balance.yaml`
- `ExternalDatasetManifest` from `01e`
- pinned external benchmark program set
- per-pipeline-stage failure partitions

## 1 — Validate the release table

TRANSFORM:
- validate the release table schema and row counts
- the prompt is answer-free
- `task_id` is unique; exactly one answer set per row
- recompute `prompt_sha256` from the `prompt` bytes
- `clue_types` has one entry per `clue_operand_form_profile` entry, same order and same clue type
- parse `gold_answer_json` according to `answer_format`; require `tolerance_json` for every non-exact answer
- do not recompute `answer_sha256`; `release_table_sha256` covers the answer columns
- recheck split isolation by `cadevolve_program_family_id` on the final table

WRITE:
- (none)

## 2 — Coverage and balance

TRANSFORM:
- validate `balance.yaml` with the `03a` rules; `release.share_tolerance` is in `[0, 1)`
- compute `conditional_release_share(s, d, v)` with the same function `03a` calls; `05` holds no share of its own
- run every coverage check per task reasoning step count: `target_category_coverage, clue_type_coverage, clue_operand_form_coverage, answer_meaning_coverage, answer_format_coverage`; no whole-release coverage row
- run every release-level check: `release_task_count, step_count_range, distinct_cad_model_count, cad_model_share_cap, built_shape_share_floor, split_share, step_share, steps_three_or_more_share, warmup_set, answer_format_share_range, answer_meaning_share_range, target_category_share_cap, clue_type_share_cap, clue_operand_form_release_share, distinct_answer_count, answer_share_cap`
- run every per-step check: `answer_format_step_mix, clue_type_step_share_cap, clue_type_step_mix, answer_meaning_step_mix, clue_operand_form_severe_mix, clue_operand_form_step_mix`
- convert every bound to an integer count: `minimum_count = ceil(minimum_share * denominator)`, `maximum_count = floor(maximum_share * denominator)`; per-step `minimum_count = max(1, ceil(0.5 * conditional_release_share * denominator))`, `maximum_count = floor(2 * conditional_release_share * denominator)`; the severe row uses its own multiples
- outcome is `pass | miss | superseded | not_applicable | deferred`; disposition is `enforced | reported | deferred`
- an `enforced` miss blocks the export until the owner accepts it and it is recorded in `known_misses`; a `reported` miss never blocks; a `deferred` row measures nothing
- a `superseded` row is recorded and does not block; it is not a known miss
- emit at least one row per listed check; a report that omits a check is a rejection
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
- write a visual review pack for a sample covering every clue type, every answer meaning, and every answer format
- each sampled task carries the prompt, one render of the final solid state with the target and every clue-bound entity highlighted in a distinct colour and labelled with its clue number, and the gold answer
- a failed review blocks the export and records the reason; the defect is fixed and the task re-reviewed
- the pack is internal and is not a release file

WRITE:
- (none)

## 5 — Export

TRANSFORM:
- `release_id` from the release inputs, computed once and never patched
- `release_table_sha256` from the finished `release.parquet`
- `generator_version` from the declared version constant; not derived from git
- copy `upstream_dataset_version` and `external_dataset_manifest_sha256` from the external dataset manifest
- record `balance.yaml` version and SHA-256
- record prompt template version, `prompts.yaml` SHA-256, and `RenderConfig.release_seed`
- copy the five support JSON files and record their schema versions and hashes
- transfer overlap: exact normalized program text at P0; record the benchmark identity and revision
- write the dataset card from the manifest; every number is copied
- write `manifest.json` last, after the checks and the review gate pass

WRITE:
- `release.parquet`, `failures.parquet`, `manifest.json`, `dataset-card.md`, `support/target-category-by-step.json`, `support/clue-type-by-step.json`, `support/clue-operand-form-by-step.json`, `support/answer-meaning-by-step.json`, `support/answer-format-by-step.json`
- `ReleaseArtifacts` `(release_id)`
- failure partition `05_validate_and_export_release`
