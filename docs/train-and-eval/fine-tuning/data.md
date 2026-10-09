# Fine-tuning — data and schedule

**Status:** active, 2026-10-09. Part of four fine-tuning/evaluation docs: this doc (data + schedule),
`training.md`, `system.md`, and `../evaluation/plan.md`.

**This doc owns — which data we train on and when:** dataset roles, candidate external datasets, the
mix recipe, training order / curriculum / SFT-vs-RL scheduling, licensing and contamination policy,
and the CAD-QA task dataset.

**The architecture doc owns — how we train the LLM model:**
`training.md` (base LLM model and stack, cookbook-first execution, capability
preservation, the training stages, hardware/budget, and the surviving-code boundary).

**The system doc owns — the post-training loop and data preparation:**
`system.md` (the Query verifier → SFT → pass@k gate → RL/distillation loop, and the
`TrainingExample` record, converter, and the ingest/normalize/quality/dedup/sample stages).

**The evaluation doc owns — the harness and scoring:**
`../evaluation/plan.md` (LLM harness and modes, tool-call surface, the scorer, the evaluation-dataset
procedure, grading reconciliation, judge independence, baselines).

**Shared interfaces, single-sourced:**

- **Format contract** (Liquid `messages` SFT JSONL) — owned by the architecture doc.
- **`TrainingExample` + converter** — owned by the system doc.
- **Evaluation datasets** — the procedure is owned by the evaluation doc; the dataset rows are produced and
  held here.
- **H1/H2** — owned by the architecture doc; the mixes they test are defined here (§3).

**Explicitly out of scope for now.** The CAD-QA **reasoning-hop dataset** itself (the internal
teacher-sampling of agent training traces from immutable CAD-QA dataset rows, step B2 in
`pipeline/02-teacher-sampling.md`). This doc defines a
**dataset** and its **contract** (§6), but does not plan its generation. That is the
separate decision owed under FT-D11 (`decisions.md`) and
Phase 3 of `../../development-plan.md`.

**Related docs.** `../../prior-art.md` (external evidence, refs [1]–[32]);
`../../PRD.md` (research contract); `decisions.md`
(FT-D* decisions).

---

## 1. Dataset roles (taxonomy)

Every training example is tagged with exactly one **dataset role** (glossary). Roles exist because
they are mixed at fixed ratios and evaluated separately. The external roles
(`emit_our_tool_call_format`, `run_the_tool_call_loop`, `preserve_general_math_and_code_reasoning`,
`expose_general_python_code`, `expose_cadquery_programs`) are
**support**: a tool-schema cold-start and general-task diversity. They are not the
scaling lever — the task environment + scorer is (`system.md` §0) — so collect them
selectively, not blindly.

| DatasetRole | What it teaches | Internal / external | Priority |
|---|---|---|---|
| `emit_our_tool_call_format` | emit our `submit_*` tool calls in the LLM model's native format | external | P0 |
| `run_the_tool_call_loop` | multi-turn tool loop (call → result → call → answer), incl. `run_code` round-trip | external | P0/P1 |
| `preserve_general_math_and_code_reasoning` | general software / math / engineering reasoning tasks, replayed to prevent reasoning collapse | external | P1 |
| `expose_general_python_code` | general Python / coding exposure | external | P1/P2 |
| `expose_cadquery_programs` | CadQuery / 3D representation exposure so the base LLM model is not CAD-blind | external | P1/P2 |
| `learn_the_cadqa_task` | the CAD-QA task itself: prompt → `submit_*` with hop reasoning | internal (**§6 only defines the dataset**) | P0 (separate plan) |
| evaluation dataset | never trained on; used to detect regression | external + internal | P0 |

**Rule:** evaluation-dataset rows must be **hashed and excluded** from every training mix. Any
overlap is contamination (`No silent data loss` and held-out hygiene).

---

## 2. Candidate external datasets

Sizes, schemas, and licenses are from the Hub cards at survey time (2026-10-08) and must be
**re-verified and pinned by revision hash** before use. Names in this 2026 landscape should be
treated as candidates, not commitments.

