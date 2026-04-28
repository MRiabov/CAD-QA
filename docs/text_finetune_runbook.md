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
GPU training dependencies are missing. A real GPU run should use the same
manifest command after bootstrapping a PyTorch/Unsloth environment.
