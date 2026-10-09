# Fine-tuning — post-training system

**Status:** active, 2026-10-09. Fourth of four fine-tuning/evaluation docs.

**This doc owns — the shape of the whole post-training system:** why a raw SFT→RL run is not
enough, the staged loop that replaces it (Query verifier → SFT → RL-readiness gate → RL/distillation), the
RL-readiness gate, reward/Query verifier design, sandboxed rollouts, logging, the framework mapping, and
**data preparation** (the `TrainingExample` record, its converter, and the
ingest/normalize/quality/dedup/sample stages).

**It does not re-own** the data (`data.md`), the training config/hardware
(`training.md`), or the harness/scorer (`../evaluation/plan.md`). It sequences
them into one system and adds the pieces none of the three owns: the RL-readiness gate, the
reward-hacking audit, and the on-policy stages.

**Related docs.** `../../prior-art.md` (refs [1]–[33]);
`decisions.md` (FT-D*); `../../PRD.md`;
`../../../plans/oct-8/trust-audit.md`.

---

## 0. Direct answer

**Raw SFT works; raw GRPO-on-top does not.** The evidence is now specific enough to say why:

- **SFT with LoRA is the reliable training stage.** It was best in 15 of 18 in-distribution settings and
  never fell below zero-shot (ref [19]). We should run it.
- **A raw SFT→GRPO run on this task is expected to be weak or null**, and the repo already
  recorded one collapse (the GRPO 2-hop collapse, FT-D6/FT-D8). Two 2026 results explain it:
  - A controlled web-agent study found **GRPO adds no credible gain on skills the supervised
    LLM model has already mastered, and only gains where the reward is reachable by sampling**
    (ref [20]). Degenerate rollout groups (all-correct or all-wrong) carry zero advantage, so the
    gradient is zero — this is the CAD-QA collapse.
  - SFT→RL can fail completely when the expert traces are too hard for the small LLM model, or
    when the SFT initialization has exponentially sparse rewards (BREAD, ref [26]).
- **The fix is a system, not an algorithm swap.** Condition RL on measured per-tier reachability
  (§3), keep only informative rollout groups (refs [21]–[23]), treat the Query verifier as a first-class
  artifact to audit (ref [24]), and prefer sampling-based SFT as the cheaper consolidation when RL
  is not clearly reachable (ref [25]).

This is what Liquid's own LFM2.5 post-training recipe does at scale: **SFT → teacher-specialist
RLVR → on-policy distillation → agentic RL (GRPO) in sandboxes**. The system below is the
single-GPU analogue.

**Scaling thesis (2025–2026).** Capability gains increasingly come from **environmental scaling** —
RL against rich, verifiable interactive environments — rather than from more SFT data ([30][31]).
The scaling asset is therefore the **CAD-QA task environment + scorer** (a task generator, the
single exact-match reward, and the `run_code`/kernel tool interface), not the SFT corpus. SFT's job
is narrow: get the small LLM model to emit our `submit_*` format and produce *some* successful
rollouts — a **readiness check, not an accuracy target** ([32]); over-doing SFT ossifies the policy
and collapses the exploration RL needs. External general data is support (a tool-schema cold-start and
general-task diversity), not the lever.

---

## 1. Why "raw SFT + RL" is the wrong frame

Three independent things break a naive loop, and each has a 2026 answer:

| Failure | What happens | Answer |
|---|---|---|
| **Degenerate groups** | A prompt every rollout passes or every rollout fails contributes zero advantage; GRPO spends compute to learn nothing | Dynamic sampling / group filtering (DAPO, ref [23]); keep the informative RL-eligible pass rate (refs [21][22]) |
| **Sparse / unreachable reward** | On hard hops the SFT policy never samples a correct answer, so RLVR has no signal at all | Measure pass@k first; only train RL where it is reachable; use a Bridge to make hard traces learnable (ref [8], ref [26]) |
| **Query verifier is wrong or hackable** | Reward is the objective; a noisy or gameable scorer optimizes the wrong thing | Audit and consolidate the scorer first (ref [24]); adversarial fixtures; this is TA-A3, already open |