**Freshness policy (prefer current).** Prefer the **most recent** sources (2026); treat 2025 as
acceptable only when it is still the state of the art; use 2024-and-earlier only as
reference/comparison corpora. The reason is not only schema drift: much of the recent capability
gain in open LLM models comes from **higher-quality data becoming available** — new open corpora
and distillations of newer closed LLM models — so the newest data tends to carry the newest teacher
behavior and formats. Record each candidate's **release / last-updated date** beside its pinned
revision hash (the hash encodes the date), and re-check for a newer version at freeze time. Age
alone is not disqualifying — `xLAM/APIGen` is still the canonical reference and is used by the
2026 controlled study below — but a 2024 corpus should not be the primary mix.

**Fresh evidence (2026).**

- "SFT or RL for Tool-Calling Agents? A Controlled Study Across Data, Method, and Scale"
  (arXiv:2609.17848, Sep 2026) trains Qwen3 0.6B–32B on `xLAM/APIGen 60k`, `ToolACE`, and
  `Glaive-FC-v2`. It finds **SFT+LoRA strongest in 15/18** in-distribution settings; **corpus
  choice changes accuracy by up to 55 points**; a **uniform mixture** is the best transfer default;
  and **LoRA beats full fine-tuning** (it preserves pretrained tool use). Direct support for our
  SFT+LoRA, mixture-first plan and H1. **Caveat (contamination):** the Qwen3 base likely saw these
  public corpora in post-training (zero-shot xLAM is 66–78%), so the in-distribution magnitudes are
  upper bounds and the `emit_our_tool_call_format` evaluation dataset must not be a held-out slice of them — see
  `../../research/2026-sft-vs-rl-tool-calling.md` and the evaluation plan §6.
- ACL 2026 "Skill-Aware Data Selection and Fine-Tuning for Data-Efficient Reasoning Distillation":
  1,000 selected traces beat random SFT from a 100K corpus. Supports small, quality-filtered sets.

### 2.1 Format + tool-calling (`emit_our_tool_call_format`)

| Dataset | Date | Size | Shape | License | Adopt/reject |
|---|---|---|---|---|---|
| `ByteDance/ToolACE` | 2025 | ~11k conversations, 26.5k APIs | multi-turn, parallel calls, refusals | see card | **Adopt** as the primary 2025+ format set; multi-turn + refusal coverage |
| `DeepNLP/Agent-Function-Calling-Open-Dataset` | 2026-01 | large | real user requests: messages + tools + calls + results | see card | **Adopt** a slice; real-request distribution |
| `NousResearch/hermes-function-calling-v1` | 2025-01 | ~10k / 5 configs | multi-turn + JSON mode | Apache-2.0 | **Adopt** a slice |
| `Salesforce/xlam-function-calling-60k` | 2024-06 | 60k (56.4k after dedup) | single-turn, parallel calls | CC-BY-4.0 | **Reference corpus** (kept; the 2026 controlled study uses it) |
| Glaive-FC-v2 | 2023 | 113k (46.2k after dedup) | conversational + calls | see card | **Reference only**; 58.5% near-duplicates per the 2026 study |
| `bebechien/SimpleToolCalling` (TRL example) | 2024 | tiny | user + tool | permissive | smoke/debug fixture only |

### 2.2 Tool-call loops (`run_the_tool_call_loop`)

| Dataset | Date | Size | Shape | License | Adopt/reject |
|---|---|---|---|---|---|
| `open-thoughts/OpenThoughts-Agent-SFT-{1K,3.16K,10K,…}` | 2026 | ladder 316→100K | task + agent trajectory (`terminus-2`) | Apache-2.0 | **Adopt**; pick a rung to match the first run's budget |
| `RESMP-DEV/Fable-GPT-5.5-Distillation-Traces` | 2026 | 9.06M | unified 2026 corpus: agentic coding, reasoning, tool use, preference | see card | **Adopt with sampling**; one-stop but huge, mixed provenance |
| `nvidia/Open-SWE-Traces` | 2026 | 207k | multilingual software-engineering agent trajectories | permissive (MIT/Apache/BSD filtered) | **P1**; engineering-flavored, not CAD |
| `AlicanKiraz0/Agentic-Chain-of-Thought-Coding-SFT-Dataset` | 2026 | 429 | Minimax-M2-distilled coding CoT + tool calls | MIT | **P2**; tiny but license-clean |
| `Glint-Research/Fable-5-traces` | 2026 | ~4.5k | Claude Fable 5 coding-agent traces | AGPL-3.0 | **Adopt with caution** — see §5 |
| `spitfire4794/Fable-5-traces` | 2026 | 4,665 | Pi sessions | AGPL-3.0 | shorter-list; same family |
| `cfahlgren1/Fable-5-traces` | 2026 | 115 | raw logs | AGPL-3.0 | **Reject** for training |

