# CAD-QA Implementation Status

This snapshot implements the reusable pipeline spine described by the epics and
specs.

## Implemented Locally

- Repository structure, package metadata, CLI, config loading, hashing, JSONL
  I/O, validation, and tests.
- Source ingestion from extracted CADEvolve-style directories, bounded tar
  archives, adjacent source auto-detection, and synthetic golden fixtures.
- AST-backed operation graph extraction for CADEvolve-style assignments and
  fluent chains.
- Static source safety checks before execution.
- Isolated, bounded CadQuery trace workers with scalar snapshots, topology
  counts, selector count tables when selectors are present, point samples, and
  conservative adjacent-volume provenance records.
- Per-snapshot entity IDs and best-effort adjacent topology matching for small
  snapshots using lightweight geometry signatures.
- Public row materialization for:
  - `operation_count`
  - `coordinate_frame`
  - `workplane_state`
  - `selector_count`
  - `bbox_after_step`
  - `signed_volume_delta`
  - `topology_count_after_step`
  - `point_membership`
  - `feature_provenance_choice`
- Group-safe split assignment, split manifests, leakage audits, metadata,
  failure manifests, and dataset-card generation.
- Manual audit sample export, trace failure taxonomy reports, and two-export
  reproducibility audits.
- Optional SVG audit render bundles with per-render manifest metadata and named
  orthographic view metadata.
- Optional render-backed prediction request export using audit render manifests.
- Protected split routing for generator, source-subtree, operation-signature,
  topology-signature, and point-sampling groups when enough groups exist.
- Explicit near-boundary point-membership tagging and protected
  `test_near_boundary` routing for datasets with enough source groups.
- Optional Parquet export when `pyarrow` is installed, with an explicit marker
  when the `parquet` extra is unavailable.
- Trace caching and a resumable sharded generation script for bounded scale
  runs.
- Baselines for majority, random, static operation count, regex operation
  count, selector heuristic, and oracle.
- Trace-label oracle upper-bound export for parser and metric sanity checks.
- Experiment comparison reports with headline, per-task, and per-split JSON,
  CSV, and Markdown tables.
- Deterministic task-balanced subset export for train/validation rows.
- Grouped numeric counterfactual source variant generation with a manifest.
- Conservative CADEditQA `parameter_edit_direction` row materialization from
  grouped numeric counterfactual manifests.
- Conservative CADEditQA `feature_to_edit` row materialization from validated
  feature-provenance QA rows.
- Conservative CADEditQA `selector_repair` and `workplane_offset_repair` row
  materialization from validated selector-count and coordinate-frame QA rows.
- Answer parsing/grading for strict integer, enum, numeric four-significant
  figure, and JSON bounding-box policies.
- Zero-shot and few-shot provider-agnostic prediction request export, response
  normalization, and closed-book prediction grading.
- Answer-only SFT JSONL preparation and local format smoke validation.
- Trace-grounded reasoning SFT JSONL preparation with template rationales
  derived from stored labels and diagnostics.
- Deterministic answer-only SFT ablation and row-count scaling subset
  preparation.
- Guarded answer-only Unsloth/TRL SFT entrypoint with dry-run and
  missing-dependency gates.
- Restartable manifest runner and local orchestration configs.
- Canary stop-gate reports for dataset validation, SFT smoke checks, experiment
  comparisons, and trace failure rates.
- Artifact retention packaging with checksum manifests and optional `tar.gz`
  archives.
- Draft paper scaffold covering abstract, introduction, related work, dataset
  construction, task families, experiments, limitations, and conclusion, with
  explicit placeholders for final release results.

## Validated Artifacts

- `runs/smoke_dataset/dataset`: 47 validated smoke rows across MVP task
  families.
- `runs/cadevolve_trace_probe_t30/dataset`: 921 validated rows from 3 adjacent
  CADEvolve-style sources, no failures.
- `data/cadqa_cadevolve_rc_10`: 1,419 validated rows from 10 adjacent
  CADEvolve-style sources. Five traces timed out at 30 seconds and are recorded
  in `failure_manifest.jsonl`; static rows are still emitted for those sources.
- `runs/cadqa_cadevolve_rc_10_sft`: answer-only SFT JSONL with 512 train and
  128 validation rows; format smoke passes.

## Still Gated

- Exact OpenCascade builder-history provenance is not implemented; current
  provenance rows are conservative adjacent-volume labels. Adjacent topology
  matching exists but is best-effort and intentionally skips heavy signatures on
  large snapshots.
- Full selector coverage depends on selectors appearing in traced sources.
- Counterfactual source variants exist, but verified counterfactual labels and
  public counterfactual task rows are not implemented.
- Large CADEvolve generation still needs runtime tuning and larger-source
  validation before public release, though cache-backed shard generation exists.
- Real Qwen3.5 4B SFT is gated on GPU environment, live pricing/account state,
  and training dependencies. The local entrypoint records structured dry-run or
  gated results when training should not launch.
- CADEditQA edit-verifier tasks are not yet implemented beyond shared CAD-QA
  infrastructure.
