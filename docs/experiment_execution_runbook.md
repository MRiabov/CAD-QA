# Experiment Execution Runbook

Run experiments through manifest entries so artifacts and stop conditions are
visible.

Local preflight:

```bash
rtk uv run python -m compileall -q cad_qa scripts tests
rtk uv run pytest -q
rtk uv run python -m scripts.experiments.run_experiment_suite configs/orchestration_smoke.yaml --list
rtk uv run python -m scripts.experiments.run_experiment_suite configs/orchestration_smoke.yaml --dry-run
```

Local smoke execution:

```bash
rtk uv run python -m scripts.experiments.run_experiment_suite configs/orchestration_smoke.yaml --resume
```

Overnight manifest dry run:

```bash
rtk uv run python -m scripts.experiments.run_experiment_suite \
  configs/overnight_experiment_suite.yaml --run answer_sft_canary --with-dependencies --dry-run
```

Do not start GPU training until dataset validation passes, leakage audit passes,
SFT JSONL smoke passes, and live GPU price/account state are known.
