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

Prepare answer-only SFT JSONL:

```bash
uv run python -m scripts.training.prepare_answer_sft_dataset \
  --dataset-dir data/cadqa_smoke \
  --output-dir runs/answer_sft/sft
```

Write a task-balanced subset for training canaries:

```bash
uv run python -m scripts.dataset.balance_dataset_classes \
  data/cadqa_smoke \
  --output-dir runs/cadqa_balanced \
  --max-rows-per-task 200
```

Generate grouped numeric counterfactual source variants:

```bash
uv run python -m scripts.dataset.generate_counterfactual_sources \
  --source-dir /path/to/cadevolve_sources \
  --output-dir runs/counterfactual_sources \
  --limit 10
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
