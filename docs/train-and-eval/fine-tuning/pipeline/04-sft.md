# 04 — SFT

## Purpose

Supervised-fine-tune **LFM2.5** with LoRA (bf16) via `liquid-finetune`, in **two phases**. The SFT set is
built **only from `sft_train`**; `rl_train` (the RL-readiness gate/RL pool) and `eval` are excluded
(`../data.md` §5).

## Two phases (FT-D16)

- **Phase 1 — refocus on coding (plus easy tasks):** the general mix (⅓ coding agent, ⅓ 3D math,
  ⅓ text2CAD + edits) + a low-hop slice of `learn_the_cadqa_task`.
- **Phase 2 — CAD-QA task + preserve:** the remaining release hop tiers (`{3..10}`; 6–10 are added only
  after the 6–10 release gate and through the §4.1 advancement gate) alongside the general mix. **No separate
  `emit_our_tool_call_format`** — the format is carried by the task.

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
- **Eval/save cadence is not a local choice.** Use the evaluation plan's rule
  (`../../evaluation/plan.md` §6): periodic eval only when an epoch is ≥250 optimizer steps, at most
  once per epoch and 3× per phase; `eval_steps = save_steps = steps_per_epoch`. Periodic eval is a trend
  monitor, not a checkpoint-selection signal; the thesis checkpoint is the final phase-2 step.

## Input pipeline (keep the GPU fed)

Loading is prefetch, not asyncio: TRL/HF `TrainingArguments` default to `dataloader_num_workers=0`, so
batches are built in the main process unless `liquid-finetune` overrides it. Confirm the effective config
on the first run.

- Materialize the final SFT set as local Parquet/Arrow (memory-mapped); never stream from the Hub during
  a run. ~80M tokens (8k average) fits in RAM.
- Pre-tokenize once through the trainer's init-time map, so the hot loop does not apply the chat template
  per batch.
- Set `dataloader_num_workers=2–4`, `persistent_workers=True`, `prefetch_factor=2–4`,
  `pin_memory=True`, and dynamic padding. These are `TrainingConfig`/`TrainingArguments` fields — still
  do not write a trainer.
- Measure GPU utilization and step time on the first real run; raise workers/prefetch only if utilization
  dips between steps. With gradient checkpointing + accumulation the loop is usually compute-bound, so
  this is a cheap check, not a tuning axis.

## Sequence and truncation policy

Working policy (2026-10-19; confirm against the measured trace-length distribution on the first
fine-tuning runs):

- **Admission window: 16,384 tokens** for the whole tokenized trace (system prompt + tool declarations +
  all turns). A trace above the window is **rejected, not truncated**, and counted
  (`{dropped,total,rate}`; the no-silent-data-loss invariant).
- **Per-response cap: 6,144 tokens** on each assistant turn, enforced during teacher sampling. This is not
  the training window; do not reuse it as `max_seq_length`.
- **Turn cap: 10** `run_code`/tool round-trips.
- **`max_seq_length=16,384`**, equal to the admission window, so an admitted trace cannot lose its final
  `submit_*` call to truncation. No right-truncation, ever. Packing is **off** for agent traces until a
  measured need appears (cross-example attention would change the target).

## Inputs / outputs

- **In:** Liquid `messages` SFT set (03).
- **Out:** a LoRA **adapter** (base + adapter) — the training output (FT-D23). A **merged LLM model** is
  produced **on demand** for a standalone checkpoint or a GGUF K-quant export (07). Evaluation runs the
  adapter on **HF Transformers** (the reference runtime, FT-D23), so no merge is needed to measure.

## Verification

```bash
# toolchain smoke (not masking evidence): reproduce the Liquid SFT example verbatim on smoltalk,
# then the Home Assistant loop
liquid-finetune job_configs/sft_example.yaml
uv run python train_and_eval/train/sft_train.py   # once ported to the LFM2.5 stack
```

**Masking evidence is a separate, mandatory check.** Smoltalk is single-turn with no tools and no
`tool`-role turns, so it never executes the template's `render_tool_calls` branch. A tool-bearing fixture
must be rendered through the **installed** `liquid-finetune` template
(`job_configs/chat_templates/lfm2_5_chat_template.jinja`) and asserted at the token/label level:
assistant reasoning **and** the tool call are loss-bearing; system/user/tool-response tokens are masked;
the final `submit_*` survives tokenization. [`../testing.md`](../testing.md) owns the fixture and
assertions.

**Template rule (strong guidance, not absolute).** Use the template `liquid-finetune` ships and applies;
do not vendor, patch, or pass a `chat_template` override. A local change invalidates the sampled traces
(`../training.md` §5.3), and the format contract is the provider's (`../training.md` §5.4). Any override
is an explicit, documented decision settled by measurement on the first fine-tuning runs — never a silent
workaround to make a check pass. Record the `liquid-finetune` revision in the run manifest; the template
comes from that package, not this repo.

## Open questions

None.

## Resolved questions

- **Q1.** *(2026-10-09)* **Not masked by default.** TRL `SFTConfig.assistant_only_loss` defaults to
  `False`; conversational `messages` data gets full-sequence loss. Set `assistant_only_loss: true` (or
  `completion_only_loss: true`). Both need `{% generation %}`/`{% endgeneration %}` — the LFM2.5
  `chat_template.jinja` has them around the assistant branch (incl. `render_tool_calls`); `liquid-finetune`
  also ships `job_configs/chat_templates/lfm2_5_chat_template.jinja`. Smoltalk cannot verify this: it is
  single-turn with no tools, so `render_tool_calls` never runs. Verify with a tool-bearing fixture through
  the installed template (token/label level); see §Verification.
- **Q2.** *(2026-10-09)* **Passes through.** The LFM2.5 template serializes any `tools` list into the system
  prompt (`List of tools: [<json>, …]`), no name allowlist, so custom `submit_*` tools pass unchanged.
  Conditions: omit `<|tool_list_start|>`/`<|tool_list_end|>` for LFM2.5 (auto-stripped); calls pre-baked as
  `<|tool_call_start|>[name(args)]<|tool_call_end|>`; OpenAI `tool_calls` auto-converted; foreign
  `<tool_call>` XML rejected.
