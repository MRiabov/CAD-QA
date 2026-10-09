# 07 — serving and export

## Purpose

Merge the SFT adapter into LFM2.5, export it for serving, and (where needed) serve it for batched
evaluation and RL rollouts.

## Inputs / outputs

- **In:** a LoRA **adapter** (04).
- **Out:** a **merged LLM model**, then a GGUF (llama.cpp) artifact and/or a vLLM checkpoint.

## Requirement

The served checkpoint must be numerically equivalent to the transformers LLM model it was merged from;
parity must be shown before any vLLM number is used (FT-D10, TA-C1). Merge is a tracked step (FT-D12;
TA-D2).

## Recipe

- **Merge** the adapter into the bf16 base, then **export** via the cookbook (GGUF `--quant-type q8_0` or
  the MLX/vLLM path). Quantization is an export/serving step, not a training step.
- **Serve** on llama.cpp (GGUF) or vLLM for batched eval/rollouts.

## Verification

```bash
# merge + export (cookbook), then a parity check (transformers vs the served checkpoint)
uv run python train_and_eval/setup/merge_adapter.py --src <adapter> --dst <merged>
```

## Open questions

- **Q1.** Parity precision: argmax token ids, or logprobs within a tolerance (TA-C1)?
- **Q2.** One tracked environment, or separate SFT and serving environments (`../../../../plans/oct-8/trust-audit.md` Q3)?
