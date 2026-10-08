# Prior-art code mining

**Status:** seed, 2026-10-07; first finding recorded 2026-10-08 (Phase 0b in progress). This
doc holds the method and candidates so the survey can be done deliberately (Phase 0b) rather
than by hand-rolling.

## Why

Literature review is done (see the manuscript). What is missing is **code/implementation**
prior art: many researchers have already built efficient LLM training / RL pipelines and
open reasoning datasets. We should mine those and build on one, instead of extending the
current vLLM workaround and hand-rolled GRPO.

The goal is a correct, efficient, reasoning-preserving pipeline we understand — not the
fastest way to a number.

## Method

For each candidate below: read the code, record what it does, what we would adopt, and what
we deliberately reject. The base-pipeline choice becomes an ADR (restructure plan D11).
Focus on:

- how reasoning data is generated (teacher vs on-policy vs rejection sampling);
- how format is enforced (constrained decoding vs imitation);
- RL details (reward shaping, entropy/KL control, curriculum, generations per prompt);
- reproducibility (pins, run manifests, seeds);
- evaluation hygiene (held-out splits, grader independence).

## Candidates

| Project | What to look at | Adoption interest |
|---|---|---|
| HuggingFace `trl` examples | SFT/DPO/GRPO trainers, completion-only masking | toolchain baseline |
| HuggingFace `alignment-handbook` | SFT/DPO recipes, masking, packing | masking + configs |
| `smol-course` | end-to-end small-LLM-model recipes | pedagogy, canaries |
| `Open-R1` | R1 reproduction: data pipeline + GRPO | reasoning RL loop |
| `open-instruct` / Tulu 3 | large-scale SFT + RLHF mix | data mixing, eval |
| `OpenThoughts` / `Bespoke-Stratos` | reasoning-data generation pipelines | agent training trace generation |
| `unsloth` notebooks | fast QLoRA, gemma/Qwen recipes | the current stack |
| `Axolotl` / `LLaMA-Factory` / `torchtune` | config-driven fine-tuning | alternatives |
| `verl` | RL for LLMs at scale | GRPO implementation |
| `Liquid4All/liquid-finetune` + Liquid LFM2.5 | first-party fine-tuning for small on-device LLM models: SFT/DPO/KTO/VLM/GRPO, QAT, GGUF export, llama.cpp serving | candidate small LLM model stack |

## Findings

One subsection per candidate, with the adopt/reject notes. (Phase 0b.)

### LFM2.5 and `liquid-finetune` (Liquid AI)

**Status:** candidate, recorded 2026-10-08, not yet trialed. Likely a stack we use during
fine-tuning; we will see how well or poorly it works.

**What it is.** LFM (`Liquid Foundation Model`) is Liquid AI's family of small, on-device LLM
models. The architecture is a non-transformer hybrid: gated short convolutions plus
grouped-query attention with QK layer norm. The current generation is **LFM2.5** (2026), with
dense sizes 230M, 350M, 1.2B, and 2.6B, an `8B-A1B` MoE, and vision-language, audio, encoder,
and retriever variants. There is no LFM2.6 generation — "2.6B" is a size.

**Why it is a candidate.** FT-D1 targets a small (2–4B) open LLM model trainable on one GPU.
LFM2.5-2.6B and LFM2.5-8B-A1B sit in that band. Liquid positions the family for agentic
tasks, tool calls, and data extraction, and recommends fine-tuning the small LLM models on
narrow use cases — the same shape as CAD-QA's agent training trace and submit tools. Small
LLM models are cheap to benchmark and fine-tune, so a canary is cheap.

**"Batteries-included" fine-tuning.** Interpreted: Liquid ships first-party fine-tuning
tooling rather than leaving the loop to third parties. `Liquid4All/liquid-finetune` covers
SFT, DPO, KTO, VLM SFT/DPO, GRPO/VLM GRPO, embedding, and ColBERT; runs on Ray Train,
Accelerate, and the HuggingFace Trainer; submits to local GPUs, SLURM, Modal, and KubeRay;
ships QAT profiles (including `gguf_q4_0`/`gguf_q8_0`) and GGUF export through a llama.cpp
checkout; and evaluates with lmms-eval. The intended loop is train on GPU (torch/vLLM) →
quantize to GGUF → serve on llama.cpp. `[assumed]` — we have not run it.

**Adoption interest.** Candidate base pipeline for Phase 3; could replace or complement the
current unsloth/trl gemma-4-E2B stack (FT-D1).

**Reject / cautions.**

- LFM2 is a non-transformer hybrid architecture, so the current unsloth/gemma toolchain does
  not transfer; adopting LFM means adopting `liquid-finetune` as well.
- `liquid-finetune` is young (56 commits, 219 stars at survey time) and depends on vLLM for
  GRPO rollouts; our own vLLM parity is already unverified (FT-D10).
- Any accuracy advantage on CAD-QA's multi-hop CAD reasoning is `[unverified]`.

**Verification.** None yet. First check: a canary SFT on the 1-hop slice with LFM2.5-1.2B or
LFM2.5-2.6B via `liquid-finetune`, evaluated on the `numpy` LLM harness.

## Resolved questions

_(none yet)_