### 2.3 General math / code reasoning (`preserve_general_math_and_code_reasoning`)

| Dataset | Date | Size | Shape | License | Adopt/reject |
|---|---|---|---|---|---|
| `open-thoughts/OpenThoughts-114k` | 2025 | 114k | DeepSeek-R1-distilled math/science/code/puzzles | Apache-2.0 | **Adopt**, sample/down-filter; fully open recipe |
| `bespokelabs/Bespoke-Stratos-17k` | 2025-01 | 17k | R1 reasoning traces | Apache-2.0 | **Adopt**; small, high-quality |
| `nvidia/OpenMathReasoning` | 2025-05 | 5.68M | math CoT | permissive | **P1**; scale only if H2 holds |
| `open-r1/OpenR1-Math-220k` | 2025-02 | 220k | math CoT | permissive | **P1** |
| `TeichAI/Claude-Opus-4.6-Reasoning-887x` etc. | 2026-04 | ~2k | Claude reasoning traces | see cards | **Adopt with caution**; TeichAI 4B recipe is a close precedent (single epoch, mixed tool/non-tool) |
| `nohurry/Opus-4.6-Reasoning-3000x-filtered` | 2026-03 | ~2.3k | filtered Opus 4.6 reasoning | see card | **P1** |
| `Jackrong/Qwen3.5-reasoning-700x` | 2026-03 | ~700 | curated step-by-step reasoning | see card | **P2** |
| `PrimeIntellect/NuminaMath` | 2024 | 860k | math problems (+ solutions) | Apache-2.0 | **Reference**; pre-2025 |

**Caution from prior art (ref [9]):** copying full teacher reasoning can *suppress* the student's
self-correction at high-entropy positions (up to 17% relative `avg@16` drop). So
reasoning-distill data is not automatically safe: prefer **filtered/verified** traces, cap their
weight, and measure the evaluation dataset.

### 2.4 Anti-forgetting (the general tasks)

There is **no dedicated replay role** (FT-D18): at SFT there is no prior checkpoint to replay from, so
prior ability is anchored by the **diverse general mix** — general code (`expose_general_python_code`),
math/code reasoning (`preserve_general_math_and_code_reasoning`), and CAD (`expose_cadquery_programs`)
— not by a replay buffer. A real replay buffer is a later (RL/distillation) concept, not an SFT role.

**Ratio:** the general tasks are the majority of every mix (≈70%); the xLAM precedent (`xLAM` §3.5)
reports 20–30% general instruction data as an anti-forgetting floor.

### 2.5 Python / general coding priming (`expose_general_python_code`)

Short-term coding exposure so the base is not code-naive. Prefer Python + reasoning traces.

| Dataset | Date | Size | Shape | License | Adopt/reject |
|---|---|---|---|---|---|
| `allenai/Dolci-Think-SFT-Python` | 2025-12 | 466k | Python prompts + R1 reasoning traces | ODC-BY-1.0 | **Adopt**; reasoning-bearing Python, permissive |
| `KodCode/KodCode-V1-SFT-R1` | 2025-03 | 483k | verifiable coding Q + R1 CoT | Apache-2.0 | **Adopt** a slice; verifiable, ACL 2025 |
| `nvidia/OpenCodeReasoning` | 2025 | 753k | code reasoning traces | see card | **P1** |
| `KodCode/KodCode-V1` | 2025-03 | 487k | Q + solution + unit tests | Apache-2.0 | **P1**; RL-ready tests |

