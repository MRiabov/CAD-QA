# Apr 28-29 CAD-QA Answer SFT

## Purpose

Implement the CAD-QA codebase far enough to produce validated public task rows,
baseline reports, answer-only SFT JSONL, and a restartable Qwen3.5 4B canary
manifest.

## Local Commands

```bash
rtk uv run python -m compileall -q cad_qa scripts tests
rtk uv run pytest -q
rtk uv run python -m scripts.experiments.run_experiment_suite configs/orchestration_smoke.yaml --resume
rtk uv run --extra cadquery cadqa generate --auto-source-dir --output-dir runs/cadevolve_trace_probe_t30/dataset --limit 3 --workers 1 --trace-timeout-seconds 30
rtk uv run --extra cadquery cadqa validate runs/cadevolve_trace_probe_t30/dataset
rtk uv run cadqa baseline runs/cadevolve_trace_probe_t30/dataset/jsonl/train.jsonl --output-dir runs/cadevolve_trace_probe_t30/baselines
rtk uv run python -m scripts.training.prepare_answer_sft_dataset --dataset-dir runs/cadevolve_trace_probe_t30/dataset --output-dir runs/cadevolve_trace_probe_t30/sft --max-train-rows 512 --max-eval-rows 128
rtk uv run python -m scripts.training.text_sft_smoke --sft-dir runs/cadevolve_trace_probe_t30/sft
rtk uv run python -m scripts.experiments.run_experiment_suite configs/overnight_experiment_suite.yaml --run answer_sft_canary --with-dependencies --dry-run
```

## Current Status

- Implementation: local CAD-QA package, CLI, scripts, configs, and tests are
  present.
- Tests: `compileall` passes and `pytest -q` reports 10 passing tests.
- Dataset: smoke generation produces 47 validated code-plus-label rows across
  the MVP task families, with 31 train rows and 16 validation rows.
- Local orchestration: `configs/orchestration_smoke.yaml` completed all runs and
  wrote dataset, validation, baseline, SFT JSONL, and SFT-format smoke
  artifacts under `runs/`.
- CadQuery: optional dependency install succeeded through
  `uv run --extra cadquery`, with CadQuery 2.7.0 and OCP 7.8.1.1 observed in
  trace metadata.
- CADEvolve probe: adjacent source directory detected at
  `/home/maksym/Work/proj/Problemologist/big-build123d-dataset/cadevolve-cq-translation/translated`.
  A 3-source trace-backed probe with a 30 second per-source timeout generated
  921 validated rows: 33 operation-count, 96 bbox, 62 signed-volume-delta, 665
  topology-count, 6 point-membership, and 59 conservative provenance rows. The
  failure manifest is empty. A 10 second probe had one timeout, so larger runs
  should use `--trace-timeout-seconds 30` or higher.
- SFT data: CADEvolve trace probe SFT prep wrote 512 train and 128 validation
  answer-only chat rows; format smoke passed.
- 10-source RC: `data/cadqa_cadevolve_rc_10` generated 1,419 validated public
  rows: 958 train, 298 validation, and 163 test-random rows. Five of ten
  sources timed out at 30 seconds and are recorded in `failure_manifest.jsonl`;
  static operation-count rows are still emitted for failed traces. Baselines are
  under `runs/cadqa_cadevolve_rc_10_baselines`, and answer-only SFT JSONL is
  under `runs/cadqa_cadevolve_rc_10_sft`.
- Training: real SFT is gated unless GPU dependencies and pricing/account state
  are confirmed. A local direct canary invocation wrote
  `runs/answer_sft_canary/train_result.json` with status `gated` and reason
  `missing_training_dependencies:torch,transformers,trl,unsloth`. The manifest
  includes `answer_sft_canary_dry_run` for local artifact checks.

## Next Command

```bash
rtk uv run --extra cadquery cadqa generate --auto-source-dir --output-dir data/cadqa_cadevolve_rc_10 --limit 10 --workers 1 --trace-timeout-seconds 30
```
