# Experiment Execution Runbook

Run experiments through manifest entries so artifacts and stop conditions are
visible.

Convenience wrapper for the common local gates:

```bash
rtk scripts/experiments/run_cadqa_experiment.sh preflight
rtk scripts/experiments/run_cadqa_experiment.sh smoke
rtk scripts/experiments/run_cadqa_experiment.sh canary-dry-run
```

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

GPU canary launch after `scripts/devops/bootstrap_vast_instance.sh`:

```bash
tmux new -d -s cadqa-sft \
  'cd /root/CAD-QA && python -m scripts.experiments.run_experiment_suite configs/overnight_experiment_suite.yaml --run answer_sft_canary --with-dependencies > overnight.log 2>&1'
```

Do not start GPU training until dataset validation passes, leakage audit passes,
SFT JSONL smoke passes, and live GPU price/account state are known.

The overnight manifest routes canary training through
`scripts.experiments.check_stop_gates` and invokes the trainer with
`uv run --extra training`. The local smoke manifest also writes a retention
package with `scripts.experiments.package_run_artifacts` and can stage it with
`scripts.experiments.upload_artifact_package`; keep the manifest, archive, and
upload manifest before deleting rented-instance storage.

After SFT or closed-book prediction artifacts exist, build P1 analysis reports
with `scripts.evaluation.evaluate_counterfactual_sensitivity`,
`scripts.experiments.build_task_transfer_matrix`, and
`scripts.evaluation.evaluate_cadedit_predictions`.
