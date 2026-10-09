# Datasets and dataset roles

**Status:** active, 2026-10-09. New. Assigns each dataset to its **DatasetRole** (`../glossary.md`).

**What this doc owns — the dataset → DatasetRole assignment** for training and evaluation. The mix
recipe (dataset role → weight) and the candidate evidence (sizes, licenses, adopt/reject) are in
`fine-tuning/data.md` §2–§3. The assignment here is canonical; change it
here, then propagate.

**Related docs.** `../glossary.md` (**DatasetRole**, **External dataset**, **Mixed training
dataset**, **Training stage**); `./fine-tuning/decisions.md` (FT-D1–D15);
`./evaluation/harness.md` and `./evaluation/baselines.md`; `fine-tuning/data.md`.

## Rules

- Every dataset has exactly one **DatasetRole**.
- Two forms: an **External dataset** (published outside CAD-QA) and a **Mixed training dataset**
  (a blend at fixed weights).
- A dataset enters only with a pinned revision hash and a recorded license (data plan §5). Sizes
  and licenses are survey-time and must be re-verified.
- `learn_the_cadqa_task` is generated internally (data plan §6); it is not an external dataset.
- Held-out and evaluation-dataset rows are hard-excluded from every training dataset (data plan §5).

## Training datasets by dataset role

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

### `preserve_prior_capabilities`

The anti-forgetting anchor: general instruction data replayed so prior ability does not regress.

| Dataset | Status |
|---|---|
| The base LLM model's own instruct mixture | Adopt if published (best anchor) |
| `nvidia/Llama-Nemotron-Post-Training-Dataset` | P1 substitute when the family mixture is closed |
| A small held-out slice of the evaluation dataset's train side | Adopt as a cheap anchor |

**Open:** the dataset is not chosen (data plan §9).

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
| `ricemonster/NeurIPS11092` | Adopt (text → CadQuery) |
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
no external equivalent.

| Dataset | Status |
|---|---|
| The CAD-QA task dataset (teacher-distilled) | Internal; producer TBD (data plan §6; FT-D11, FT-D15) |

## Mixed training datasets

A **Mixed training dataset** is `{dataset role → weight}`. Names are not yet chosen (open question).

| Composition | Feeds |
|---|---|
| `emit_our_tool_call_format` + `preserve_prior_capabilities` | the H1 tool-schema probe |
| `emit_our_tool_call_format` + `run_the_tool_call_loop` + `preserve_general_math_and_code_reasoning` + `learn_the_cadqa_task` + `preserve_prior_capabilities` | H2 (the thesis number) |

## Evaluation datasets by dataset role

Evaluation is the set of datasets that serve H1–H4; each is composed across Difficulty tiers and run
at four points in the training pipeline (baseline, periodic subset, phase-end, final). Dataset roles
are not yet named.

| Serves | Evaluation dataset | Tier |
|---|---|---|
| H2 (headline) | CAD-QA held-out (`learn_the_cadqa_task`) | P0 |
| H3, H4 | BenchCAD `qa_code` | P0 (means) |
| H3 | BenchCAD `edit_code` T4/T5 | P1 (end) |
| H3 | Text2CAD-Bench | P1 (end/defect) |
| H3 | Text-to-CadQuery | P1 |
| H3 | CAD-Editor | P1 |
| H1 | Tool-format held-out (`emit_our_tool_call_format`) | P0 |
| guard | General math + code (`preserve_general_math_and_code_reasoning`) | P0 |
| guard | Evaluation-dataset rows (never trained) | P0 |

## Open questions

- **Q1.** Which dataset provides `preserve_prior_capabilities` (data plan §9)?
- **Q2.** What are the two Mixed training dataset names?
- **Q3.** Do evaluation dataset roles split into `target` / `guard`?
