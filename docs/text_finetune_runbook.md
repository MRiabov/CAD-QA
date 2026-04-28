# Text Fine-Tune Runbook

CAD-QA answer-only SFT uses public prompts and canonical structured answers.
Training rows must come from `train`; validation and held-out splits are for
evaluation only.

Prepare SFT JSONL:

```bash
rtk uv run python -m scripts.training.prepare_answer_sft_dataset \
  --dataset-dir runs/smoke_dataset/dataset \
  --output-dir runs/prepare_answer_sft_canary/sft \
  --max-train-rows 512 \
  --max-eval-rows 128
```

Run local format smoke:

```bash
rtk uv run python -m scripts.training.text_sft_smoke \
  --sft-dir runs/prepare_answer_sft_canary/sft
```

The checked-in `text_sft_train_unsloth` entrypoint records a gated result when
GPU training dependencies are missing.

Run the checked-in canary through the manifest:

```bash
rtk uv run python -m scripts.experiments.run_experiment_suite \
  configs/overnight_experiment_suite.yaml --run answer_sft_canary --with-dependencies --dry-run
```

On a bootstrapped GPU instance, drop `rtk` and the dry-run flag:

```bash
python -m scripts.experiments.run_experiment_suite \
  configs/overnight_experiment_suite.yaml --run answer_sft_canary --with-dependencies
```

The `answer_sft_canary` manifest entry invokes `uv run --extra training` so a
fresh environment installs the training extra before launching Unsloth/TRL. If
the canary completes, promote manually with the same trainer and a larger
`--max-steps` in a new run directory after checking loss, invalid-output rate,
GPU utilization, disk, and adapter artifacts.
