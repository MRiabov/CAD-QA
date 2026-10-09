# Development context

**As of:** 2026-10-07. This records where the project actually is: what exists, what is
proven, what is assumed, and what is missing. Everything is either evidence or explicitly
marked (`[unknown]`, `[unverified — needs <env>]`, `[assumed]`).

## Repo identity

- Remote: `https://github.com/MRiabov/CAD-QA.git`.
- Primary checkout: this repo, branch `main`, commit `512a514` (2026-08-09).
- **Local `main` is ahead of `origin/main` (`e89838d`, 2026-08-08).** The Aug 8–9
  fine-tuning work is committed locally but never pushed.

## History

| When | What | Artifact |
|---|---|---|
| 2026-04-29 | Graph-first reset: one CAD ontology + a deterministic query and Query verifier replaces the old split between "core", "graph query", and "multi-hop" | `overnight-task.md`, `specs/` |
| 2026-05 → 06 | Dataset builder: CadQuery program ingestion, CadQuery tracing, CAD ontology graph, query synthesis/resolver, prompt rendering, release gates | `dataset/` (now `dataset_generation/`), `docs/_archive/implementation_status.md` (retired) |
| 2026-06 → 07 | Harbor export, cloud runners, provider pinning | `dataset/harbor.py`, `docs/_archive/harbor.md` |
| 2026-08-08 | First gemma-4-E2B baseline: rc10 (0-hop) 30%, release10k (2–5 hop) 14% | `docs/experiments/2026-08-08-gemma-e2b-bench.md` |
| 2026-08-08/09 | Teacher rejection sampling, SFT, native tool-call format fix, 1-hop bridge, `run_code` sandbox, harness modes, a vLLM conversion | `train_and_eval/`, `docs/_archive/rl_*.md`, `docs/_archive/agent_handoff_2026-08-09.md` |
| 2026-08-09 | Last commit | `512a514` |

## Motivation — the EngineerBench origin

**Status:** first-hand, `[own, unbacked]`, recorded 2026-10-09. Motivation, not evidence.

CAD-QA grew out of **EngineerBench** (`github.com/MRiabov/EngineerBench`), an earlier construction
benchmark. While building it (roughly 2026-H1, 6–8 months before 2026-10), proprietary LLM models
consistently failed to:

- make proper shapes;
- use anything beyond boxes;
- make non-overlapping shapes;
- reason about dimensions in CAD.

Indicative pass rate was about **10%**, with a consistent shape in **under 40%** (not 50%).

**Stale and unbacked.** These numbers are first-hand and are not reproducible from tracked
artifacts, and they are **stale**: the frontier moved from about 0.3 to **0.95+** on BenchCAD in
roughly six months, so a 2026-H1 construction estimate does not describe today's LLM models. Use them
as history, not as a result.

**Why CAD-QA.** EngineerBench could not separate "the LLM model reasoned incorrectly" from "the
LLM model failed to execute", so CAD-QA removes construction from the loop: it is no-kernel and
code-comprehension. The long-run aim is that training comprehension **improves generation and
prevents invalid or overlapping geometry** — the original EngineerBench failure modes. That is why
the external transfer suite targets both comprehension (BenchCAD `qa_code`) and construction /
defect (`edit_code`, text-to-CAD).

## Components

**Dataset generation** (`dataset/`): CadQuery program ingestion
(`source.py`), CadQuery tracing (`trace.py`), CAD ontology extraction (`ontology/`), query
synthesis and resolution (`query/`), prompt rendering (`prompts/`), materialize/validate/
release (`dataset/`), Harbor export (`harbor.py`), CLI (`cli.py`).

**Fine-tuning and evaluation** (`train_and_eval/`): row loading
(`rows_loader.py`), the typed tool contract (`tool_calls.py`), the teacher
(`teacher.py`), rejection sampling (`train/rejection_sample.py`), agent training trace normalization
(`train/normalize_traces.py`), SFT (`train/sft_train.py`), GRPO (`train/grpo_train.py`,
`reward_cadqa.py`), the eval harness (`eval/eval_bench.py`), and the vLLM conversion
(`setup/convert_for_vllm.py`).

