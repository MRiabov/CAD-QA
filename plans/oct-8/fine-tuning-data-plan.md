# Fine-tuning data and training-regime plan (2026-10-08)

**Status:** draft, 2026-10-08. Part of a four-doc set: this doc (data + schedule),
`fine-tuning-architecture-plan.md` (training), `fine-tuning-system-plan.md` (the staged
post-training loop and data preparation), and `evaluation-plan.md` (evaluation/harness). Written in
the primary checkout per the repo-local rule in `plans/oct-7/restructure-docs.md` §0.

**This doc owns — which data we train on and when:** data roles, candidate external datasets, the
mix recipe, training order / curriculum / SFT-vs-RL scheduling, licensing and contamination policy,
and the `cadqa_hop` slot.

**The architecture doc owns — how we train the model:**
`fine-tuning-architecture-plan.md` (base LLM model and stack, cookbook-first execution, capability
preservation, the training stages, hardware/budget, and the surviving-code boundary).

**The system doc owns — the post-training loop and data preparation:**
`fine-tuning-system-plan.md` (the verifier → SFT → pass@k gate → RL/distillation loop, and the
`TrainingExample` record, converter, and the ingest/normalize/quality/dedup/sample stages).

**The evaluation doc owns — the harness and scoring:**
`evaluation-plan.md` (LLM harness and modes, tool-call surface, the scorer, the canary
procedure, grading reconciliation, judge independence, baselines).

**Shared interfaces, single-sourced:**

- **Format contract** (Liquid `messages` SFT JSONL) — owned by the architecture doc.
- **`TrainingExample` + converter** — owned by the system doc.
- **Eval canaries** — the procedure is owned by the evaluation doc; the canary rows are produced and
  held here.
- **H1/H2** — owned by the architecture doc; the mixes they test are defined here (§3).

**Explicitly out of scope for now.** The CAD-QA **reasoning-hop dataset** itself (the internal
teacher-sampling of agent training traces from frozen CAD-QA dataset rows, step B2 in
`../../docs/train-and-eval/fine-tuning/pipeline/02-teacher-sampling.md`). This doc defines a
**slot** and a **contract** for that data (§6), but does not plan its generation. That is the
separate decision owed under FT-D11 (`../../docs/train-and-eval/fine-tuning/decisions.md`) and
Phase 3 of `../../docs/development-plan.md`.

**Related docs.** `../../docs/prior-art.md` (external evidence, refs [1]–[32]);
`../../docs/PRD.md` (research contract); `../../docs/train-and-eval/fine-tuning/decisions.md`
(FT-D* decisions).

---

## 1. Data roles (taxonomy)

Every training example is tagged with exactly one **role**. Roles exist because they are mixed at
fixed ratios and evaluated separately. The external roles (`format_tool`, `agent_trace`,
`reasoning_distill`, `rehearsal`, `domain_*`) are **support**: a format cold-start, capability
preservation, and canaries. They are not the scaling lever — the task environment + scorer is
(`fine-tuning-system-plan.md` §0) — so collect them selectively, not blindly.

| Role | What it teaches | Internal / external | Priority |
|---|---|---|---|
| `format_tool` | emit a valid typed tool call in the model's native format | external | P0 |
| `agent_trace` | multi-turn tool loop (call → result → call → answer), incl. `run_code` round-trip | external | P0/P1 |
| `reasoning_distill` | step-by-step reasoning style (long CoT, self-check) | external | P1 |
| `rehearsal` | anchor general instruction-following so it is not forgotten | external | P0 |
| `domain_code` | Python / general coding priming | external | P1/P2 |
| `domain_3d` | 3D / CAD / geometry priming so the base is not 3D-blind | external | P1/P2 |
| `cadqa_hop` | the CAD-QA task itself: prompt → `submit_*` with hop reasoning | internal (**§6 only defines the slot**) | P0 (separate plan) |
| `eval_canary` | never trained on; used to detect regression | external + internal | P0 |

**Rule:** `eval_canary` examples must be **hashed and excluded** from every training mix. Any
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
  upper bounds and the `tool_valid` canary must not be a held-out slice of them — see
  `../../docs/research/2026-sft-vs-rl-tool-calling.md` and the evaluation plan §6.
