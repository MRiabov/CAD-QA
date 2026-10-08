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
we deliberately reject. The base-pipeline choice becomes a recorded decision (restructure plan
D11); the current proposal is FT-D11 in `train-and-eval/fine-tuning/decisions.md`.
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

**Base rank does not predict fine-tuned rank.** Academic work finds that selecting a
base LLM model by size, zero-shot score, or small-subset tuned performance does not predict full
fine-tuning performance (the correlation can even be negative) [13], and that most base LLM
models degrade under fine-tuning while only a subset transfer well [14]. The practitioner
benchmarks agree: distil labs' 12-LLM-model, 8-task benchmark
(Dec 2025) [1] produced three different winners for three questions: best zero-shot — Qwen3-8B
(rank 1.75); best after fine-tuning — Qwen3-4B-Instruct-2507 (2.25); most tunable —
Llama-3.2-1B-Instruct (3.44), i.e. tunability inverts the size hierarchy. Their 4-LLM-model
MoE benchmark (Jul 2026) [3] nearly inverted the ordering: the worst zero-shot
(Nemotron-3-Nano-30B, base rank 3.43) was the most tunable (1.29) and tied for best after
fine-tuning (1.00). Their reading: base leaderboards are a poor guide to which base LLM model
to fine-tune; choose on deployment constraints and let training close the gap. The tunability
crown also moves between studies and dates: Llama-3.2-1B in the Dec 2025 12-LLM-model study
[1]; LFM2-350M, LFM2-1.2B, and LFM2.5-1.2B-Instruct in a Mar 2026 15-LLM-model study [2];
Nemotron-3-Nano-30B in the Jul 2026 MoE study [3].

**Family sets the start; training sets the finish.** In a tool-calling study (Aug 2026) [4],
base scores spread from 9.9% to 63.2% across families on the same tasks, but tuned scores
converge into a 90–98% band — "the starting point is a family property; the finishing point
mostly isn't." Fine-tuning moves accuracy far more than family choice: FunctionGemma 270M goes
9.90%→96.04% on shell commands [4]; LFM2.5-350M goes 61.4%→98.0% and beats its ~120B teacher
(97.03%) [4]; a fine-tuned Qwen3-4B matches or exceeds a GPT-OSS-120B teacher on 7 of 8 tasks
[1]. A separate AAAI 2026 workshop study reached 77.55% ToolBench pass with a single SFT epoch
on OPT-350M, above ChatGPT-CoT (26.00%) and ToolLLaMA-DFS (30.18%) [6].

**Per-family notes (2026 tool-calling).** Qwen3/Qwen3.5 has the strongest all-round
fine-tuned record and the best un-tuned tool-calling priors, and is eligible across 0.6B–9B
[4]. Llama 3.2 1B/3B is the most tunable from thin seed data [1]. Liquid LFM2/LFM2.5 ranks in
the top for tunability [2], and LFM2.5-350M posted the highest tuned tool-calling scores at
that size [4]. Gemma 3 is excluded from the tool-calling catalog at every size; only Gemma 4
E2B/E4B and FunctionGemma 270M qualify, with native function-call special tokens [4].
Phi-4-mini (~3.8B, MIT) has the strongest reasoning chain but slightly weaker raw tool mapping
[5]. The peer-reviewed study of the same question finds small LLM models improve from zero- to
few-shot and perform best with fine-tuning, with output-format adherence as the recurring
weakness [16]; BFCL is the shared benchmark behind these numbers [17], and its results show a
1–3B band clearly ahead of sub-1B [18].

**Reasoning preservation (SFT vs RL).** "RL Squeezes, SFT Expands" (ICLR 2026) [7] finds SFT
expands the reasoning graph while RL squeezes it into hub-like structures, and that the
two-stage SFT→RL ordering is best practice — directly relevant to CAD-QA's recorded GRPO
collapse, which is a squeeze symptom. "Learning What to Learn" (2026) [8] argues SFT should
acquire not-yet-mastered skills and RL should consolidate skills already partly accessible,
so difficulty must be aligned to the stage. Privileged on-policy distillation can degrade
thinking LLM models (up to 17% relative drop in avg@16) by suppressing self-correction at
high-entropy positions [9], so copying full teacher reasoning data is not obviously safe.

