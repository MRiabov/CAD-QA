# Fine-tuning pipeline

**Status:** active, 2026-10-07. Code is `train_and_eval/` (to become `fine_tuning/` per the
repo restructure). This surface is **being revised**; the docs describe behaviour and record
known defects as open questions rather than implying the pipeline is finished.

This directory documents how CAD-QA turns a **rows artifact** into a trained small model and
evaluates it: teacher **rejection sampling** → **trace normalization** → **SFT**; **GRPO**
training; the **harness modes** used for evaluation; and **vLLM** serving.

## Start here

1. [requirements.md](requirements.md) — intended-vs-verified summary, environment, what "done"
   would need.
2. [pipeline/00-overview.md](pipeline/00-overview.md) — the DAG and the stage IO contract
   (the single source for artifact and field names).
3. The step docs, in DAG order (below).
4. [decisions.md](decisions.md) — unit-level decisions (ADR format).

Supporting context: `../PRD.md` (the research contract), `../glossary.md` (canonical terms),
`../development-context.md` (as-of snapshot and history).

## Stage index

| Step | Doc | Status | Code |
|---|---|---|---|
| B1 | [01-rows-loader.md](pipeline/01-rows-loader.md) | `verified` | `train_and_eval/rows_loader.py` |
| B2 | [02-teacher-sampling.md](pipeline/02-teacher-sampling.md) | `[unverified — needs OPENROUTER_API_KEY + network]` | `teacher.py`, `train/rejection_sample.py`, `train/compact_agentic.py`, `train/gen_1hop_queries.py`, `train/export_rl_data.py`, `setup/publish_traces.py` |
| B3 | [03-trace-normalization.md](pipeline/03-trace-normalization.md) | `[unverified — needs unsloth gemma-4 processor]` | `train/normalize_traces.py`, `tool_calls.py` (rendering) |
| B4 | [04-sft.md](pipeline/04-sft.md) | `[unverified — needs GPU + unsloth/trl]` | `train/sft_train.py` |
| B5 | [05-grpo.md](pipeline/05-grpo.md) | `[unverified — needs GPU + unsloth/trl]` | `train/grpo_train.py`, `reward_cadqa.py` |
| B6 | [06-harness-modes.md](pipeline/06-harness-modes.md) | `[unverified — needs GPU + merged model]`; `cadquery` not implemented | `eval/eval_bench.py`, `run_code_sandbox.py` |
| B7 | [07-serving-vllm.md](pipeline/07-serving-vllm.md) | `[unverified — needs vLLM + GPU + merged checkpoint]` | `setup/convert_for_vllm.py`, `eval/bench_vllm.py` |

## Current state at a glance

- The strongest measured result is **directionally encouraging but statistically unusable**:
  native-format SFT reached 50% accuracy / 58.3% tool-valid on **12** held-out rows; the
  post-gold-fix re-run was 41.7% / 75% on the same 12 (`../development-context.md`).
- **Known defects are open questions**, not hidden. The load-bearing ones: SFT prompt masking
  unknown; GRPO entropy collapse history; vLLM parity unverified; `cadquery` harness
  unimplemented; `json`/`number` teacher coverage zero; reward and eval graders can diverge.
- There is **no live GPU box**; historical runs used a single RTX 4080S.

## Code ↔ doc map

- `train_and_eval/rows_loader.py` → B1
- `train_and_eval/teacher.py`, `train/rejection_sample.py`, `train/compact_agentic.py`,
  `train/gen_1hop_queries.py`, `train/export_rl_data.py`, `setup/publish_traces.py` → B2
- `train_and_eval/train/normalize_traces.py`, `tool_calls.py` (rendering) → B3
- `train_and_eval/train/sft_train.py` → B4
- `train_and_eval/train/grpo_train.py`, `reward_cadqa.py` → B5
- `train_and_eval/eval/eval_bench.py`, `run_code_sandbox.py`, `tool_calls.py` (`HarnessMode`,
  `execute_code`) → B6
- `train_and_eval/setup/convert_for_vllm.py`, `eval/bench_vllm.py` → B7
- `train_and_eval/tool_calls.py` (the typed tool contract) → shared; defined in
  [pipeline/00-overview.md](pipeline/00-overview.md#shared-tool-call-contract)
- Tests: `train_and_eval/test_rows_loader.py`, `train_and_eval/eval/test_tool_calls.py`

## Terms

Use the canonical vocabulary in `../glossary.md`. The three easily-confused "trace" terms:
an **agent training trace** is an agent-facing reasoning + tool-call record (this pipeline's SFT
signal); a **CAD query trace** is a source's recorded CadQuery execution; a **candidate
trace** is a row's candidate-narrowing record.

## Note on raw material

`../agent_handoff_2026-08-09.md`, `../rl_progress_2026-08-09.md`,
`../rl_checkpoint_2026-08-08.md`, `../rl_checkpoint_2026-08-09_2.md`,
`../rl_state_2026-08-09_1140.md`, `../rl_runbook.md`, and `../text_finetune_runbook.md` are
**raw material** for these docs, not current specs. They are superseded by this directory.
