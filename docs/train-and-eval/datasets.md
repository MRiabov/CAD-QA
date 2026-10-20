# Datasets and dataset roles

**Status:** active, 2026-10-09. New. Assigns each dataset to its **DatasetRole** (`../glossary.md`).

**What this doc owns — the dataset → DatasetRole assignment** for training and evaluation. The mix
recipe (dataset role → weight) and the candidate evidence (sizes, licenses, adopt/reject) are in
`fine-tuning/data.md` §2–§3. The assignment here is canonical; change it
here, then propagate.

**Related docs.** `../glossary.md` (**DatasetRole**, **External dataset**, **Mixed training
dataset**, **Training stage**); `./fine-tuning/decisions.md` (FT-D1–D24);
`./evaluation/harness.md` and `./evaluation/baselines.md`; `fine-tuning/data.md`.

## Rules

- Every **External dataset** has exactly one **DatasetRole**; a **Mixed training dataset** is a
  blend of roles at fixed weights.
- Two forms: an **External dataset** (published outside CAD-QA) and a **Mixed training dataset**
  (a blend at fixed weights).
- A dataset enters only with a pinned revision hash and a recorded license (data plan §5). Sizes
  and licenses are survey-time and must be re-verified.
- `learn_the_cadqa_task` is generated internally (dataset rows in `../../dataset/`; agent training trace distillation in
  `fine-tuning/pipeline/02-teacher-sampling.md`); it is not an external dataset.
- Held-out and evaluation-dataset rows are hard-excluded from every training dataset (data plan §5).
- **DatasetRole is not a data pool.** The SFT/RL/eval pool assignment (`sft_train` / `rl_train` /
  `eval`, target ~70/15/15) is owned by `fine-tuning/data.md` §5 and recorded in the split manifest;
  `sft_train` is the only pool that enters an SFT mix, and `rl_train` is the RL-readiness gate/RL pool.
  External **training** datasets are SFT-only support and are assigned `pool=sft_train`; they never enter
  `rl_train` or `eval`. External evaluation datasets are separate `eval` rows.

## Training datasets by dataset role

### Supervision and verification

Only `learn_the_cadqa_task` is **teacher-generated** (pipeline `02`); every other role is a **native
corpus** that already carries its supervision (an agent training trace and/or a tool call), normalized in `03`.
Under FT-D17 a corpus enters a mix only if **execution-verified** or **teacher rejection-sampled**.
Verification **adopts the upstream project's environment** — a Docker image, a reproducible harness, or a
shipped baseline LLM model we inference over — rather than building an executor. We do **not** build a CAD
kernel.

| DatasetRole | Supervision | Verification | Environment (adopted, not built) |
|---|---|---|---|
| `emit_our_tool_call_format` | native (tool-call turns) | schema/parse against the `submit_*` contract; generic calls re-targeted | our tool-call contract validator (no execution) |
| `run_the_tool_call_loop` | native (agent trajectories) | re-run the tool calls; check the final answer | our tool sandbox (`run_code`; Modal Sandbox) |
| `preserve_general_math_and_code_reasoning` | native (R1/Claude reasoning) | check the final answer; execute code | standard math/code checker (library) |
| `expose_general_python_code` | native (Python + R1 CoT) | execute against unit tests | standard Python sandbox (library) |
| `expose_cadquery_programs` | native (code/label pairs; no CoT) | `BenchCAD code_gen` is verified at origin; text2CAD/edit tasks | **the external benchmark's environment** (Docker/harness/baseline LLM model) — no kernel of ours |
| `learn_the_cadqa_task` | **teacher-generated (`02`)** | the Query verifier accepts the call | our CAD-QA task environment (Query verifier) |

The **text2CAD + edits** third and the H3 transfer targets (`Text2CAD-Bench`, `Text-to-CadQuery`,
`CAD-Editor`, BenchCAD `edit_code`; `../evaluation/plan.md` §5.1) are served by the **same adopted upstream
environments**, so one setup covers both verification and transfer evaluation. Wiring these environments is
itself high-effort (Docker/harness or rebuild — both a pain), so stand up the minimum and prefer
verified-at-origin corpora; the external roles are support, not the lever (FT-D15).

**Do not start there.** Wiring these environments is a known time sink: beginning with it can consume the
budget before any CAD-QA result exists. Run the cookbook and the first mix on **verified-at-origin**
corpora, and stand up an external environment only when a specific role's corpus demands it and the
evaluation shows that role matters.

### `emit_our_tool_call_format`

Teaching a small LLM model to emit our `submit_*` tool calls. The base is an instruct LLM model
with native tool calling, so the gap is our schema, not tool calling itself.

| Dataset | Status |
|---|---|
| `ByteDance/ToolACE` | Adopt as the primary 2025+ set (multi-turn, refusals) |
| `DeepNLP/Agent-Function-Calling-Open-Dataset` | Adopt a slice (real-request distribution) |
| `NousResearch/hermes-function-calling-v1` | Adopt a slice (Apache-2.0) |
| `Salesforce/xlam-function-calling-60k` | Reference (canonical; used by the 2026 controlled study) |
| `Glaive-FC-v2` | Reference only (58.5% near-duplicates) |
| `bebechien/SimpleToolCalling` | Smoke/debug fixture only |

### `run_the_tool_call_loop`

Multi-turn call → result → call → answer, including the `run_code` round-trip.

| Dataset | Status |
|---|---|
| `open-thoughts/OpenThoughts-Agent-SFT-*` | Adopt; pick a rung to match the budget |
| `RESMP-DEV/Fable-GPT-5.5-Distillation-Traces` | Adopt with sampling (huge, mixed provenance) |
| `nvidia/Open-SWE-Traces` | P1 |
| `AlicanKiraz0/Agentic-Chain-of-Thought-Coding-SFT-Dataset` | P2 (tiny, license-clean) |
| `Glint-Research/Fable-5-traces` | Adopt with caution (AGPL-3.0) |
| `spitfire4794/Fable-5-traces` | Same family |

