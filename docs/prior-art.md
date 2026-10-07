# Prior-art code mining

**Status:** seed, 2026-10-07. Not yet executed. This doc holds the method and candidates so
the survey can be done deliberately (Phase 0b) rather than by hand-rolling.

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

| Source | What to look at | Adoption interest |
|---|---|---|
| HuggingFace `trl` examples | SFT/DPO/GRPO trainers, completion-only masking | toolchain baseline |
| HuggingFace `alignment-handbook` | SFT/DPO recipes, masking, packing | masking + configs |
| `smol-course` | end-to-end small-model recipes | pedagogy, canaries |
| `Open-R1` | R1 reproduction: data pipeline + GRPO | reasoning RL loop |
| `open-instruct` / Tulu 3 | large-scale SFT + RLHF mix | data mixing, eval |
| `OpenThoughts` / `Bespoke-Stratos` | reasoning-data generation pipelines | trace generation |
| `unsloth` notebooks | fast QLoRA, gemma/Qwen recipes | the current stack |
| `Axolotl` / `LLaMA-Factory` / `torchtune` | config-driven fine-tuning | alternatives |
| `verl` | RL for LLMs at scale | GRPO implementation |

## Findings

_(to be filled by the Phase 0b survey — one subsection per adopted source, with
`path::symbol`-style references and the adopt/reject notes)_

## Resolved questions

_(none yet)_
