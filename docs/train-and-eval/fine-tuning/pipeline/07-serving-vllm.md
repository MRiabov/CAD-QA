# 07 — serving (vLLM)

## Purpose

Convert a **merged LLM model** checkpoint so it loads in vLLM, and use vLLM for high-throughput
batched evaluation and rollouts.

## Inputs / outputs

- **In:** a **merged LLM model** directory in the unsloth/HF save layout (e.g.
  `/root/cadqa-sft-merged`).
- **Out `vLLM checkpoint`:** a converted safetensors directory (e.g.
  `/root/cadqa-sft-merged-vllm3`) that `vllm serve` / `LLM(model=...)` accepts.
- **Smoke script:** `train_and_eval/eval/bench_vllm.py` (throughput only).

## Requirement

The served checkpoint must be numerically equivalent to the transformers LLM model it was merged
from. A conversion that silently alters weights (for example a wrong `k_norm` mapping) makes
every vLLM number untrustworthy, so parity must be shown before vLLM results are used.

## Current status

`[unverified — needs vLLM + GPU + merged checkpoint]`. The conversion code is present; no
conversion or parity run was performed in this audit. `docs/_archive/agent_handoff_2026-08-09.md` A4
records a hand fix (weight rename + shared-layer `k_norm` duplication + `TORCH_SDPA` backend)
that made vLLM load and serve at 121–871 tok/s, **but no transformers-vs-vLLM parity check
exists**. `docs/development-context.md` lists this as an unresolved `[unverified]` risk.

## Verification

```bash
# convert (needs a merged checkpoint)
rtk uv run python train_and_eval/setup/convert_for_vllm.py \
  --src /root/cadqa-sft-merged --dst /root/cadqa-sft-merged-vllm

# throughput smoke
bash train_and_eval/eval/run_bench_vllm.sh
```

A parity check (same prompts, transformers vs vLLM, compare token logprobs or argmax) is
`[unknown]` — no such test exists.

## Local decisions

### FT-07-D1 — Hand conversion: prefix rename + duplicated shared-layer `k_norm`

- **Status:** accepted (2026-08).
- **Context:** vLLM's Gemma4 architecture expects keys under `language_model.model.*` and a
  `k_norm` weight on every decoder layer; the HF/unsloth checkpoint stores keys as
  `model.language_model.*` and only stores `k_norm` on the non-shared layers.
- **Decision:** rename the three prefixes (`model.language_model.`,
  `model.vision_tower.`, `model.audio_tower.`) and, for layers
  `>= unique_kv_layers` (default `15`), copy `k_norm` from layer `layer % unique_kv_layers`
  (`train_and_eval/setup/convert_for_vllm.py::main`). The layout assumes
  `num_kv_shared_layers=20` over 35 layers → 15 unique.
- **Consequences:** the conversion is checkpoint-specific and unasserted; it must be redone if
  the base architecture or KV-sharing config changes.

### FT-07-D2 — Use vLLM for batched eval and rollouts

- **Status:** accepted (2026-08).
- **Context:** transformers decode measured ~13–19 tok/s on a 4080S; RL rollouts need
  batching.
- **Decision:** serve the converted checkpoint in vLLM for future batched work
  (`docs/_archive/agent_handoff_2026-08-09.md` A4).
- **Consequences:** all vLLM-derived numbers inherit the parity risk until checked.

## Open questions

- **Q1.** **Parity is unverified.** There is no transformers-vs-vLLM comparison. If the `k_norm`
  duplication or prefix rename is wrong, every vLLM number is contaminated. P0.
- **Q2.** **`bench_vllm.py` is stale and contradicts the handoff.** It loads the *base* LLM model from a
  hardcoded cache glob (`google/gemma-4-E2B-it`) and calls `llm.generate` with **raw string**
  prompts; `docs/_archive/agent_handoff_2026-08-09.md` A4 warns that raw prompts produce
  EOS-immediately / fake numbers and that `llm.chat(messages)` must be used. As written, the
  smoke number is meaningless.
- **Q3.** **Hardcoded `unique_kv_layers=15`.** Derived from an assumed `num_kv_shared_layers=20`; not
  read from the checkpoint config. `[unknown]` how a config change would be detected.
- **Q4.** **Single-shard assumption.** The converter copies non-safetensors files and processes only
  `model.safetensors`; a sharded checkpoint would not be handled.
- **Q5.** **Environment pins disagree.** The untracked pins under `runs/gemma_bench/rl/env/` list
  `vllm==0.15.1`/`0.17.0` and `transformers==4.56.2`, while the narrative docs cite
  vLLM 0.26 / transformers 5.14.1. Which stack actually served the checkpoint is `[unknown]`.
- **Q6.** **Pins are not in the repo.** `runs/` is gitignored (`.gitignore`), so the requirement
  files that define the environment are not tracked; see
  [../requirements.md](../requirements.md#environment).

## Resolved questions

None yet.

## Extra deliverables - P2

- An automated parity test that fails on logprob divergence.
- Publish a vLLM-ready or GGUF artifact alongside the adapter for reproducibility.