The single most important consequence: **the Query verifier is the objective, not a metric.** In SFT a
bad scorer only miscounts; in RL it is what the LLM model climbs. So the evaluation doc's P0
"one scorer" is not bookkeeping — it is a precondition for ever running RL.

---

## 2. The system

```text
[ Training stage 0  Query verifier + eval contract ]  <- P0, gates everything
        |
[ Training stage 1  difficulty-aligned SFT ]     <- our tool schema + easy hops + Bridge for hard traces + general-task diversity
        |
[ Training stage 2  RL-readiness gate (pass@k) ]     <- measure reachability per tier; build RFT data
        |            \___ if no tier is reachable -> stop at SFT / RFT, do not run RL
        |
[ Training stage 3  RL (GRPO + dynamic sampling, only on reachable tiers, sandboxed) ]
        |
[ Training stage 4  on-policy distillation / RFT consolidation ]  <- optional, cheaper alternative to Training stage 3
```

**Training stage 0 — Query verifier and eval contract.** Reconcile the three scorers into one (TA-A3), add the
off-oracle wrong-answer/formatting fixtures (TA-A2), and freeze the held-out + evaluation-dataset rows. No
downstream training stage is trustworthy until this passes. (Owned by `../evaluation/plan.md`.)

**Training stage 1 — difficulty-aligned SFT.** Per ref [8]: SFT should acquire not-yet-mastered skills;
data difficulty must be aligned to the training stage. Concretely: `emit_our_tool_call_format` + easy hops first, then
harder `learn_the_cadqa_task`; for hard teacher traces that the small LLM model cannot imitate, apply a
**Bridge** transformation (rewrite the raw agent training trace from the teacher into more learnable supervision) rather
than feeding an unlearnable target. Keep the general tasks in every training stage. SFT runs only to the **readiness check**
(format holds, pass@k > 0), then stops — it is not an accuracy target ([32]).
(Owned by the data + architecture docs.)

**Training stage 2 — RL-readiness gate.** The new piece. After SFT, sample a rollout count of completions
per prompt with the tuned policy and compute the **pass rate** per tier:

- **mastered** (all rollouts pass): RL adds nothing here (ref [20]); use as an evaluation dataset, not for training.
- **learnable** (some but not all rollouts pass): the RL-training set. Aim the training distribution at the
  ~0.25–0.75 RL-eligible pass rate (refs [21][22]); ~0.5 maximizes reward entropy and group-filter survival.
- **unreachable** (zero pass): no RL signal. Add via Bridge/re-distillation at the next SFT
  training stage (ref [8]) or leave out and record it.

The same rollouts, filtered to the learnable bucket, are the cheapest consolidation: **rejection
sampling fine-tuning (RFT)** — SFT on self-generated correct traces. Ref [25] finds SFT with
sampling can beat on-policy RL on new-task generalization *and* prior-capability retention. For a
single-GPU thesis, Training stage 2 may be the whole answer, with Training stage 3 optional.

**Training stage 3 — RL, only where reachable.** GRPO with **dynamic sampling** (drop all-pass/all-fail
groups, ref [23]), RL-eligible pass-rate scheduling (refs [21][22]), and a composite reward (§4). Run
rollouts in a sandbox (§5). Never run RL on a tier with no partial signal.