### 2.6 3D and CAD priming (`expose_cadquery_programs`)

The earlier "no large public CadQuery corpus" claim was **wrong** — there are several. This role
exists so the base LLM model has seen 3D/CAD before CAD-QA — **representation priming, not a
CadQuery-generation capability**.

| Dataset | Date | Size | Shape | License | Adopt/reject |
|---|---|---|---|---|---|
| `CADCODER/GenCAD-Code` | 2025 | 163k | image → CadQuery Python pairs | Apache-2.0 (repo) | **P2** — image input is not useful for a text-only base today |
| `BenchCAD/BenchCAD` (`code_gen`) | 2026 | 17.9k | CadQuery GT code + 5 renders, 106 part families | CC-BY-4.0 | **Adopt**; execution-verified synthetic CadQuery — preferred corpus (keep out of the transfer eval) |
| `ricemonster/NeurIPS11092` | 2025 | 170k | text → CadQuery (Text2CAD via Gemini 2.0 Flash) | see card | **P2 / caution** — third-party generation, unverified; execution-filter or drop (FT-D17) |
| `azizzjr/qwen3-32b-fusion360-98k-v2` | 2025-07 | 98k | Fusion360 code | see card | **P2**; Fusion360, not CadQuery |
| `MRiabov/IntersectionQA-15K` / `-90K` | 2026-04 | 15k / 90k | 3D intersection QA (owner's own) | see card | **Exclude (`[unknown]`)** — same area as CAD-QA and likely an unfinished release, like the benchmark; not a training candidate |
| `sanjuhs/cadforge-cadquery-agentic-traces` | 2026-04 | 174 | agentic CadQuery traces | see card | **Study**; tiny, but exactly our agentic shape |
| `hhllzz/surprise-3d` (SURPRISE3D) | 2025-07 | 190k | 3D-scene spatial-reasoning VQA | MIT | **P2**; scene-level, image/point-cloud grounded |
| PointLLM / Cap3D captions | 2023 | 730k | object point cloud + text instructions | see card | **P2**; object-level |
| `hiyouga/geometry3k` | 2025 | 3k | image geometry VQA | MIT | **P2**; image-based |
| `LiAuto-DSR/GeoGramBench` | 2025 | 500 | program-to-geometry benchmark | see card | **Eval only**; already ref [10] |

**Contamination rule:** `expose_cadquery_programs` must not leak the CAD-QA held-out programs or their generating
corpus. Any same-area set (including an owner-authored one) carries a higher leakage risk: run the
quality gate (`system.md` §7) and a held-out overlap check before mixing.

**Verification rule (FT-D17).** An SFT corpus is either **rejection-sampled by us** (teacher
`deepseek-v4-flash`, FT-D2 — keep only traces the Query verifier accepts) or **execution-verified** before
it enters a mix. Unverified third-party generation teaches the generating LLM model's errors and is
P2/caution (`NeurIPS11092`, Gemini 2.0 Flash, 2025).

**Where BenchCAD steps in.** `BenchCAD/BenchCAD` `code_gen` feeds the **text2CAD + edits** third
(execution-verified CadQuery), while BenchCAD `qa_code` (and `edit_code`) is the **H3 transfer** target
(`../evaluation/plan.md` §5.1). Because it is both a training corpus and the transfer benchmark, either
keep the transfer split disjoint from the training rows or drop `code_gen` from training and use another
CadQuery corpus.

**Deferred (vision):** image→CAD and point-cloud/3D-vision sets (`CADCODER/GenCAD-Code`,
`hhllzz/surprise-3d`, PointLLM/Cap3D, `hiyouga/geometry3k`) are **P2** — the primary base LLM model
is text-only, so image and point-cloud inputs are not usable until a multimodal training stage.

**Excluded:** `MRiabov/IntersectionQA` is the owner's own same-area release, but its outcome is
`[unknown]` (likely unfinished, like CAD-QA). It is not a training candidate unless it is later
found to be clean and non-overlapping.

---

## 3. The mix recipe

**General tasks (the "general" share).** Split into equal thirds, so "general" is not a single blob:
**coding agent** (⅓; general code + multi-turn tool loops — `expose_general_python_code`,
`run_the_tool_call_loop`, and our tool format via `emit_our_tool_call_format` in the first run),
**3D math** (⅓; `preserve_general_math_and_code_reasoning`), and **text2CAD + edits** (⅓;
`expose_cadquery_programs` — text→CadQuery generation and edit tasks).

| Mix | Role weights | Purpose |
|---|---|---|
| `mixed_dataset_general_and_easy_cadqa` (first run) | 70% general (⅓ coding agent, ⅓ 3D math, ⅓ text2CAD + edits), 30% low-hop `learn_the_cadqa_task` (rejection-sampled) | first run: format + easy task, cheapest signal |
| `mixed_dataset_full_cadqa_training` (primary) | 50% general (same thirds), 50% `learn_the_cadqa_task` (progressively more complex) | test H2, the thesis number; **no separate `emit_our_tool_call_format`** — the format is carried by `learn_the_cadqa_task`. The task share is the **curriculum** — rows ordered by increasing complexity (the 0→1→2→3→5 hop ladder), not a flat sample |

Rationale and tradeoffs:

- **Format before reasoning.** If the LLM model cannot emit a valid `submit_*` call, accuracy is zero
  regardless of reasoning. Prove H1 first on the cheapest possible data.
- **Mix corpora; corpus choice matters.** The 2026 controlled study (arXiv:2609.17848) found
  corpus choice swings tool-calling accuracy by up to 55 points and a uniform mixture is the best
  transfer default — so `mixed_dataset_general_and_easy_cadqa` blends sources rather than betting on one.
  (Magnitude is contamination-affected; see §2.)
- **The general tasks are not optional.** A diverse general mix (code + math + CAD) is the
  anti-forgetting mechanism (FT-D18); a LoRA-only setting still risks regression without it.
- **`learn_the_cadqa_task` weight is a placeholder.** Until its generation is planned (§6), `mixed_dataset_full_cadqa_training` is not
  runnable; `mixed_dataset_general_and_easy_cadqa` is runnable immediately from public data and is the first GPU spend.
- **Sample, don't ingest wholesale.** Cap each External dataset (e.g. 5–20k examples) by quality score and
  dedup; xLAM and TeichAI both report that quality beats quantity at this size. **Pull a subset,
  not the whole corpus** — stream or select shards/rows at the pinned revision instead of
  downloading a multi-million-row dataset to keep a few thousand; record the selection rule and
  seed so the manifest reproduces it.

### 3.1 Corpus size targets

Aim **~10,000 examples (band 5,000–20,000)** for the primary run, with a **~1,000–2,000 first run**.
The binding constraint is the internal `learn_the_cadqa_task` set, not the external data: it is generated by
teacher API calls and must cover every Answer format × hop, so it sets the budget and the wall
clock. **≥1,000 verified traces** is the target; the current ~300 is too few — `json`/`number`
coverage was 0.

| Training stage | Total | General (⅓ coding agent · ⅓ 3D math · ⅓ text2CAD + edits) | `learn_the_cadqa_task` |
|---|---|---|---|
| First run (`mixed_dataset_general_and_easy_cadqa`) | 1,000–2,000 | 700–1,400 | 300–600 |
| Primary (`mixed_dataset_full_cadqa_training`) | 10,000 (5k–20k) | 5,000 | 5,000 |

- **Why not larger.** Curated small sets match or beat large ones at this size: ACL 2026 (1,000
  selected traces beat random SFT from 100k), TeichAI (~4k), AnkitAI/Parable (~4.4k), and `ToolACE`
  9.7k competed with `xLAM` 56k in the 2026 controlled study. The gain is coverage + quality, not
  raw count.
- **Scale is GPU-cheap, data-expensive.** At `SEQ=6144`, 10k examples is roughly 10–30M tokens; a
  single epoch on a 2.6B base is hours on a 24 GB card. The teacher API budget is the real ceiling.
- **Coverage beats volume.** Every Answer format and hop bucket must clear a floor; a format with
  zero traces cannot be learned (the recorded task-corpus coverage defect). Enforce a per-format minimum,
  not just a total.

---

## 4. Order and curriculum of training

This section owns the *order* the roles and difficulty are presented in. The architecture doc owns
the mechanics (epochs, mixing implementation).

- **Two training phases.** SFT runs as **phase 1 (refocus on coding + easy tasks)**: the base already
  trains on code, so coding/Python is not new — phase 1 refocuses it (`expose_general_python_code`),
  adds a little text-to-CadQuery (`expose_cadquery_programs`), and carries a simple slice of our tasks
  (e.g. hop 0, `learn_the_cadqa_task`); then **phase 2 (CAD-QA task + preserve)**: CAD is new, so
  `mixed_dataset_full_cadqa_training` adds `learn_the_cadqa_task` + CAD at scale, with
  the general tasks (`preserve_general_math_and_code_reasoning`, `expose_*`) as the anchor.
  Shape and rationale: `system.md` §2; eval cadence: `../evaluation/plan.md` §6.
- **Phase-2-only fallback.** If phase 1 shows no measured phase-end gain, drop it and run one SFT Training stage
  over `mixed_dataset_full_cadqa_training` (the cookbook default); the 2-phase pipeline must earn its
  place on the phase-end eval (ref [19]). The `mixed_dataset_general_and_easy_cadqa` first run is the
  format gate before either phase.
- **Difficulty-aligned rows.** Order or interleave the `learn_the_cadqa_task` rows by Reasoning hop count
  (the `0→1→2→3→5` ladder in `../../development-plan.md` Phase 3 and the teacher quotas in
  FT-02-D1). Do not front-load the hard slice.
- **The general tasks are interleaved, not appended.** Keep the general-task share in every phase, so
  general ability is anchored throughout, not restored at the end.
- **Cap `preserve_general_math_and_code_reasoning` early.** Per prior-art ref [9], do not let teacher reasoning dominate
  before format and the task itself are established.
- **Text-to-CadQuery exposure is representation, not generation.** We do not need the LLM model to
  *write* CadQuery well; a little text-to-CadQuery (`expose_cadquery_programs`) teaches syntax and
  semantics. Whether that transfer reaches *reading/reasoning* over a given CadQuery program is the H2
  hypothesis, not a given — A/B it on the phase-end eval.
- **Sequencing must earn its place.** Sequential fine-tuning spans two Training stages: higher forgetting
  risk and cost, and the 2026 controlled study (ref [19]) found a single SFT training stage strongest with
  no consistent gain from a second. Keep the general tasks in *every* phase and advance only
  on a measured phase-end gain (§4.1).
- **SFT → RL/DPO only after SFT is measured (P2).** The recorded ordering ("RL squeezes, SFT
  expands", prior-art refs [7]/[8]; FT-D8) is a second training stage, deferred until the SFT number is
  real.

### 4.1 Advancement gate

Advance to the next difficulty tier (the hop ladder / `difficulty_bucket`) only on a **measured,
held-out** pass rate — never on training loss, and never on the training rows (overfit). The
mechanism differs by training stage:

- **SFT: a data decision, not a guarantee.** SFT trains by imitation, so it cannot guarantee
  mastery of a tier; but per-hop held-out accuracy at checkpoints can drive a *data* decision —
  add the next hop's `learn_the_cadqa_task` rows only once the current hop clears the gate. A held-out floor
  of ~80% is a reasonable default.
- **RL: a true on-policy gate (P2).** Only RL can enforce advancement on the LLM model's own
  rollouts. Use a **band, not a floor**: GRPO needs reward variance, so once a tier is ~80%+
  correct most groups are fully correct and the gradient collapses. CAD-QA's recorded GRPO
  hop-2 collapse is a version of this. Advance when the tier is **saturated** (pass ≥ ~80% and no
  learning signal remains) or sits in the learnable band (~30–70%); never run RL on an all-correct
  tier.
- **Why gates exist.** The tiers exist because pass rate, not epoch, is the real progress signal:
  a tier that never clears stalls the ladder and must be recorded, not skipped.
- **Prerequisite.** A tier needs enough rows to train *and* a held-out slice to measure; a tier
  too thin to gate cannot be advanced safely. The per-tier held-out slice is owned by
  `../evaluation/plan.md`; the ordering and the gate live here.

---

## 5. Governance: registry, licensing, and contamination

- **Registry.** Every dataset has id, revision hash, license, dataset role, size, and field mapping.
  A dataset without a pinned revision does not enter.
- **Contamination policy.** CAD-QA held-out rows and the evaluation datasets are hard-excluded; any
  evaluation-dataset id appearing in `train` is a hard failure. The mechanics (quality gate, near-dedup,
  hash-exclusion, no-silent-loss) live in `system.md` §7.
- **Licensing and provenance.** Two concerns, often conflated:
  - **AGPL-3.0** (the Fable agent training trace sets) is copyleft, **not a research restriction** — training on
    it is fine. Its obligations attach to **distribution** of the material or a derivative. That
    matters only if we redistribute those rows (or a work held to derive from them; whether trained
    weights are a derivative is legally unsettled).
  - **Provider terms** on commercial-assistant outputs (Claude/Fable, GPT-5.5, Opus) — the sets'
    cards warn that provider terms may restrict downstream training/distillation. In practice this
    is widely ignored: large numbers of open fine-tunes train on these traces with no attribution
    or enforcement, so for a non-commercial thesis the practical risk is low — a formal/policy
    consideration, not a blocker.
  Defensible posture, in order:
  1. Prefer permissively licensed, fully-open sources (`OpenThoughts`, `Bespoke-Stratos`, `xLAM`,
     `Hermes`) for the primary mix.
  2. Record each External dataset's license and provider terms in the registry and the LLM model
     card, and keep AGPL / commercial agent training trace rows separable so a redistribution or a
     venue objection is tractable.
  3. If commercial agent training traces are mixed in, disclose it in the manuscript's data statement.

---

## 6. The CAD-QA task dataset

The CAD-QA task dataset (`learn_the_cadqa_task`) is the CAD-QA task itself: one row of an immutable
CAD-QA dataset file → a prompt plus a typed `submit_*` answer, with hop reasoning. This doc fixes
only the dataset:

- **This is the comprehension corpus.** CAD-QA *is* the program → question (comprehension) data;
  there is no large public equivalent, which is the dataset contribution. That is why the external
  `expose_cadquery_programs` sets are generation-only proxies, and this dataset — not they — carries the task signal.
- **Producer (not planned here):** the Phase 3 replacement for step B2 teacher sampling, owed
  under FT-D11.
- **Contract:** each example is a `TrainingExample` with `dataset_role=learn_the_cadqa_task`, `answer_format` set,
  `reasoning_hop_count` set, and (once rendered) a `submit_*` tool call.
- **Coverage requirement:** every Answer format must have at least one agent training trace, because a format the
  teacher never produces cannot be learned (the `json`/`number` zero-coverage defect in
  `pipeline/02-teacher-sampling.md`).
- **Contamination:** CAD-QA held-out rows are hard-excluded (§5).
- **Priority:** P0, but a separate plan.

---

## 7. P0 / P1 / P2 (data)

| Item | Tier | Rationale |
|---|---|---|
| `TrainingExample` record + Liquid `messages` JSONL converter (owned by the system plan) | **P0** | the only custom data code we should need; cookbook-compatible |
| Registry with pinned revisions, licenses, and dates | **P0** | reproducibility, the license audit, and the 2025+ freshness policy |
| `mixed_dataset_general_and_easy_cadqa` data build (general tasks + low-hop `learn_the_cadqa_task`) | **P0** | feeds the first run |
| Contamination + dedup pass against CAD-QA held-out and evaluation datasets | **P0** | held-out hygiene; a leak invalidates the thesis number |
| General-task curation (code + math + CAD, ≈70%) | **P0** | anti-forgetting anchor (FT-D18) |
| **`learn_the_cadqa_task` generation plan** | **P0, separate** | the thesis needs it; explicitly not in this doc |
| Permissive reasoning mix (`OpenThoughts`/`Bespoke`) | **P1** | tests H2 without license risk |
| `run_the_tool_call_loop` / `run_code` data (`OpenThoughts-Agent`) | **P1** | needed for the primary `numpy` LLM harness behaviour |
| Staged training order (`mixed_dataset_general_and_easy_cadqa` → `mixed_dataset_full_cadqa_training`) | **P1** | tests H1→H2 ordering if the mixed baseline underperforms |
| Dedup/contamination automation | **P1** | manual hashing works for the first run; automate before `mixed_dataset_full_cadqa_training` |
| Commercial agent training trace mix (Fable/Opus/TeichAI) | **P1** | strong signal; accepted in the thesis (§8); permissive mixes remain the default |
| `expose_general_python_code` Python/coding priming | **P1/P2** | cheap code exposure; measure the evaluation datasets |
| `expose_cadquery_programs` text→CadQuery (`BenchCAD` code_gen, execution-verified) | **P1** | so the base is not 3D-blind; keep it out of the transfer eval |
| `expose_cadquery_programs` image→CAD / point-cloud priming (`GenCAD-Code`, `SURPRISE3D`, PointLLM) | **P2** | not usable with a text-only base today |
| Math/reasoning scale-up (`OpenMathReasoning`, `NuminaMath`) | **P2** | scale only if H2 holds |
| ≥10k CAD-QA Dataset release tier | **P2** | already P2 in `../../development-plan.md` |

---

## 8. Decisions (data)

**Resolved:**

- **Commercial agent training trace policy.** Accepted: agent training traces distilled from commercial models (Fable/Opus/TeichAI) may be
  used in the published thesis, and not only as an ablation — the work is non-commercial research and
  the External dataset is open. Permissive mixes remain the default; record the originating LLM model and
  license per sample so the mix can be isolated if a venue objects.
- **`preserve_general_math_and_code_reasoning` earns a place.** It is a capability-preservation role
  (anti-collapse of general reasoning), not an ablation; content is general software / math /
  engineering tasks, and is part of the general-task mix that anchors prior ability (FT-D18).

**Still to make:**

1. **Mix ratios.** The §3 numbers are a starting hypothesis, not a result.
2. **Order of training.** Mixed single training stage (default) vs staged format→full. Decide after the
   `mixed_dataset_general_and_easy_cadqa` first run.
3. **CAD-QA task dataset ownership.** Who plans the internal teacher-sampling replacement (B2), and
   against which immutable dataset revision?
4. **Target `answer_format` coverage.** `json`/`number` teacher coverage was zero; the external
   `emit_our_tool_call_format` dataset may not contain the CadQuery workplane tool. Decide whether the
   CAD-QA task dataset must synthesize it.

---

## 9. Open questions (data)

- **Q1.** Is there a public CadQuery instruction corpus worth using, or does the internal set alone provide the `submit_workplane` (`json`) format? `[unverified]`.
- **Q2.** How much of the Fable/Opus signal survives filtering and dedup? `[unknown]`.
- **Q3.** Does the external `emit_our_tool_call_format` dataset teach the exact `submit_*` tool names/args,
  or only generic function calling? If only generic, `learn_the_cadqa_task` must carry the mapping.
- **Q5.** Should evaluation dataset roles split into `target` / `guard`? `[open]`
- **Q6.** What are the two Mixed training dataset names (`mixed_dataset_*`)? `[open]`

---

## 10. Immediate next step (data)

1. Write the `TrainingExample` record + converter (P0), reusing the surviving `rows_loader.py` and
   the typed definitions in `tool_calls.py`; emit Liquid's `messages` JSONL.
2. Build `mixed_dataset_general_and_easy_cadqa` (general tasks + low-hop `learn_the_cadqa_task`) from
   permissive sources, with the registry/quality/dedup pass (`system.md` §7).
3. Hand the artifact to the training doc's cookbook run for the `emit_our_tool_call_format` evaluation dataset.
4. Only after H1 is measured, plan `learn_the_cadqa_task` (§6) and `mixed_dataset_full_cadqa_training`.
