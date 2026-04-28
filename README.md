# CAD-QA

CAD-QA is a code-plus-label benchmark pipeline for questions over executable
CadQuery construction programs. The implementation in this repository follows
the staged design in `specs/`: source ingestion, AST operation graph extraction,
optional isolated CadQuery tracing, task-row materialization from stored trace
metadata, split-safe export, validation, and simple baselines.

## Quick Start

Generate a deterministic smoke dataset:

```bash
uv run cadqa smoke --output-dir data/cadqa_smoke
```

Validate exported rows:

```bash
uv run cadqa validate data/cadqa_smoke
```

Run baselines:

```bash
uv run cadqa baseline data/cadqa_smoke/jsonl/train.jsonl --output-dir runs/smoke_baselines
```

Run the trace-label oracle upper bound:

```bash
uv run python -m scripts.evaluation.tool_assisted_upper_bound \
  data/cadqa_smoke/jsonl/validation.jsonl \
  --output-dir runs/smoke_upper_bound
```

Load a CADEvolve source directory, or auto-detect an adjacent one, and generate
rows:

```bash
uv run cadqa generate --source-dir /path/to/cadevolve_sources --output-dir data/cadqa_run --limit 100
uv run cadqa generate --auto-source-dir --output-dir data/cadqa_auto --limit 100 --workers 2
```

Run the local orchestration smoke:

```bash
uv run python -m scripts.experiments.run_experiment_suite configs/orchestration_smoke.yaml --resume
```

Build experiment comparison tables from metric artifacts:

```bash
uv run python -m scripts.experiments.compare_experiment_runs \
  runs/smoke_baselines \
  --output-dir runs/compare_smoke_experiments
```

Check canary stop gates and package retained artifacts:

```bash
uv run python -m scripts.experiments.check_stop_gates \
  --dataset-stats runs/validate_smoke_dataset/dataset_stats.json \
  --sft-smoke-report runs/text_sft_format_smoke/text_sft_smoke_report.json \
  --experiment-comparison runs/compare_smoke_experiments/experiment_comparison.json \
  --output runs/check_smoke_stop_gates/stop_gate_report.json

uv run python -m scripts.experiments.package_run_artifacts \
  runs/smoke_dataset runs/validate_smoke_dataset runs/smoke_baselines \
  --output-dir runs/package_smoke_artifacts
```

Prepare answer-only SFT JSONL:

```bash
uv run python -m scripts.training.prepare_answer_sft_dataset \
  --dataset-dir data/cadqa_smoke \
  --output-dir runs/answer_sft/sft
```

Prepare trace-grounded reasoning SFT JSONL:

```bash
uv run python -m scripts.training.prepare_reasoning_sft_dataset \
  --dataset-dir data/cadqa_smoke \
  --output-dir runs/reasoning_sft/sft
```

Prepare SFT ablation and scaling subsets:

```bash
uv run python -m scripts.training.prepare_sft_ablation_datasets \
  --dataset-dir data/cadqa_smoke \
  --output-dir runs/sft_ablations

uv run python -m scripts.training.prepare_sft_scaling_datasets \
  --dataset-dir data/cadqa_smoke \
  --output-dir runs/sft_scaling \
  --sizes 1000 5000 15000 50000
```

Write a task-balanced subset for training canaries:

```bash
uv run python -m scripts.dataset.balance_dataset_classes \
  data/cadqa_smoke \
  --output-dir runs/cadqa_balanced \
  --max-rows-per-task 200
```

Create release QA reports:

```bash
uv run python -m scripts.dataset.manual_audit_sample \
  data/cadqa_smoke \
  --output-dir runs/manual_audit_sample

uv run python -m scripts.dataset.failure_report \
  data/cadqa_smoke \
  --output runs/failure_report.json

uv run python -m scripts.dataset.reproducibility_audit \
  data/cadqa_smoke data/cadqa_smoke_rerun \
  --output runs/reproducibility_audit.json
```

Generate grouped numeric counterfactual source variants:

```bash
uv run python -m scripts.dataset.generate_counterfactual_sources \
  --source-dir /path/to/cadevolve_sources \
  --output-dir runs/counterfactual_sources \
  --limit 10
```

Export closed-book model requests:

```bash
uv run python -m scripts.evaluation.export_prediction_requests \
  data/cadqa_smoke/jsonl/validation.jsonl \
  --output runs/eval/zero_shot_requests.jsonl

uv run python -m scripts.evaluation.build_fewshot_prompts \
  --train-rows data/cadqa_smoke/jsonl/train.jsonl \
  --eval-rows data/cadqa_smoke/jsonl/validation.jsonl \
  --output runs/eval/fewshot_requests.jsonl \
  --shots 3
```

Normalize and grade closed-book model responses:

```bash
uv run python -m scripts.evaluation.evaluate_prediction_responses \
  --rows data/cadqa_smoke/jsonl/validation.jsonl \
  --responses runs/eval/model_responses.jsonl \
  --output-dir runs/eval/model_eval \
  --label zero_shot
```

CadQuery execution is optional. Without CadQuery, the app still supports source
records, operation graphs, static task rows, smoke fixtures, validation, splits,
and baseline evaluation. With CadQuery installed, `cadqa trace` can emit scalar
snapshots for supported scripts in an isolated worker.

To run trace-backed generation in a local environment:

```bash
uv run --extra cadquery cadqa generate --auto-source-dir \
  --output-dir data/cadqa_cadevolve_rc \
  --limit 10 \
  --workers 1 \
  --trace-timeout-seconds 30 \
  --cache-dir data/cache
```

Run a resumable sharded generation probe:

```bash
uv run python -m scripts.dataset.generate_resumable_dataset \
  --output-dir runs/cadqa_resumable \
  --auto-source-dir \
  --total-limit 10 \
  --shard-size 2 \
  --workers 1 \
  --trace-timeout-seconds 30 \
  --extra-cadquery \
  --resume
```
