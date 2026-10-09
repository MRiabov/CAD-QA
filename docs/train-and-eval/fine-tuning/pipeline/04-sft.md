# 04 — SFT

## Purpose

Supervised-fine-tune **LFM2.5** with LoRA (bf16) via `liquid-finetune`, in **two phases**.

## Two phases (FT-D16)

- **Phase 1 — refocus on coding (plus easy tasks):** the general mix (⅓ coding agent, ⅓ 3D math,
  ⅓ text2CAD + edits) + a low-hop slice of `learn_the_cadqa_task`.
- **Phase 2 — CAD-QA task + preserve:** the full **progressive** `learn_the_cadqa_task` (0→1→2→3→5)
  alongside the general mix. **No separate `emit_our_tool_call_format`** — the format is carried by the
  task.

A **phase-2-only fallback** applies if phase 1 shows no measured phase-end gain.

## Recipe (FT-D11, FT-D12)

- **Plain LoRA on the bf16 base** (not QLoRA by default), cookbook hyperparameters (`r=16`,
  `lora_alpha=32`, `lr=2e-4`, cookbook epochs), gradient checkpointing + accumulation.
- **Do not write a trainer.** Use `liquid-finetune` configs (`TrainingConfig(extends="DEFAULT_SFT")`,
  `PeftConfig(extends="DEFAULT_LORA")`); override only `model_name` and the dataset path until a measured
  result says otherwise.
- **Completion-only loss** verified on the `messages` format (not hand-rolled masking).
- **Base + stack:** LFM2.5 (2.6B primary, 1.2B pilot) on `liquid-finetune` (FT-D11).

## Inputs / outputs

- **In:** Liquid `messages` SFT JSONL (03).
- **Out:** a LoRA **adapter**, then a **merged LLM model** (merge step to be scripted; FT-D12).

## Verification

```bash
# smoke: reproduce the Liquid SFT example verbatim on smoltalk, then the Home Assistant loop
liquid-finetune job_configs/sft_example.yaml
uv run python train_and_eval/train/sft_train.py   # once ported to the LFM2.5 stack
```

## Open questions

- **Q1.** Does `liquid-finetune` / TRL mask the prompt for `messages` SFT by default (`../training.md` Q1)?
- **Q2.** Does the LFM2.5 chat template pass our `submit_*` tool list through unchanged (`../training.md` Q2)?
