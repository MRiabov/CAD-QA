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
- **Assistant-only loss, set explicitly.** TRL's `assistant_only_loss` defaults to `False` and
  conversational (`messages`) data gets full-sequence loss — set `assistant_only_loss: true` (or
  `completion_only_loss: true`). It needs the template's `{% generation %}`/`{% endgeneration %}` markers
  (present in LFM2.5). Not hand-rolled masking.
- **Base + stack:** LFM2.5 (2.6B primary, 1.2B pilot) on `liquid-finetune` (FT-D11).

## Inputs / outputs

- **In:** Liquid `messages` SFT set (03).
- **Out:** a LoRA **adapter** (base + adapter) — the training output (FT-D23). A **merged LLM model** is
  produced **on demand** for a standalone checkpoint or a GGUF K-quant export (07). Evaluation runs the
  adapter on **HF Transformers** (the reference runtime, FT-D23), so no merge is needed to measure.

## Verification

```bash
# smoke: reproduce the Liquid SFT example verbatim on smoltalk, then the Home Assistant loop
liquid-finetune job_configs/sft_example.yaml
uv run python train_and_eval/train/sft_train.py   # once ported to the LFM2.5 stack
```

## Open questions

_(none)_

## Resolved questions

- **Q1.** *(2026-10-09)* **Not masked by default.** TRL `SFTConfig.assistant_only_loss` defaults to
  `False`; conversational `messages` data gets full-sequence loss. Set `assistant_only_loss: true` (or
  `completion_only_loss: true`). Both need `{% generation %}`/`{% endgeneration %}` — the LFM2.5
  `chat_template.jinja` has them around the assistant branch (incl. `render_tool_calls`); `liquid-finetune`
  also ships `job_configs/chat_templates/lfm2_5_chat_template.jinja`. Verify on the smoltalk reproduction.
- **Q2.** *(2026-10-09)* **Passes through.** The LFM2.5 template serializes any `tools` list into the system
  prompt (`List of tools: [<json>, …]`), no name allowlist, so custom `submit_*` tools pass unchanged.
  Conditions: omit `<|tool_list_start|>`/`<|tool_list_end|>` for LFM2.5 (auto-stripped); calls pre-baked as
  `<|tool_call_start|>[name(args)]<|tool_call_end|>`; OpenAI `tool_calls` auto-converted; foreign
  `<tool_call>` XML rejected.