> **P2 backlog — hint-based rollouts.** The dataset already carries a deterministic derivation: the
> **ordered Gold query program**, with the per-row `clue_map` mapping each predicate to its public clue (a
> **private** field, withheld from public rows). That yields a natural **hint ladder** (reveal a leading
> prefix of the ordered predicates) to condition or anneal rollouts. It is also the designated
> **fallback** when the RL-readiness gate finds no `learnable` tier: rather than stopping, roll out with
> the hints (teacher, or a student that passed an easier tier) and anneal toward un-hinted RFT
> (`pipeline/05-rl-readiness-gate.md`). P2 only; read first that privileged on-policy
> distillation can *harm* thinking LLM models (ref [9]) and that hints are a reward-hacking risk
> (refs [27][28]). There is no separate "hints" dataset field today — this is the `clue_map` +
> Gold query program.
>
> **Related P2 — step-level verification.** Check that a pass *followed the Gold query program's
> predicates* (via `clue_map` traceability) rather than guessing the answer, so a pass is a correct
> trajectory, not a lucky sample (refs [27][28]).

**Training stage 4 — consolidation.** On-policy distillation (the student rolls out, a per-domain teacher
supervises; Liquid's MOPD training stage) or another RFT round, to fold the RL gains back without entropy
collapse ("RL squeezes, SFT expands", ref [7]).

**The two training phases.** SFT is run as two phases, each a run over a Mixed training dataset
(`data.md` §4):

1. **Phase 1 — refocus on coding (plus easy tasks).** The base LLM model is already trained on code,
   so coding/Python is not new — it is just not its focus. Phase 1 refocuses it on a **general mix**
   (⅓ coding agent, ⅓ 3D math, ⅓ text2CAD + edits) and carries a **simple slice of our own tasks**
   (e.g. hop 0, `learn_the_cadqa_task`) as a safety net.
2. **Phase 2 — the CAD-QA task (new domain) + preserve.** CAD is very likely new to the base LLM model, and our
   CAD-QA dataset certainly is. Phase 2 fine-tunes on `learn_the_cadqa_task` at scale — progressively
   more complex rows (the 0→1→2→3→5 hop ladder) — alongside the general mix, with **no separate
   `emit_our_tool_call_format`** (the format comes with the task), and
   shifts the objective from *eliciting* reasoning to *preserving* it (`preserve_general_math_and_code_reasoning`,
   `expose_*`).

The evaluation datasets (`../evaluation/plan.md` §6) measure both phases: **baseline** before phase 1,
**periodic** subsets and a **phase-end** extensive eval in each phase, and the **final** eval after
phase 2; iterate from the final eval. The RL-readiness gate (§3) sits after SFT, and RL (Training stage 3)
stays conditional on it.

---

## 3. The RL-readiness gate

Promote the §4.1 advancement gate from the data doc into a system-level advancement gate:

- **Signal to advance a tier:** held-out pass rate clears the SFT floor (~80%) — the tier is
  *mastered* and becomes SFT-stable.
- **Signal to run RL on a tier:** it is *learnable* — `0 < pass@k < 1`, and preferably in the
  ~0.25–0.75 RL-eligible pass rate. Use **pass@k, not greedy accuracy**, to predict RL potential (ref [8]).
- **Signal to stop:** no tier is learnable → report an SFT/RFT result; RL is not indicated. This
  is a finding, not a failure (PRD definition of done, item 3).

Record pass@k per tier for every checkpoint. This is also how the `learn_the_cadqa_task` difficulty tiers earn
their keep: the tiers let us measure reachability, not just train in order.

---

## 4. Reward and Query verifier design

- **Single sourced scorer** (TA-A3) is the reward and the eval metric. The `boolean` union from
  `grading/parse.py` is the target.
- **Composite, outcome-primary reward:** outcome exact-match (primary) + format/tool-valid term +
  a bounded length/overlong penalty. Do not let a dense format term dominate the outcome term —
  that is exactly the reward-hacking recipe (ref [27]): a dense heuristic reward gets optimized at
  the expense of the verifiable one. Use optimality-preserving shaping (GRM/ADOPS) if a dense term
  is added.
- **Query verifier audit is P0, not P1.** Ref [24] finds Query verifier self-agreement as low as 53.8% and two
  configurations of the *same* library disagreeing on 49.9% of pairs. Our three divergent scorers
  are this risk already realized. Before RL: adversarial cases, off-oracle fixtures, and a
  metamorphic check (equivalent answers must score equal).
- **Reward-hacking detection:** sample rollouts, and before trusting a gain, test counterfactuals
  (e.g. inject a wrong hint; a correct answer that changes with the hint is hacking) and audit for
  degenerate length/format tricks. Gradient-fingerprint methods (ref [28]) are P2.

---

## 5. Sandboxed rollouts and logging

- **Rollouts run generated code**, so they need real isolation, not the `python -I -B`
  accidental-misuse guard (FT-D7, TA-B1). Use **Modal Sandboxes** (already our environment) or
  `liquid-finetune`'s optional **OpenEnv** block for stateful multi-turn tool use.
- **Log every rollout** — internal reasoning, visible output, tool calls, reward, and the
  pass/fail — to JSONL/DB, per the repo standing rule (FT-D9): easy to reconstruct, one record
  per call, never collapse reasoning into output.

---

## 6. Framework mapping (stay in one stack)

`Liquid4All/liquid-finetune` already covers the whole loop, so the system does not require a
second framework:

| System training stage | `liquid-finetune` provision |
|---|---|
| SFT, LoRA | `training_type: sft`, `TrainingConfig(extends="DEFAULT_SFT")`, `PeftConfig(extends="DEFAULT_LORA")` |
| GRPO | `training_type: grpo`, TRL v1 `GRPOTrainer`, vLLM rollouts, Ray Train |
| Reward | `rewards:` block resolving plain Python callables/recipes from `rewards/`; extra columns forwarded |
| Stateful rollouts | optional `rl_env:` (OpenEnv) block; `uv sync --extra rl-env` |
| Launch | Modal (recommended) or local CUDA on Vast.ai |

Escalate to **verl** (the framework behind Liquid's own agentic RL) only if we reach real
multi-turn agentic harness RL with per-step rewards. For text
single-turn `learn_the_cadqa_task`, `liquid-finetune` GRPO is sufficient. Modal officially supports GRPO with
both TRL and verl and provides Sandboxes for rollout isolation, so either path fits our environment.

Note: the **DSpark** speculator is **SGLang-only** (not vLLM), so accelerating GRPO rollouts with it would
ride the **verl + SGLang** path, not the default TRL + vLLM one (FT-D22 Q4).

---

## 7. Data preparation (the record and the converter)

**The on-disk training artifact is a Liquid `messages` SFT set** — the `messages` schema the cookbook
and `liquid-finetune` validate (the architecture doc owns that contract). `messages` is a **schema,
not a container** (Parquet preferred / JSONL fallback; `../training.md` §4). `TrainingExample` is the
typed CAD-QA-side record; a small **converter** turns it into the cookbook format. Do not grow this
schema or the converter beyond what the mix and the evaluation datasets need.

| Field | Notes |
|---|---|
| `id` (`str`) | stable, content-hashed |
| `dataset_role` (`DatasetRole`, StrEnum) | `emit_our_tool_call_format`, `run_the_tool_call_loop`, `preserve_general_math_and_code_reasoning`, `expose_general_python_code`, `expose_cadquery_programs`, `learn_the_cadqa_task` |
| `messages` (`list[ChatMessage]`) | the conversation; `ChatMessage{role, content, tool_calls?}` maps 1:1 to Liquid's `messages` schema |
| `source_id` (`str`) | HF repo or internal artifact |
| `source_revision` (`str`) | **commit hash**, not a branch/config name |
| `license` (`str`) | e.g. `apache-2.0`, `agpl-3.0`, `cc-by-4.0` |
| `reasoning_text` (`str \| None`) | internal reasoning, kept distinct (A5 rule) |
| `tool_call_text` (`str \| None`) | the call envelope, kept distinct (A5 rule) |
| `tools` (`list[ToolSpec]`) | declared tools for the turn |
| `answer_format` (`AnswerFormat \| None`) | for `learn_the_cadqa_task` and `emit_our_tool_call_format` |
| `reasoning_hop_count` (`int \| None`) | for `learn_the_cadqa_task` curriculum |
| `split` (`Split`, StrEnum) | `train` / `validation` / `test` |
| `provenance` (`str`) | the exact field mapping/transform applied, for audit |

Preparation stages (pipeline stages 1–5; the architecture doc owns pipeline stages 6–8 and the
evaluation doc owns pipeline stage 9):

1. **Registry.** Dataset id, revision hash, license, role, size, field mapping. The data doc's
   governance section owns the policy; an External dataset without a pinned revision does not enter.
2. **Ingest + normalize.** Pull a **bounded subset** of each External dataset — stream, select
   shards, or filter rows at the pinned revision, never materialize a whole multi-million-row
   corpus to keep a few thousand — then map it into `TrainingExample`. Record reasoning, visible
   output, and tool calls **distinctly** (A5). Record the selection rule and seed for the manifest.
   Fail loudly on unknown fields.
3. **Quality gate.** Schema validation; secrets scrub; length filter; tool-call parse under the
   typed contract (`../../../train_and_eval/tool_calls.py::tool_call_matches` semantics); language
   filter; plus the Home Assistant contamination gates (benchmark blocklist, exact/substring,
   trigram Jaccard > 0.5 discard, cross-validation).
4. **Dedup + contamination.** MinHash/LSH near-dedup within and across sources; hash-exclude the
   CAD-QA held-out rows and the evaluation datasets. Hard failure if any evaluation-dataset id appears in `train`.
5. **Sample + mix.** Per-role quotas from the data doc §3; deterministic seed; **order/interleave the
   `learn_the_cadqa_task` rows by Reasoning hop count** (the progressive curriculum, data plan §4); emit a mix report
   (counts, token totals, role weights, and per-hop/per-format coverage for `learn_the_cadqa_task`).

**No silent data loss.** Rejected/filtered rows and failed joins are recorded, not dropped
silently.

---

## 8. P0 / P1 / P2 (system)

| Item | Tier | Rationale |
|---|---|---|
| One scorer + off-oracle fixtures (TA-A2/A3) | **P0** | the Query verifier is the RL objective; nothing downstream is valid without it |
| RL-readiness gate: pass@k per tier after SFT | **P0** | decides whether RL is indicated at all (refs [8][20]) |
| Reward-hacking audit (counterfactuals, degenerate tricks) | **P0** | RLVR's central failure mode (refs [24][27]) |
| Sandboxed rollouts + full rollout logging | **P0** | safety + reproducibility (FT-D9) |
| Dynamic-sampling GRPO (drop degenerate groups) | **P1** | cheap, principled; needed the moment RL runs (ref [23]) |
| RL-eligible pass-rate scheduling (~0.25–0.75) | **P1** | keeps batches informative (refs [21][22]) |
| RFT / SFT-with-sampling consolidation | **P1** | cheapest consolidation; can beat on-policy RL (ref [25]) |
| Bridge for unlearnable hard traces | **P1** | turns all-fail tiers into SFT signal (ref [8]) |
| On-policy distillation (MOPD-style) | **P2** | Liquid's recipe; heavy for one GPU |
| verl / multi-turn agentic RL with per-step rewards | **P2** | only if single-turn RL saturates |
| Gradient-fingerprint hacking detection | **P2** | research-grade; use counterfactual audit first |

---

## 9. Decisions and open questions (system)

**Proposed decisions.**

- **FT-D13 — the post-training system is staged, not raw SFT→GRPO.** Training stage 0 Query verifier → Training stage 1
  difficulty-aligned SFT → Training stage 2 RL-readiness gate → Training stage 3 RL only on learnable tiers
  (dynamic sampling) → optional Training stage 4 distillation. RL on this task is *conditional on a measured
  learnable tier*, not a default second training stage.
- **FT-D14 — the scorer is the reward and is audited before RL.** The one-scorer reconciliation
  (TA-A3) and the off-oracle fixtures (TA-A2) are P0 gates for any RL run, not cleanup.
- **FT-D11 addendum — `liquid-finetune` covers SFT *and* GRPO** (TRL v1 `GRPOTrainer`, `rewards/`,
  optional OpenEnv), so the Phase 3 stack does not need a second RL framework; FT-D8's "GRPO second
  training stage" stays deferred but is now cheap to attempt once Training stage 2 says it is reachable.

**Open questions.**

- **Q5.** The staged loop labels the Query-verifier/eval-contract step and the RL-readiness gate as
  `Training stage 0`/`Training stage 2`, but neither consumes a Mixed training dataset or updates
  weights (the glossary's Training-stage definition). Should these be renamed (for example
  `system stage`), or is the broad use intended? `[open]`

**Resolved.**

- **Q1.** *(2026-10-09)* Tiers are **measured** from pass@k, not derived from `difficulty_bucket` +
  Reasoning hop count — those are priors to stratify by, not the definition. A rollout count of 8 to
  screen → 16 to confirm; rollout temperature ≈ 1.0. Definition: `pipeline/05-rl-readiness-gate.md`.

**Owner decisions needed (cross-plan).** These block a step and need a human call; the other open
questions here resolve by running or inspection. Labels point to the owning doc.

- `../evaluation/plan.md` Q5 — canonical BenchCAD transfer target (full `qa_code` / Spatial Reasoning axis /
  hard family subset), and whether `edit_code` T4/T5 is in scope at 2–4B.
- `../../../plans/oct-8/trust-audit.md` Q1 — accept the accidental-misuse-guard threat assumptions, or require kernel isolation before
  the external claim.
- `../../../plans/oct-8/trust-audit.md` Q3 — one tracked environment, or separate SFT and serving environments.
- `../../../plans/oct-8/trust-audit.md` Q4 — GPU parity + SFT re-run in Phase 0, or the top of Phase 1.
- `data.md` Q5 / `docs/train-and-eval/datasets.md` Q3 — do evaluation dataset roles split
  into `target` / `guard`.
- `data.md` Q6 / `docs/train-and-eval/datasets.md` Q2 — the two `mixed_dataset_*` names.

**Resolved questions.**

- **Q2.** *(2026-10-09)* Framework conformance, not a research unknown. TRL / `liquid-finetune` GRPO takes
  plain Python reward callables and forwards dataset columns, and `reward_cadqa(completions, **kwargs)`
  already matches that signature; tool passthrough is an `apply_chat_template(tools=…)` concern. Confirm
  both on the first GRPO smoke run (§10).
- **Q3.** *(2026-10-09)* Answered by construction: the Training stage 2 RL-readiness gate decides RFT vs RL from
  the measured reachability, not on paper (§3; FT-D13).
- **Q4.** *(2026-10-09)* No — `cadquery` mode is not needed for RL. RL uses the same `run_code`/`numpy` tool
  interface; `cadquery` is a P2 evaluation upper bound (`../evaluation/plan.md` §2). RL itself is conditional on
  the RL-readiness gate (FT-D13), so the question is moot until then.

---

## 10. Immediate next steps (system)

1. **Training stage 0:** reconcile the scorer (one implementation) and build the off-oracle fixtures
   (evaluation doc, P0).
2. **Training stage 1:** run the cookbook pilot, then `mixed_dataset_general_and_easy_cadqa`, then `mixed_dataset_full_cadqa_training` (training + data
   docs).
3. **Training stage 2:** once an SFT checkpoint exists, run the RL-readiness gate per tier and record
   reachability. Decide RL vs RFT from that number, not from ambition.
4. **Only then** wire the `liquid-finetune` GRPO config with dynamic sampling and the composite reward, in a
   Modal sandbox; on that smoke run, confirm our `submit_*` tool list passes through
   `apply_chat_template(tools=…)` and that `reward_cadqa(completions, **kwargs)` matches the framework's
   reward-callable signature (this resolves the former Q2).