### `preserve_general_math_and_code_reasoning`

General (not CAD) software / math / engineering reasoning tasks, replayed to prevent reasoning
collapse. Support data; FT-D15 does not treat external reasoning as the lever.

| Dataset | Status |
|---|---|
| `open-thoughts/OpenThoughts-114k` | Adopt, down-filter (fully open recipe) |
| `bespokelabs/Bespoke-Stratos-17k` | Adopt |
| `nvidia/OpenMathReasoning` | P1 (scale only if H2 holds) |
| `open-r1/OpenR1-Math-220k` | P1 |
| `TeichAI/Claude-Opus-4.6-Reasoning-887x` | Adopt with caution |
| `nohurry/Opus-4.6-Reasoning-3000x-filtered` | P1 |
| `Jackrong/Qwen3.5-reasoning-700x` | P2 |
| `PrimeIntellect/NuminaMath` | Reference (pre-2025) |

### `expose_general_python_code`

General Python/code exposure, because the base LLM model is not recommended for programming.

| Dataset | Status |
|---|---|
| `allenai/Dolci-Think-SFT-Python` | Adopt (reasoning-bearing Python) |
| `KodCode/KodCode-V1-SFT-R1` | Adopt a slice (verifiable, ACL 2025) |
| `nvidia/OpenCodeReasoning` | P1 |
| `KodCode/KodCode-V1` | P1 (RL-ready tests) |

### `expose_cadquery_programs`

CadQuery/3D representation exposure so the base LLM model is not blind to CAD — representation
priming, not a generation capability. Must not leak the CAD-QA held-out programs.

| Dataset | Status |
|---|---|
| `ricemonster/NeurIPS11092` | P2 / caution — unverified Gemini 2.0 Flash generation (FT-D17) |
| `BenchCAD/BenchCAD` `code_gen` | Adopt; exclude from the transfer evaluation (shared parts) |
| `kulibinai/cadevolve` | Candidate (2M CadQuery programs) |
| `CADCODER/GenCAD-Code` | P2 (image input) |
| `azizzjr/qwen3-32b-fusion360-98k-v2` | P2 (Fusion360, not CadQuery) |
| `sanjuhs/cadforge-cadquery-agentic-traces` | Study (tiny, our agentic shape) |
| `hhllzz/surprise-3d`, PointLLM/Cap3D, `hiyouga/geometry3k` | P2 (vision) |
| `LiAuto-DSR/GeoGramBench` | Eval only (already ref [10]) |

### `learn_the_cadqa_task`

The CAD-QA task itself: a CAD-QA dataset row → a rule-rendered prompt plus a typed `submit_*`
answer with hop reasoning. This is the comprehension corpus and the dataset contribution; there is
no external equivalent. Its rows carry a **hop tier** (release hops `{2,3,4,5}`; synthesis floors at
`hop≥2`); the first run uses the low-hop end only, and later tiers are added through the measured
advancement gate in `fine-tuning/data.md` §4.1, not by ordering a static dataset. Row generation is
planned and owned in `../../dataset/`; the agent training trace distillation is `fine-tuning/pipeline/02-teacher-sampling.md`.

| Dataset | Status |
|---|---|
| The CAD-QA task dataset (teacher-distilled) | Internal; dataset rows **regenerated** — the current release is superseded — with row generation planned/owned in `../../dataset/`; agent training trace distillation in `fine-tuning/pipeline/02-teacher-sampling.md` |

## Mixed training datasets

A **Mixed training dataset** is `{dataset role → weight}`. Its recipe and weights are owned by
`fine-tuning/data.md` §3; the two (provisional) names are `mixed_dataset_general_and_easy_cadqa`
(first run: 70% general / 30% low-hop `learn_the_cadqa_task`) and `mixed_dataset_full_cadqa_training`
(primary: 50/50, the task share covering the release hop tiers `{2,3,4,5}`).

## Evaluation datasets

Evaluation is the set of datasets that serve H1–H4; each is composed across Difficulty tiers and run
at four points in the training pipeline (baseline, periodic subset, phase-end, final). Each evaluation
dataset is the held-out split that mirrors a training DatasetRole; evaluation dataset roles themselves
are not yet named (`plan.md` §6).

| Serves | Evaluation dataset | Tier |
|---|---|---|
| H2 (thesis number) | CAD-QA held-out (`learn_the_cadqa_task`) | P0 |
| H3, H4 | BenchCAD `qa_code` | P0 (means) |
| H3 | BenchCAD `edit_code` T4/T5 | P1 (end) |
| H3 | Text2CAD-Bench | P1 (end/defect) |
| H3 | Text-to-CadQuery | P1 |
| H3 | CAD-Editor | P1 |
| H1 | Tool-format held-out (`emit_our_tool_call_format`) | P0 |
| guard | General math + code (`preserve_general_math_and_code_reasoning`) | P0 |
| guard | Evaluation-dataset rows (never trained) | P0 |

## Open questions

- **Q2.** What are the two Mixed training dataset names? (Provisional names are used in
  `fine-tuning/data.md` §3 and FT-D19.)
- **Q3.** Do evaluation dataset roles split into `target` / `guard`?

## Resolved questions

- **Q1.** *(2026-10-09)* Which dataset provides `preserve_prior_capabilities`? Answered by FT-D18:
  the role was dropped; there is no dedicated replay role, and the diverse general-task mix anchors
  prior ability (FT-D18 in `fine-tuning/decisions.md`).