**The task itself is hard, independent of the base.** GeoGramBench (500 Program-to-Geometry
problems) found even frontier LLM models below 50% at the highest abstraction level, with
chain-of-thought not helping [10]; QueryCAD's CAD question-answering benchmark had GPT-4o
answer 44 of 111 [11]; and NoReGeo reports that fine-tuning alone does not confer native
geometric understanding [12]. For CAD-QA's hard (3+ hop) slice, a small base LLM model faces a
capability ceiling, so "little gain" may be the task rather than the tuning.

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

### References

External sources for this section, numbered to match the markers above. One summary note per
reference lives in [`research/`](research/README.md). Provenance tags follow the standard in
`research/README.md#sourcing-standards`: independent research is preferred, and a `[vendor]`
reference never stands alone for a load-bearing claim.

1. distil labs (2025) 'We Benchmarked 12 Small Language Models Across 8 Tasks to Find the Best
   Base LLM Model for Fine-Tuning', *distil labs blog*, 10 December.
   `distillabs.ai/blog/we-benchmarked-12-small-language-models-across-8-tasks`. `[vendor]`.
   Note: `research/2025-distil-labs-12-small-models-fine-tuning.md`.
2. distil labs (2026) 'What Small `Language Model` Is Best for Fine-Tuning', *distil labs
   blog*, 16 March. `distillabs.ai/blog/what-small-language-model-is-best-for-fine-tuning`.
   `[vendor]`. Note: `research/2026-distil-labs-15-small-models-fine-tuning.md`.
3. distil labs (2026) 'Does `Base-Model` Accuracy Predict Fine-Tuned Performance: A Mid-Size
   MoE Benchmark', *distil labs blog*, 16 July.
   `distillabs.ai/blog/does-base-model-accuracy-predict-fine-tuned-performance`. `[vendor]`.
   Note: `research/2026-distil-labs-base-vs-tuned-moe.md`.
4. distil labs (2026) 'Qwen vs Llama vs Gemma for Tool Calling', *distil labs learn*, 2
   August. `distillabs.ai/learn/qwen-vs-llama-vs-gemma-for-tool-calling`. `[vendor]`. Note:
   `research/2026-distil-labs-tool-calling-families.md`.
5. Yang, E.X. (2026) 'Phi-4-Mini vs Gemma 4 vs Qwen3-4B: Tool Calling', *ert.as*, 10 May,
   updated 7 August. `ertas.ai/blog/on-device-tool-calling-2026-qwen3-gemma4-phi4`. `[vendor]`.
   Note: `research/2026-ertas-on-device-tool-calling.md`.
6. Jhandi, P., Kazi, O., Subramanian, S. and Sendas, N. (2026) 'Small Language Models for
   Efficient Agentic Tool Calling: Outperforming Large Models with Targeted Fine-tuning',
   arXiv:2512.15943; AAAI 2026 workshop. `arxiv.org/abs/2512.15943`. `[workshop]`. Note:
   `research/2026-slm-agentic-tool-calling.md`.
7. Matsutani, K., Takashiro, S., Minegishi, G., Kojima, T., Iwasawa, Y. and Matsuo, Y. (2026)
   'RL Squeezes, SFT Expands: A Comparative Study of Reasoning LLMs', ICLR 2026.
   arXiv:2509.21128. `arxiv.org/abs/2509.21128`. `[peer-reviewed]`. Note:
   `research/2026-rl-squeezes-sft-expands.md`.
8. He, C., Zhang, R., Wang, Z. and Li, X. (2026) 'Learning What to Learn: Stage-Specific Data
   Sets for SFT-then-RL in Small `Language Model` Reasoning', arXiv:2606.04466.
   `arxiv.org/abs/2606.04466`. `[preprint]`. Note: `research/2026-learning-what-to-learn.md`.