- ACL 2026 "Skill-Aware Data Selection and Fine-Tuning for Data-Efficient Reasoning Distillation":
  1,000 selected traces beat random SFT from a 100K corpus. Supports small, quality-filtered sets.

### 2.1 Format + tool-calling (`format_tool`)

| Dataset | Date | Size | Shape | License | Adopt/reject |
|---|---|---|---|---|---|
| `ByteDance/ToolACE` | 2025 | ~11k conversations, 26.5k APIs | multi-turn, parallel calls, refusals | see card | **Adopt** as the primary 2025+ format set; multi-turn + refusal coverage |
| `DeepNLP/Agent-Function-Calling-Open-Dataset` | 2026-01 | large | real user requests: messages + tools + calls + results | see card | **Adopt** a slice; real-request distribution |
| `NousResearch/hermes-function-calling-v1` | 2025-01 | ~10k / 5 configs | multi-turn + JSON mode | Apache-2.0 | **Adopt** a slice |
| `Salesforce/xlam-function-calling-60k` | 2024-06 | 60k (56.4k after dedup) | single-turn, parallel calls | CC-BY-4.0 | **Reference corpus** (kept; the 2026 controlled study uses it) |
| Glaive-FC-v2 | 2023 | 113k (46.2k after dedup) | conversational + calls | see card | **Reference only**; 58.5% near-duplicates per the 2026 study |
| `bebechien/SimpleToolCalling` (TRL example) | 2024 | tiny | user + tool | permissive | smoke/debug fixture only |

### 2.2 Agent traces (`agent_trace`)

| Dataset | Date | Size | Shape | License | Adopt/reject |
|---|---|---|---|---|---|
| `open-thoughts/OpenThoughts-Agent-SFT-{1K,3.16K,10K,…}` | 2026 | ladder 316→100K | task + agent trajectory (`terminus-2`) | Apache-2.0 | **Adopt**; pick a rung to match the canary budget |
| `RESMP-DEV/Fable-GPT-5.5-Distillation-Traces` | 2026 | 9.06M | unified 2026 corpus: agentic coding, reasoning, tool use, preference | see card | **Adopt with sampling**; one-stop but huge, mixed provenance |
| `nvidia/Open-SWE-Traces` | 2026 | 207k | multilingual software-engineering agent trajectories | permissive (MIT/Apache/BSD filtered) | **P1**; engineering-flavored, not CAD |
| `AlicanKiraz0/Agentic-Chain-of-Thought-Coding-SFT-Dataset` | 2026 | 429 | Minimax-M2-distilled coding CoT + tool calls | MIT | **P2**; tiny but license-clean |
| `Glint-Research/Fable-5-traces` | 2026 | ~4.5k | Claude Fable 5 coding-agent traces | AGPL-3.0 | **Adopt with caution** — see §5 |
| `spitfire4794/Fable-5-traces` | 2026 | 4,665 | Pi sessions | AGPL-3.0 | shorter-list; same family |
| `cfahlgren1/Fable-5-traces` | 2026 | 115 | raw logs | AGPL-3.0 | **Reject** for training |

### 2.3 Reasoning distillation (`reasoning_distill`)

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
weight, and measure the canary.

### 2.4 Rehearsal (`rehearsal`) — the anti-forgetting anchor

