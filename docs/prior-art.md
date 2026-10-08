# Prior-art code mining

**Status:** seed, 2026-10-07; findings recorded 2026-10-08 (Phase 0b in progress). This doc
holds the method and candidates so the survey can be done deliberately (Phase 0b) rather than
by hand-rolling.

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

### External evidence on fine-tuning small LLM models (2025–2026)

**Status:** recorded 2026-10-08 from a literature and benchmark pass, not from our runs.
Motivated by the first CAD-QA passes with gemma-4-E2B and small Qwen LLM models looking like
"lots of effort, little gain".

**Base rank does not predict fine-tuned rank.** distil labs' 12-LLM-model, 8-task benchmark
(Dec 2025) produced three different winners for three questions: best zero-shot — Qwen3-8B
(rank 1.75); best after fine-tuning — Qwen3-4B-Instruct-2507 (2.25); most tunable —
Llama-3.2-1B-Instruct (3.44), i.e. tunability inverts the size hierarchy. Their 4-LLM-model
MoE benchmark (Jul 2026) nearly inverted the ordering: the worst zero-shot
(Nemotron-3-Nano-30B, base rank 3.43) was the most tunable (1.29) and tied for best after
fine-tuning (1.00). Their reading: base leaderboards are a poor guide to which base LLM model
to fine-tune; choose on deployment constraints and let training close the gap. The tunability
crown also moves between studies and dates: Llama-3.2-1B in the Dec 2025 12-LLM-model study;
LFM2-350M, LFM2-1.2B, and LFM2.5-1.2B-Instruct in a Mar 2026 15-LLM-model study;
Nemotron-3-Nano-30B in the Jul 2026 MoE study.

**Family sets the start; training sets the finish.** In a tool-calling study (Aug 2026), base
scores spread from 9.9% to 63.2% across families on the same tasks, but tuned scores converge
into a 90–98% band — "the starting point is a family property; the finishing point mostly
isn't." Fine-tuning moves accuracy far more than family choice: FunctionGemma 270M goes
9.90%→96.04% on shell commands; LFM2.5-350M goes 61.4%→98.0% and beats its ~120B teacher
(97.03%); a fine-tuned Qwen3-4B matches or exceeds a GPT-OSS-120B teacher on 7 of 8 tasks. A
separate AAAI 2026 workshop study reached 77.55% ToolBench pass with a single SFT epoch on
OPT-350M, above ChatGPT-CoT (26.00%) and ToolLLaMA-DFS (30.18%).

**Per-family notes (2026 tool-calling).** Qwen3/Qwen3.5 has the strongest all-round
fine-tuned record and the best un-tuned tool-calling priors, and is eligible across 0.6B–9B.
Llama 3.2 1B/3B is the most tunable from thin seed data. Liquid LFM2/LFM2.5 ranks in the top
for tunability, and LFM2.5-350M posted the highest tuned tool-calling scores at that size.
Gemma 3 is excluded from the tool-calling catalog at every size; only Gemma 4 E2B/E4B and
FunctionGemma 270M qualify, with native function-call special tokens. Phi-4-mini (~3.8B, MIT)
has the strongest reasoning chain but slightly weaker raw tool mapping.

**Reasoning preservation (SFT vs RL).** "RL Squeezes, SFT Expands" (ICLR 2026) finds SFT
expands the reasoning graph while RL squeezes it into hub-like structures, and that the
two-stage SFT→RL ordering is best practice — directly relevant to CAD-QA's recorded GRPO
collapse, which is a squeeze symptom. "Learning What to Learn" (2026) argues SFT should
acquire not-yet-mastered skills and RL should consolidate skills already partly accessible,
so difficulty must be aligned to the stage. Privileged on-policy distillation can degrade
thinking LLM models (up to 17% relative drop in avg@16) by suppressing self-correction at
high-entropy positions, so copying full teacher reasoning data is not obviously safe.

**The task itself is hard, independent of the base.** GeoGramBench (500 Program-to-Geometry
problems) found even frontier LLM models below 50% at the highest abstraction level, with
chain-of-thought not helping; QueryCAD's CAD question-answering benchmark had GPT-4o answer
44 of 111. For CAD-QA's hard (3+ hop) slice, a small base LLM model faces a capability
ceiling, so "little gain" may be the task rather than the tuning.

**Implication for CAD-QA.** The external evidence says a base-LLM-model swap should not be
expected to fix a recipe/data wall. Fix the recipe first (prompt-masked SFT, bounded epochs,
SFT→RL ordering, difficulty-aligned data, a teacher that clears the task) and then, if still
worth it, canary base LLM models with the recipe held fixed. Candidate bases, ranked by
external evidence and fit to a single-GPU 2–4B target: Qwen3-4B-Instruct-2507 (or the Qwen3.5
equivalent); LFM2.5-1.2B/2.6B; Llama-3.2-3B for thin seed data; Phi-4-mini for reasoning;
Gemma 4 E2B/E4B to stay in today's family with native tool tokens. Cheapest experiment: hold
the agent training trace set and recipe fixed, swap 3–4 bases, evaluate on the same held-out
1-hop slice, and report accuracy, entropy, and completion length — this separates the base
variable from the recipe variable.

Citations (external, dated): `distillabs.ai/learn/qwen-vs-llama-vs-gemma-for-tool-calling`
(Aug 2026); `distillabs.ai/blog/what-small-language-model-is-best-for-fine-tuning` (Mar 2026);
`distillabs.ai/blog/does-base-model-accuracy-predict-fine-tuned-performance` (Jul 2026);
`distillabs.ai/learn/does-base-model-accuracy-predict-fine-tuned-performance` (Aug 2026);
`distillabs.ai/blog/we-benchmarked-12-small-language-models-across-8-tasks` (Dec 2025);
`arxiv.org/abs/2512.15943` (AAAI 2026 workshop); `arxiv.org/abs/2509.21128` (ICLR 2026);
`arxiv.org/abs/2606.04466`; `arxiv.org/abs/2505.17653` (GeoGramBench); `ertas.ai` on-device
tool-calling (2026).

## Resolved questions

_(none yet)_