**Data** (`MRiabov/cadqa-rl-2000` on HuggingFace): `v2_curriculum` and `v3_curriculum`
(1,445 rows; hops `{0:100, 1:342, 2:374, 3:291, 5:338}`), `sft_traces_v1` (275 traces),
`sft_traces_v2` (308 traces).

## Proven

- Base gemma-4-E2B, `no_tools` LLM harness: rc10 (0-hop) 30/100; release10k (2–5 hop) 14/100
  (`docs/experiments/2026-08-08-gemma-e2b-bench.md`).
- Native-format SFT: 50% accuracy / 58.3% tool-valid on **12** held-out rows; the earlier
  non-native format scored 16.7% on the same rows.
- Post-gold-encoding-fix re-run on the same 12 rows: 41.7% / 75% (movement is ±1–2 rows).
- Cost-effective models on the rc10 clean-100 slice (0-hop, easy): Mimo 65%, DeepSeek 63%,
  Kimi 59%.

The 12-row result is directionally encouraging but statistically unusable; do not quote it
as a headline number.

## Tool-call and answer-submission format churn

Answer submission was changed twice in the Aug-2026 push, and the first choice was
**incompatible with the base LLM model's pretrained tool tokens**. Recorded because this is a
recurring failure mode, not a one-off.

- **Foreign JSON envelope (first SFT).** The first agent training traces and the eval harness
  taught an OpenAI-style JSON tool-call envelope, which the gemma-4 base LLM model was not
  pretrained to emit. The base LLM model rambled and rarely produced a parseable call;
  held-out accuracy on the 12-row set was 16.7%
  ([FT-D3](train-and-eval/fine-tuning/decisions.md#ft-d3--native-gemma-tool-call-format-not-an-openai-json-envelope)).
- **Native format (fix).** Rendering the base LLM model's own tool-call tokens
  (`<|tool_call>call:<name>{args}<tool_call|>`, `<|tool_response|>`) raised the same 12-row
  accuracy to 50% / 58.3% tool-valid (`experiments/`, `_archive/agent_handoff_2026-08-09.md`).
- **`json` is not generic JSON.** The `json` Answer format maps to `submit_workplane`, a CadQuery workplane tool
  (`train_and_eval/tool_calls.py::FORMAT_TO_TOOL`), so "answer as JSON" is misleading in the contract
  ([FT-D4](train-and-eval/fine-tuning/decisions.md#ft-d4--one-typed-submit-tool-per-answer-format)).
- **`boolean` is declared but unrouted.** `boolean` is listed as an Answer format in
  `glossary.md` but has no entry in the typed tool contract, so a boolean CAD-QA dataset row
  would fail at load or eval
  ([open question](train-and-eval/fine-tuning/pipeline/01-rows-loader.md#open-questions)).

**Lesson.** The answer-submission format is a property of the base LLM model, not of CAD-QA. It
must be re-derived for each base LLM model and cannot be assumed to transfer. For LFM2.5 the
native tokens are `<|tool_call_start|>` / `<|tool_call_end|>` with **Pythonic** calls by default
(JSON only when the system prompt asks), so the gemma `<|tool_call>` rendering does not carry
over ([FT-D11](train-and-eval/fine-tuning/decisions.md#ft-d11--start-phase-3-on-the-liquid-ai-lfm25-stack);
Liquid tool-use docs).

## Assumed or unverified

- `[unverified]` **vLLM.** The engine loads a hand-converted checkpoint (weight rename plus
  a `k_norm` mapping) at high throughput, but there is no transformers-vs-vLLM output
  parity check. The `k_norm` mapping may be wrong, which would contaminate every vLLM
  number.
- `[unverified]` **SFT is reasoning-preserving.** Four epochs over 268 traces, no evidence
  of prompt masking. Eval completions over-generated; GRPO collapsed to 2-token completions
  with near-zero entropy. Both point at a rigid, imitation-heavy signal.
- `[unverified]` **Grader correctness** beyond the oracle-key path.
- `[unverified]` **`run_code` sandbox isolation** (no network, timeout, no CadQuery).
- `[assumed]` **The 1,445-row curriculum is "ready."** It does not pass the repo's own
  `benchmark-release` gates (scale, split-group coverage, parameter balance).
- `[assumed]` **Hard-slice (3+ hop) big LLM model numbers meet the paper's ≤30% target.** Not
  recorded anywhere found.
- `[unverified]` **Prompt clarity.** Public prompts are rule-rendered from LLM-authored
  templates (`prompt-templates.yaml`), and the owner — reading as a human — cannot always
  tell what a rendered question is actually asking. A benchmark question that is unclear to
  a careful human reader is a defect, not just awkward wording.

## Gaps and risks

1. **Trust gap (primary).** The code is undocumented as executed behaviour; claims are not
   reproducible. Phase 0 (the audit) exists for this.
2. **Dataset scale.** 1,445 rows versus the spec's 10,000; small hard slices make held-out
   results noisy.
3. **Reasoning collapse.** The training signal taught what to output, not how to think.
4. **Serving correctness.** vLLM conversion unverified.
5. **Missing orchestrator.** The run-experiments skill references `scripts/` and `configs/`,
   which do not exist at this commit. The real path is the `train_and_eval/` scripts, which
   are undocumented.
6. **Environment rot.** No live GPU box; the Aug-2026 stack (unsloth git-main, trl 1.9.2,
   transformers 5.14.1, vLLM 0.26) is unverified today.
7. **Paper integrity.** No results, no figures.
8. **Sloppy generated text in the dataset itself.** The same LLM sloppiness that made the
   docs hard to read also went into the dataset artifact: the prompt templates and their
   rendered questions (`prompt-templates.yaml` — `clause_templates`, `metric_labels`,
   `aggregation_templates`, `tie_break_templates`) are not reliably clear, and the owner, as
   a reader, often cannot tell what a question is asking. This ships in every public prompt,
   so it is a benchmark-validity problem, not a style one: an ambiguous question cannot
   fairly judge an answer. Needs a clarification pass (rewrite to unambiguous wording, then
   re-render and re-check) before the benchmark is immutable. Tracked in
   `_audit/owner-audit-todo.md` (E5).
9. **Fine-tuning surface is being replaced.** Most of `train_and_eval/` — teacher, rejection
   sampling, agent training trace normalization, SFT, GRPO, evaluation, serving — is expected to
   be deleted in Phase 3, keeping only the rows loader and the typed tool/answer contract
   ([FT-D12](train-and-eval/fine-tuning/decisions.md#ft-d12--the-phase-3-rewrite-retains-only-the-loader-and-the-typed-tool-contract)).
   The component list above is the 2026-08 state, not the target.

## Environment

- No live GPU instance. The last box and its checkpoints are gone `[assumed]`.
- Package manager `uv`; Python 3.12 (`uv.lock`).
- A local `.env` holds the OpenRouter key `[assumed]`.
- **Environment pins are untracked and conflict with the narrative.** The compiled pins
  live under gitignored `runs/gemma_bench/rl/env/` (for example `transformers==5.5.0`,
  `trl==0.22.2`, `torch==2.10.0`, and `vllm==0.15.x`/`0.17.x`), while the RL/SFT docs cite
  `trl 1.9.2`, `transformers 5.14.1`, and `vLLM 0.26`. Which stack produced the recorded
  results is `[unknown]`; the repo cannot reproduce its training environment from tracked
  files. See `train-and-eval/fine-tuning/requirements.md`.