| Dataset | Date | Size | Shape | License | Adopt/reject |
|---|---|---|---|---|---|
| Model-family own instruct mix (e.g. the base's instruct SFT mixture if published) | current | varies | general chat | family license | **Adopt if available** — same distribution as the base is the best anchor |
| `nvidia/Llama-Nemotron-Post-Training-Dataset` (or a permissive general SFT set) | 2025-05 | large | general | permissive | **P1** substitute when the family mix is closed |
| A small held-out slice of the canary's *train* side | current | small | general instruction | permissive | **Adopt** as a cheap anchor |

**Ratio:** 20–30% of the mix, per the xLAM precedent (`xLAM` paper §3.5 reports 20–30% general
instruction data).

### 2.5 Python / general coding priming (`domain_code`)

Short-term coding exposure so the base is not code-naive. Prefer Python + reasoning traces.

| Dataset | Date | Size | Shape | License | Adopt/reject |
|---|---|---|---|---|---|
| `allenai/Dolci-Think-SFT-Python` | 2025-12 | 466k | Python prompts + R1 reasoning traces | ODC-BY-1.0 | **Adopt**; reasoning-bearing Python, permissive |
| `KodCode/KodCode-V1-SFT-R1` | 2025-03 | 483k | verifiable coding Q + R1 CoT | Apache-2.0 | **Adopt** a slice; verifiable, ACL 2025 |
| `nvidia/OpenCodeReasoning` | 2025 | 753k | code reasoning traces | see card | **P1** |
| `KodCode/KodCode-V1` | 2025-03 | 487k | Q + solution + unit tests | Apache-2.0 | **P1**; RL-ready tests |

### 2.6 3D and CAD priming (`domain_3d`)

The earlier "no large public CadQuery corpus" claim was **wrong** — there are several. This role
exists so the base LLM model has seen 3D/CAD before CAD-QA — **representation priming, not a
CadQuery-generation capability**.

| Dataset | Date | Size | Shape | License | Adopt/reject |
|---|---|---|---|---|---|
| `CADCODER/GenCAD-Code` | 2025 | 163k | image → CadQuery Python pairs | Apache-2.0 (repo) | **P2** — image input is not useful for a text-only base today |
| `ricemonster/NeurIPS11092` | 2025 | 170k | text → CadQuery (Text2CAD via Gemini 2.0 Flash) | see card | **Adopt**; text-to-CadQuery pairs + 90/5/5 split |
| `BenchCAD/BenchCAD` (`code_gen`) | 2026 | 17.9k | CadQuery GT code + 5 renders, 106 part families | CC-BY-4.0 | **Adopt**; clean synthetic CadQuery |
| `azizzjr/qwen3-32b-fusion360-98k-v2` | 2025-07 | 98k | Fusion360 code | see card | **P2**; Fusion360, not CadQuery |
| `MRiabov/IntersectionQA-15K` / `-90K` | 2026-04 | 15k / 90k | 3D intersection QA (owner's own) | see card | **Exclude (`[unknown]`)** — same area as CAD-QA and likely an unfinished release, like the benchmark; not a training candidate |
| `sanjuhs/cadforge-cadquery-agentic-traces` | 2026-04 | 174 | agentic CadQuery traces | see card | **Study**; tiny, but exactly our agentic shape |
| `hhllzz/surprise-3d` (SURPRISE3D) | 2025-07 | 190k | 3D-scene spatial-reasoning VQA | MIT | **P2**; scene-level, image/point-cloud grounded |
| PointLLM / Cap3D captions | 2023 | 730k | object point cloud + text instructions | see card | **P2**; object-level |
| `hiyouga/geometry3k` | 2025 | 3k | image geometry VQA | MIT | **P2**; image-based |
| `LiAuto-DSR/GeoGramBench` | 2025 | 500 | program-to-geometry benchmark | see card | **Eval only**; already ref [10] |

**Contamination rule:** `domain_3d` must not leak the CAD-QA held-out programs or their generating
corpus. Any same-area set (including an owner-authored one) carries a higher leakage risk: run the
quality gate (`fine-tuning-system-plan.md` §7) and a held-out overlap check before mixing.

**Deferred (vision):** image→CAD and point-cloud/3D-vision sets (`CADCODER/GenCAD-Code`,
`hhllzz/surprise-3d`, PointLLM/Cap3D, `hiyouga/geometry3k`) are **P2** — the primary base LLM model
is text-only, so image and point-cloud inputs are not usable until a multimodal stage.

**Excluded:** `MRiabov/IntersectionQA` is the owner's own same-area release, but its outcome is
`[unknown]` (likely unfinished, like CAD-QA). It is not a training candidate unless it is later
found to be clean and non-overlapping.

---

## 3. The mix recipe

| Mix | Role weights | Purpose |
|---|---|---|
| `mix-format` (canary) | 70% `format_tool`, 30% `rehearsal` | test H1 alone, cheapest signal |
| `mix-full` (primary) | 35% `format_tool` + `agent_trace`, 25% `reasoning_distill`, 25% `cadqa_hop`, 15% `rehearsal` | test H2, the thesis number |

Rationale and tradeoffs:

- **Format before reasoning.** If the model cannot emit a valid `submit_*` call, accuracy is zero
  regardless of reasoning. Prove H1 first on the cheapest possible data.
- **Mix corpora; corpus choice matters.** The 2026 controlled study (arXiv:2609.17848) found
  corpus choice swings tool-calling accuracy by up to 55 points and a uniform mixture is the best
  transfer default — so `mix-format` blends `format_tool` sources rather than betting on one.
  (Magnitude is contamination-affected; see §2.)
- **Rehearsal is not optional.** Without it, the LoRA-only setting still risks regression (see the
  architecture doc, capability preservation); it is cheap insurance.
- **`cadqa_hop` weight is a placeholder.** Until its generation is planned (§6), `mix-full` is not
  runnable; `mix-format` is runnable immediately from public data and is the first GPU spend.
- **Sample, don't ingest wholesale.** Cap each source (e.g. 5–20k examples) by quality score and
  dedup; xLAM and TeichAI both report that quality beats quantity at this size. **Pull a subset,
  not the whole corpus** — stream or select shards/rows at the pinned revision instead of
  downloading a multi-million-row dataset to keep a few thousand; record the selection rule and
  seed so the manifest reproduces it.

### 3.1 Corpus size targets

Aim **~10,000 examples (band 5,000–20,000)** for the primary run, with a **~1,000–2,000 canary**.
The binding constraint is the internal `cadqa_hop` set, not the external data: it is generated by
teacher API calls and must cover every Answer format × hop, so it sets the budget and the wall
clock. **≥1,000 verified traces** is the target; the current ~300 is too few — `json`/`number`
coverage was 0.

| Stage | Total | `format_tool` + `agent_trace` | `reasoning_distill` | `cadqa_hop` | `rehearsal` |
|---|---|---|---|---|---|
| Canary (`mix-format`) | 1,000–2,000 | 700–1,400 | — | — | 300–600 |
| Primary (`mix-full`) | 10,000 (5k–20k) | 3,500 | 2,500 | 1,000–2,500 | 1,500 |

- **Why not larger.** Curated small sets match or beat large ones at this size: ACL 2026 (1,000
  selected traces beat random SFT from 100k), TeichAI (~4k), AnkitAI/Parable (~4.4k), and `ToolACE`
  9.7k competed with `xLAM` 56k in the 2026 controlled study. The gain is coverage + quality, not
  raw count.
- **Scale is GPU-cheap, data-expensive.** At `SEQ=6144`, 10k examples is roughly 10–30M tokens; a
  single epoch on a 2.5B base is hours on a 24 GB card. The teacher API budget is the real ceiling.
- **Coverage beats volume.** Every Answer format and hop bucket must clear a floor; a format with
  zero traces cannot be learned (the recorded `cadqa_hop` defect). Enforce a per-format minimum,
  not just a total.

---

## 4. Order and curriculum of training

This section owns the *order* the roles and difficulty are presented in. The architecture doc owns
the mechanics (epochs, mixing implementation).

- **Default: one mixed supervised stage (`mix-full`).** The cookbook trains a single SFT stage, so
  the default is one pass over the mixed data. This is the baseline; do not stage until the
  baseline is measured.
- **Format before reasoning (staged option, P1).** If the mixed baseline underperforms on format,
  stage it: (1) `mix-format` to lock the tool format, (2) `mix-full` to add
  `reasoning_distill` + `cadqa_hop`. The staged option tests the H1→H2 ordering directly.
- **Difficulty-aligned rows.** Order or interleave the `cadqa_hop` rows by Reasoning hop count
  (the `0→1→2→3→5` ladder in `../../docs/development-plan.md` Phase 3 and the teacher quotas in
  FT-02-D1). Do not front-load the hard slice.
- **Rehearsal is interleaved, not appended.** Keep the `rehearsal` share in every stage, so
  general ability is anchored throughout, not restored at the end.
- **Cap `reasoning_distill` early.** Per prior-art ref [9], do not let teacher reasoning dominate
  before format and the task itself are established.
- **Domain-first, then task (owner-proposed): CadQuery extensively, then progressively harder
  CAD-QA.** The intent is right — domain adaptation before task SFT, easy hops before hard ones —
  and it maps to `domain_3d` → `mix-full` with the `cadqa_hop` rows ordered by Reasoning hop count.
  Two caveats:
  - **Priming, not a generation capability.** We do not need the model to *write* CadQuery; the
    public corpora (`NeurIPS11092`, `GenCAD-Code`) are useful only as SFT signal that teaches
    CadQuery syntax and semantics — representation priming. Whether that transfer reaches
    *reading/reasoning* over a given CadQuery program is the hypothesis to test, not a given, so
    keep `domain_3d` out of the first canary and A/B it.
  - **Staging is an ablation, not an assumption.** Sequential fine-tuning is multi-stage
    fine-tuning: higher forgetting risk and cost, and the 2026 controlled study (ref [19]) found a
    single SFT stage strongest with no consistent gain from a second stage. Keep rehearsal in
    *every* stage and canary each; implement as either a curriculum *order* within one run
    (cheaper) or a checkpoint-resumed second stage, and measure both before committing.
  Keep it P1 and measure the canary.
- **SFT → RL/DPO only after SFT is measured (P2).** The recorded ordering ("RL squeezes, SFT
  expands", prior-art refs [7]/[8]; FT-D8) is a second stage, deferred until the SFT number is
  real.

### 4.1 Advancement gate

Advance to the next difficulty tier (the hop ladder / `difficulty_bucket`) only on a **measured,
held-out** pass rate — never on training loss, and never on the training rows (overfit). The
mechanism differs by stage:

- **SFT: a data decision, not a guarantee.** SFT trains by imitation, so it cannot guarantee
  mastery of a tier; but per-hop held-out accuracy at checkpoints can drive a *data* decision —
  add the next hop's `cadqa_hop` rows only once the current hop clears the gate. A held-out floor
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
  `evaluation-plan.md`; the ordering and the gate live here.

---

## 5. Governance: registry, licensing, and contamination

- **Registry.** Every source has id, revision hash, license, role, size, and field mapping. A
  source without a pinned revision does not enter.
- **Contamination policy.** CAD-QA held-out rows and the eval canaries are hard-excluded; any
  canary id appearing in `train` is a hard failure. The mechanics (quality gate, near-dedup,
  hash-exclusion, no-silent-loss) live in `fine-tuning-system-plan.md` §7.
- **Licensing and provenance.** Several strong candidate sets are **traces of commercial
  assistant models** (Claude/Fable, GPT-5.5, Opus) and warn that provider terms may apply to
  downstream training/distillation; the Fable sets are **AGPL-3.0**. For a published Master's
  thesis this is a real risk. Mitigation, in order:
  1. Prefer permissively licensed, fully-open sources (`OpenThoughts`, `Bespoke-Stratos`, `xLAM`,
     `Hermes`) for the primary mix.
  2. Treat Claude/Fable/Opus distill sets as **P1/P2 and attribution-dependent**; record their
     terms in the registry and the model card.
  3. If a commercial-trace mix is used, disclose it in the manuscript's data statement.

---

## 6. The `cadqa_hop` slot

`cadqa_hop` is the CAD-QA task itself: one row of a frozen CAD-QA dataset file → a prompt plus a
typed `submit_*` answer, with hop reasoning. This doc fixes only the slot:

- **This is the comprehension corpus.** CAD-QA *is* the program → question (comprehension) data;
  there is no large public equivalent, which is the dataset contribution. That is why the external
  `domain_3d` sets are generation-only proxies, and this slot — not they — carries the task signal.
- **Producer (not planned here):** the Phase 3 replacement for step B2 teacher sampling, owed
  under FT-D11.
- **Contract:** each example is a `TrainingExample` with `role=cadqa_hop`, `answer_format` set,
  `reasoning_hop_count` set, and (once rendered) a `submit_*` tool call.
- **Coverage requirement:** every Answer format must have at least one trace, because a format the
  teacher never produces cannot be learned (the `json`/`number` zero-coverage defect in
  `../../docs/train-and-eval/fine-tuning/pipeline/02-teacher-sampling.md`).
- **Contamination:** CAD-QA held-out rows are hard-excluded (§5).
- **Priority:** P0, but a separate plan.

---

## 7. P0 / P1 / P2 (data)

| Item | Tier | Rationale |
|---|---|---|
| `TrainingExample` record + Liquid `messages` JSONL converter (owned by the system plan) | **P0** | the only custom data code we should need; cookbook-compatible |
| Registry with pinned revisions, licenses, and dates | **P0** | reproducibility, the license audit, and the 2025+ freshness policy |
| `mix-format` data build (`format_tool` + `rehearsal`) | **P0** | feeds the first canary (H1) |
| Contamination + dedup pass against CAD-QA held-out and canaries | **P0** | held-out hygiene; a leak invalidates the thesis number |
| Rehearsal slice curation (20–30%) | **P0** | anti-forgetting anchor |
| **`cadqa_hop` generation plan** | **P0, separate** | the thesis needs it; explicitly not in this doc |
| Permissive reasoning mix (`OpenThoughts`/`Bespoke`) | **P1** | tests H2 without license risk |
| `agent_trace` / `run_code` data (`OpenThoughts-Agent`) | **P1** | needed for the primary `numpy` LLM harness behaviour |
| Staged training order (`mix-format` → `mix-full`) | **P1** | tests H1→H2 ordering if the mixed baseline underperforms |
| Dedup/contamination automation | **P1** | manual hashing works for the canary; automate before `mix-full` |
| Commercial-trace mix (Fable/Opus/TeichAI) | **P1/P2** | strong signal, attribution risk; only if the P0 path is green |
| `domain_code` Python/coding priming | **P1/P2** | cheap code exposure; measure the canary |
| `domain_3d` text→CadQuery priming (`NeurIPS11092`, `BenchCAD` code_gen) | **P1** | so the base is not 3D-blind; text→CadQuery pairs exist |
| `domain_3d` image→CAD / point-cloud priming (`GenCAD-Code`, `SURPRISE3D`, PointLLM) | **P2** | not usable with a text-only base today |
| Math/reasoning scale-up (`OpenMathReasoning`, `NuminaMath`) | **P2** | scale only if H2 holds |
| ≥10k CAD-QA release tier | **P2** | already P2 in `development-plan.md` |

---

## 8. Decisions still to make (data)

1. **Commercial-trace policy.** Do we accept Claude/Fable/Opus distill data in a published thesis?
   Recommendation: permissive-first, commercial-trace only as an ablation.
2. **Mix ratios.** The §3 numbers are a starting hypothesis, not a result.
3. **Order of training.** Mixed single stage (default) vs staged format→full. Decide after the
   `mix-format` canary.
4. **`cadqa_hop` ownership.** Who plans the internal teacher-sampling replacement (B2), and
   against which frozen dataset revision?
5. **Target `answer_format` coverage.** `json`/`number` teacher coverage was zero; the external
   `format_tool` mix may not contain the CadQuery workplane tool. Decide whether `cadqa_hop` must
   synthesize it.

---

## 9. Open questions (data)

- Is there a public CadQuery instruction corpus worth using, or is the internal set the only source
  of the `submit_workplane` (`json`) format? `[unverified]`.
- How much of the Fable/Opus signal survives filtering and dedup, and is the remaining license
  risk acceptable for publication? `[unknown]`.
- Does the external `format_tool` mix teach the exact `submit_*` tool names/args, or only generic
  function calling? If only generic, `cadqa_hop` must carry the mapping.

---

## 10. Immediate next step (data)

1. Write the `TrainingExample` record + converter (P0), reusing the surviving `rows_loader.py` and
   the typed definitions in `tool_calls.py`; emit Liquid's `messages` JSONL.
2. Build `mix-format` from `Salesforce/xlam-function-calling-60k` + a permissive rehearsal slice,
   with the registry/quality/dedup pass (`fine-tuning-system-plan.md` §7).
3. Hand the artifact to the architecture doc's cookbook run for the `tool_valid` canary.
4. Only after H1 is measured, plan `cadqa_hop` (§6) and `mix-full`.
