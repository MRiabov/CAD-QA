# 04 — SFT

## Purpose

Supervised-fine-tune a **base LLM model** on the **normalized text** of accepted **training
traces**, producing a LoRA **adapter**.

## Inputs / outputs

- **In:** `normalized text` JSONL (`sft_texts.jsonl`; each record has a pre-rendered `text`)
  from 03.
- **Out `adapter`:** LoRA weights saved to `CADQA_SFT_OUT` via `model.save_pretrained`
  (`train_and_eval/train/sft_train.py::main`).
- **Produced out-of-band:** the **merged LLM model** (no code in this repo).
- **Config knobs (env):** `CADQA_SFT_SEQ` (default `6144`), `CADQA_SFT_EPOCHS` (`4`),
  `CADQA_SFT_LR` (`3e-4`), `CADQA_SFT_OUT`, `CADQA_SFT_TRACES`, `CADQA_SFT_ROWS` (`0`=all).

## Requirement

The adapter must improve held-out exact-match accuracy over the **base LLM model** without
degenerating into over-generation. Concretely: on held-out rows, SFT should raise accuracy
above the base baseline and keep the LLM model emitting a parseable `submit_*` call within a
bounded budget.

## Current status

`[unverified — needs GPU + unsloth/trl]`. Code is present; no training run was performed in
this audit. Historical result (`docs/_archive/agent_handoff_2026-08-09.md`): native-format SFT on 268
traces → 50% accuracy / 58.3% tool-valid on 12 held-out rows; post-gold-fix re-run 41.7% /
75% on the same 12 rows. Those numbers are directionally encouraging but statistically
unusable (12 rows).

## Verification

```bash
# on a box with the unsloth stack and sft_texts.jsonl
CADQA_SFT_TRACES=/root/cadqa-bench/sft_texts.jsonl \
CADQA_SFT_OUT=/root/cadqa-sft-final \
rtk uv run python train_and_eval/train/sft_train.py

# or the launcher used on the box
bash train_and_eval/train/run_sft.sh
```

Then evaluate via [06-harness-modes.md](06-harness-modes.md) (the SFT script itself does not
evaluate).

## Local decisions

### FT-04-D1 — QLoRA (4-bit NF4) in the current code

- **Status:** accepted (2026-08) — but see the open question.
- **Context:** the base LLM model is `unsloth/gemma-4-E2B-it` (~5.1B total / ~2.3B active).
- **Decision:** `FastVisionModel.from_pretrained(load_in_4bit=True, bnb_4bit_quant_type="nf4",
  bnb_4bit_compute_dtype="bfloat16")`, then `get_peft_model(r=32, lora_alpha=64,
  target_modules=[q,k,v,o,gate,up,down]_proj)`.
- **Consequences:** the committed code is QLoRA, while `docs/_archive/agent_handoff_2026-08-09.md`
  section 5 says the working runs used `load_in_4bit=False` (16-bit LoRA). Which produced the
  50% result is `[unknown]`.

### FT-04-D2 — `loss_type="nll"` and forced gemma eos/pad

- **Status:** accepted (2026-08).
- **Context:** trl 1.9.2 defaults to `chunked_nll`, which breaks on unsloth's
  `functools.partial`-wrapped forward; gemma-4 eos is `<turn|>` and pad `<pad>`, which the
  unsloth defaults are not.
- **Decision:** monkeypatch `SFTConfig.__init__` to drop `push_to_hub_token`, force
  `eos_token="<turn|>"` and `pad_token="<pad>"`, and set `loss_type="nll"` in the config
  (`train_and_eval/train/sft_train.py`).
- **Consequences:** these are version-specific workarounds against `trl`/`unsloth`; they
  must be re-checked when either library moves.

### FT-04-D3 — Train on the flat pre-rendered `text` column

- **Status:** accepted (2026-08).
- **Context:** 03 pre-renders the whole conversation.
- **Decision:** `build_dataset` builds a `Dataset` with one `text` field; packing is off.
- **Consequences:** whether the prompt is masked is delegated to the trainer default; see the
  open question.

### FT-04-D4 — Sequence length 6144

- **Status:** accepted (2026-08).
- **Context:** measured normalized sequences were p50 2221 / p90 4066 / max 5822.
- **Decision:** `SEQ=6144` fits 100% of the agent training trace pool (268 records).
- **Consequences:** a longer future agent training trace pool no longer fits this budget.

## Open questions

- **Is the prompt masked?** `build_dataset` passes a single `text` column to `SFTTrainer`;
  no masking or completion-only collator is configured. If the prompt is not masked, the
  LLM model is trained to reproduce the question, which is consistent with the observed
  over-generation and the earlier GRPO entropy collapse. This is a P0 correctness question.
- **QLoRA vs 16-bit LoRA.** Code says 4-bit; the handoff narrative says 16-bit produced the
  working run. Reconcile or re-run and record.
- **Adapter merge is missing.** No code merges the adapter into the base LLM model; the eval
  expects a merged bf16 directory. Script it or document the manual step.
- **No held-out gate in the script.** `sft_train.py` does not evaluate; `[unknown]` how the
  "improves over base" requirement is enforced.
- **Over-generation.** Historical eval completions over-generated; GRPO collapsed to 2-token
  completions with near-zero entropy (`docs/development-context.md`). The SFT signal is
  suspected to be imitation-heavy, not reasoning-preserving.

## Resolved questions

_(none yet)_

## Extra deliverables - P2

- A sealed held-out SFT evaluation run recorded as a dated experiment.
- Ablation over `SEQ`, `EPOCHS`, and masked vs unmasked loss.