9. Kaur, S., Ri, N., He, Y., Fowl, L.H. and Arora, S. (2026) 'Rethinking On-Policy
   Self-Distillation for Thinking Models', ICML 2026 FoGen workshop.
   `openreview.net/forum?id=VhCJItwQHn`. `[workshop]`. Note:
   `research/2026-privileged-on-policy-distillation.md`.
10. Luo, S., Zhu, Z., Yuan, Y., Yang, Y., Shan, L. and Wu, Y. (2025) 'GeoGramBench:
    Benchmarking the Geometric Program Reasoning in Modern LLMs', arXiv:2505.17653.
    `arxiv.org/abs/2505.17653`. `[preprint]`. Note:
    `research/2025-geogrambench-program-to-geometry.md`.
11. Kienle, C. et al. (2024) 'QueryCAD: Grounded Question Answering for CAD Models',
    arXiv:2409.08704. `arxiv.org/abs/2409.08704`. `[preprint]`. Note:
    `research/2024-querycad-cad-question-answering.md`.
12. Abdullaeva, I., Vasiliuk, A., Goncharova, E., Rahmatullaev, T., Ivan, Z., Kurkin, M. and
    Kuznetsov, A. (2026) 'NoReGeo: Non-Reasoning Geometry Benchmark', *Proceedings of the AAAI
    Conference on Artificial Intelligence*, 40(23), pp. 18901–18909. doi:
    `10.1609/aaai.v40i23.38960`. `[peer-reviewed]`. Note:
    `research/2026-noregeo-non-reasoning-geometry-benchmark.md`.
13. Lin, H., Huang, B., Ye, H., Chen, Q., Wang, Z., Li, S., Ma, J., Wan, X., Zou, J. and
    Liang, Y. (2024) 'Selecting Large `Language Model` to Fine-tune via Rectified Scaling Law',
    ICML 2024. arXiv:2402.02314. `arxiv.org/abs/2402.02314`. `[peer-reviewed]`. Note:
    `research/2024-selecting-llm-to-finetune-rectified-scaling-law.md`.
14. Choshen, L., Venezian, E., Don-Yehia, S., Slonim, N. and Katz, Y. (2022) 'Where to start?
    Analyzing the potential value of intermediate models', arXiv:2211.00107.
    `arxiv.org/abs/2211.00107`. `[preprint]`. Note:
    `research/2022-where-to-start-intermediate-models.md`.
15. Zeng, H., Hui, K., Zhuang, H., Qin, Z., Yue, Z., Zamani, H. and Alon, D. (2025) 'Can
    Pre-training Indicators Reliably Predict Fine-tuning Outcomes of LLMs?', arXiv:2504.12491.
    `arxiv.org/abs/2504.12491`. `[preprint]`. Note:
    `research/2025-pretraining-indicators-finetuning-outcomes.md`.
16. Kavathekar, I., Donakanti, R., Kumaraguru, P. and Vaidhyanathan, K. (2025) 'Small Models,
    Big Tasks: An Exploratory Empirical Study on Small Language Models for Function Calling',
    EASE 2025. doi: `10.1145/3756681.3757001`; arXiv:2504.19277. `arxiv.org/abs/2504.19277`.
    `[peer-reviewed]`. Note: `research/2025-small-models-big-tasks-function-calling.md`.
17. Patil, S.G., Mao, H., Ji, C.C.-J., Yan, F., Suresh, V., Stoica, I. and Gonzalez, J.E.
    (2025) 'The Berkeley Function Calling Leaderboard (BFCL): From Tool Use to Agentic
    Evaluation of Large Language Models', ICML 2025. `gorilla.cs.berkeley.edu/leaderboard`.
    `[peer-reviewed]`. Note: `research/2025-berkeley-function-calling-leaderboard.md`.
18. Haque, M.A., Rahman, F., Gupta, K.D., Shujaee, K. and George, R. (2025) 'TinyLLM:
    Evaluation and Optimization of Small Language Models for Agentic Tasks on Edge Devices',
    arXiv:2511.22138. `arxiv.org/abs/2511.22138`. `[preprint]`. Note:
    `research/2025-tinyllm-agentic-edge.md`.

## Resolved questions

_(none yet)_
