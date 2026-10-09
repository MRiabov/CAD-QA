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

**The format contract is shipped too (checked 2026-10-08).** `docs.liquid.ai/lfm/key-concepts/`
documents the LFM2 ChatML-like chat template, the native tool-call tokens
(`<|tool_call_start|>`/`<|tool_call_end|>`; LFM2 additionally `<|tool_list_*|>` and
`<|tool_response_*|>`), Pythonic-by-default calls with a JSON mode selected by a system-prompt
phrase, and reference generation settings; `docs.liquid.ai/lfm/fine-tuning/datasets` documents
the SFT (`messages`), DPO (`prompt`/`chosen`/`rejected`), GRPO (prompt-only), and tool-calling
dataset shapes that `liquid-finetune` validates. This makes the "batteries" claim concrete: the
tool/format contract is inherited, not hand-rolled — the exact axis where the Aug-2026 gemma
work burned effort (`development-context.md`, "Tool-call and answer-submission format churn").
It also sharpens the lock-in caution below: the CAD-QA `submit_*` answer tools must be
re-authored for these tokens and are not portable. (The docs briefly showed the repo as
`leap-finetune`; Liquid renamed it to `Liquid4All/liquid-finetune` on 2026-10-08.) LFM2/LFM2.5
checkpoints ship in `bfloat16`; 4-bit GGUF (including the QAD Q4_0 checkpoints, ~97% of BF16)
are separate deployment artifacts, so training is done on the bf16 base LLM model.

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

**Method and corpus choice for tool calling (2026).** A controlled study across six Qwen3 sizes
(0.6B–32B) compared SFT with LoRA, GRPO, and SFT-then-GRPO on three public tool-calling corpora
(`xLAM/APIGen 60k`, `ToolACE`, `Glaive-FC-v2`) [19]. SFT with LoRA was strongest in 15 of 18
in-distribution settings; GRPO and SFT-then-GRPO rarely beat it and sometimes fell below
zero-shot. Two findings matter here: **training-corpus choice moved accuracy by up to 55 points**,
as much as the method, and a **uniform mixture** was the best cross-dataset transfer default. It
also found **LoRA beat full fine-tuning** at 4B (88.0% vs 80.4% on `xLAM`), read as LoRA better
preserving pretrained tool use. **Caveat (contamination, raised 2026-10-08).** The base (Qwen3)
likely saw these public corpora during post-training — its own zero-shot xLAM scores are 66–78%,
and a dedicated contamination-free function-calling evaluation now exists [29] — so the
in-distribution magnitudes are upper bounds and this study is corroborating, not load-bearing.

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

### Building a proper SFT→RL system (2026)

**Status:** recorded 2026-10-08 from a targeted pass on RL post-training for small tool-calling
LLM models. Motivated by the question "will a raw SFT-then-GRPO run work here". The answer is
**no as-is**, and the fix is a system (`plans/oct-8/fine-tuning-system-plan.md`).

**GRPO needs something left to learn.** A controlled web-agent study [20] establishes a *null*:
GRPO adds no credible gain on tasks the supervised LLM model has already mastered, and 22 points
where the reward is reachable by sampling; the failure is learning-rate-gated at the weights. This
is the mechanism behind CAD-QA's recorded GRPO hop-2 collapse — a group whose rollouts all pass or
all fail has zero advantage, so the gradient is zero. Two results turn this into a rule: keep only
informative prompt groups (DAPO's dynamic sampling, [23]) and aim the training distribution at the
**pass-rate band around 0.5** (the ~0.25–0.75 intermediate-difficulty band maximizes reward
variance, which lower-bounds the reverse KL and thus learnability, [21]; 50% pass rate maximizes
reward entropy and group-filter survival, and a 1/8 or 7/8 group carries about half the per-rollout
information, [22]). Consequence: gate RL on a measured **pass@k** per difficulty tier.

**SFT+RL can fail outright, not just underperform.** BREAD [26] shows the SFT+RL recipe fails
completely when the expert's training traces are too difficult for the small LLM model to express,
or when the initialization has exponentially sparse rewards — both live risks on CAD-QA's hard
hops. The mitigations are a Bridge that rewrites hard teacher training traces into learnable
supervision [8] and a sampling gate that refuses to run RL on an unreachable tier.

**The reward scorer is the objective, so audit it.** `Where the Verifier Fails` [24] audits the
scorer rather than the LLM model over 307,420 verdicts: self-agreement on identical inputs ranges from
53.8% to 95.2%, and two configurations of the *same* library disagree on 49.9% of pairs; a numeric
cascade accepts off-by-one answers as a scale-dependent step function. This makes CAD-QA's three
divergent scorers (TA-A3) a P0 gate before RL, and the equivalent-answer metamorphic fixture the
right TA-A2 test. Reward hacking is the companion risk: hacking is often implicit and emerges
gradually before dominating [28], and a dense heuristic reward layered on a sparse verifiable one
is actively hacked unless the shaping is optimality-preserving (GRM/ADOPS, [27]).

**Sampling may beat RL at this scale.** SFT with sampling can outperform on-policy RL and
self-distillation on new-task generalization *and* prior-capability retention [25]. For a
single-GPU thesis this is the cheapest path: after SFT, sample k rollouts per prompt, keep the
correct ones, and fine-tune again (rejection-sampling SFT) — with GRPO reserved for tiers that
remain reachable-but-unmastered.

**Environment scaling is the lever (2025–2026).** The agent-RL literature reframes the scaling
target: RL needs verifiable interactive experience at a scale hand-built benchmarks cannot supply,
so **environments became the central object** and *scaling environments is how agent capability
scales* [30]. RLVE [31] shows expanding the **collection of verifiable environments** consistently
improves generalizable reasoning, while adding RL data within a fixed set does not (a single
environment already generates unbounded data), and that static data yields **vanishing learning
signal** when problems are too easy or too hard. In the same line, RL on synthesized tasks
transfers to a held-out benchmark only when the small LLM model is first SFT'd into the scaffold —
a **warm-start that is a readiness gate, not an accuracy target**, and over-doing it ossifies the
policy [32]. For CAD-QA this moves the center of gravity from the SFT mix to the **task environment
+ scorer** (a CAD-QA task generator with verifiable answers and the `run_code`/kernel tool
surface); SFT becomes a thin cold-start and the general external data becomes support/canary.

**Implication for CAD-QA.** Do not run a raw SFT→GRPO. Run **Stage 0** one-scorer + off-oracle
audit, **Stage 1** difficulty-aligned SFT with a Bridge for hard traces, **Stage 2** a pass@k
sampling gate that also produces rejection-sampling SFT data, and **Stage 3** GRPO with dynamic
sampling only on learnable tiers, in a sandbox, with rollout logging. `liquid-finetune` already
ships SFT, GRPO (TRL v1 `GRPOTrainer`), a `rewards/` callable registry, and an optional OpenEnv
multiturn block, so the whole loop stays in one stack on Modal.

### BenchCAD and the CAD benchmark saturation (2026)

**Status:** recorded 2026-10-09 from the public BenchCAD leaderboard and task docs. Detail and
citations: `research/2026-benchcad.md` (ref [33]).

BenchCAD (Zhang et al., 2026) has two lines on 17,900 execution-verified CadQuery programs,
graded deterministically with no LLM judge: **1.0** (four tasks, including the **Code QA**
comprehension task) and **2.0** (six reconstruction-only tasks — parts, assemblies, PCB
wiring). The repo's research note holds a full three-way comparison table. Four findings
matter for CAD-QA:

- **It now does comprehension, not only generation.** Besides Vision2Code and Code Edit, it has
  Vision QA and **Code QA** (CadQuery program + numeric question → number; 2,400 questions over
  200 parts; symmetric-ratio grading). Code QA is the CAD-QA base task shape, so the paper's
  "no open dataset" claim no longer holds.
- **Generation tasks are saturating; comprehension is not.** Re-graded Vision2Code voxel IoU is
  ~0.27, but provider-reported IoU with no access to CadQuery is now ~0.49–0.75 and agentic ~0.87–0.96 (a
  different metric and split, not re-graded). Code QA total is 0.80–0.84, with a Spatial
  Reasoning axis of 0.537–0.731 against a 0.42 blind baseline.
- **CAD-QA is differentiated by depth, not task shape.** Code QA is single-pass numeric lookup;
  CAD-QA is multi-hop, distractor-rich reasoning beyond numeric answers, over the CAD ontology,
  with automated graph-derived synthesis and a Reasoning hop curriculum / critical path. Use
  BenchCAD `qa_code` as an independent transfer benchmark (text-in, unsaturated), keep its
  programs out of training (contamination), and run frontier LLM models on the immutable CAD-QA
  hard slice to establish whether the multi-hop gap is still live.
- **2.0 is a different construct.** BenchCAD 2.0 is reconstruction-only (assemblies, PCB
  wiring) and adds no comprehension or multi-hop task, so it does not deepen the overlap.

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
19. Laskar, M.T.R., Fu, X.-Y. and Shashi Bhushan, T.N. (2026) 'SFT or RL for Tool-Calling Agents?
    A Controlled Study Across Data, Method, and Scale', arXiv:2609.17848.
    `arxiv.org/abs/2609.17848`. `[preprint]`. Note:
    `research/2026-sft-vs-rl-tool-calling.md`.
20. (2026) 'A Learning-Rate-Gated Failure of GRPO in a Small Language and Vision-Language Model <!-- dont-say: allow -->
    Web Agent: A Controlled Null and Its Mechanism', arXiv:2607.12640.
    `arxiv.org/html/2607.12640v1`. `[preprint]`. Note:
    `research/2026-grpo-null-web-agent.md`.
21. (2025) 'Online Difficulty Filtering for Reasoning Oriented Reinforcement Learning',
    arXiv:2504.03380. `arxiv.org/html/2504.03380v2`. `[preprint]`. Note:
    `research/2025-online-difficulty-filtering-rlvr.md`.
22. (2026) 'Rollout Pass-Rate Control: Steering Binary-Reward RL Toward Its Most Informative
    Regime', arXiv:2605.05112. `arxiv.org/pdf/2605.05112`. `[preprint]`. Note:
    `research/2026-rollout-pass-rate-control.md`.
23. Yu, Q. et al. (2025) 'DAPO: An Open-Source LLM Reinforcement Learning System at Scale',
    arXiv:2503.14476. `arxiv.org/abs/2503.14476`. `[preprint]`. Note:
    `research/2025-dapo-decoupled-clip-dynamic-sampling.md`.
24. Xin, E. (2026) 'Where the Verifier Fails: A Category-Level Audit of Reward Signals in RLVR', <!-- dont-say: allow -->
    arXiv:2609.01354. `arxiv.org/abs/2609.01354`. `[preprint]`. Note:
    `research/2026-where-the-verifier-fails.md`.
25. (2026) 'Finetuning with Sampling: SFT Learns Better Than You Think', arXiv:2610.02140.
    `arxiv.org/html/2610.02140`. `[preprint]`. Note: `research/2026-finetuning-with-sampling.md`.
26. (2025) 'BREAD: Branched Rollouts from Expert Anchors Bridge SFT & RL for Reasoning', NeurIPS
    2025 poster 118358; OpenReview `forum?id=NUDaln2vCe`. `[peer-reviewed]`. Note:
    `research/2025-bread-branched-rollouts.md`.
27. Forbes, G.C., Villalobos-Arias, L., Wang, J., Jhala, A. and Roberts, D.L. (2026) 'Preventing
    Process Reward Model Hacking When Training Large Language Models on Verifiable Rewards', <!-- dont-say: allow -->
    AAMAS 2026 (extended abstract). doi: `10.65109/BWFN6920`. `[workshop]`. Note:
    `research/2026-prm-reward-hacking-aamas.md`.
28. Wang, S., Pham, Q.H., Yin, F., Wang, X., Chen, J.Q., Durrett, G. and Ye, X. (2026) 'Detecting
    and Suppressing Reward Hacking with Gradient Fingerprints', COLM 2026. arXiv:2604.16242.
    `arxiv.org/pdf/2604.16242`. `[peer-reviewed]`. Note:
    `research/2026-gradient-fingerprints-reward-hacking.md`.
29. (2025) 'Towards Reliable Benchmarking: A Contamination Free, Controllable Evaluation Framework
    for Multi-step LLM Function Calling', arXiv:2509.26553; ICLR 2026.
    `arxiv.org/html/2509.26553v2`. `[peer-reviewed]`. Note:
    `research/2025-contamination-free-function-calling-eval.md`.
30. (2025) 'Scaling Environments for LLM Agents in the Era of Learning from Interaction: A Survey',
    arXiv:2511.09586. `arxiv.org/html/2511.09586v1`. `[preprint]`. Note:
    `research/2025-scaling-environments-llm-agents.md`.
31. (2025) 'RLVE: Scaling Up Reinforcement Learning for Language Models with Adaptive Verifiable
    Environments', arXiv:2511.07317. `arxiv.org/html/2511.07317v1`. `[preprint]`. Note:
    `research/2025-rlve-adaptive-verifiable-environments.md`.
32. (2026) 'Endless Terminals', arXiv:2601.16443. Cited by the environment-scaling survey [30].
    `[preprint]`. Note: `research/2026-endless-terminals-warm-start.md`.
33. Zhang, H., Liu, K., Chen, M., Li, L., Yang, S., Peng, C. and Chen, H. (2026) 'BenchCAD: A
    Comprehensive, Industry-Standard Benchmark for Programmatic CAD', arXiv:2605.10865.
    `arxiv.org/abs/2605.10865`. `[preprint]`. Note: `research/2026-benchcad.md`.

## Resolved questions

_(none yet)_
