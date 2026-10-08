# Fine-tuning pipeline — overview

**Status:** active, 2026-10-07. Code lives in `train_and_eval/`. This surface is **being
revised**; it is not frozen.

## Purpose

Define the ordered stages that turn a **dataset file** into a trained LLM model, and
the single contract for the artifacts and fields that pass between those stages.

## Stage map (DAG order)

```text
dataset_generation
   │  dataset file: rows.parquet | rows.jsonl
   ▼
[01 rows-loader] ── decoded CAD-QA dataset rows ──────────────┐
   │                                                         │
   ▼                                                         │
[02 teacher-sampling] ── agent training trace ──▶ [03 trace-normalization]
   │                                              │
   │ sampling log (audit)                         │ normalized text
   │                                              ▼
   │                                         [04 SFT] ── adapter ──▶ (merge, out-of-band)
   │                                                                     │
   │  rows feed GRPO directly (no teacher)                              │ merged model
   ▼                                                                     │
[05 GRPO] ── RL adapter                              [06 harness-modes] ◀─┘ ── eval result
                                                             ▲
                                                      merged model
                                                             │
                                                      [07 serving-vLLM] ── vLLM checkpoint
```

Reading the DAG:

- **SFT and GRPO are parallel consumers of the dataset file, not a chain.** SFT learns from
  **agent training traces** produced by the teacher; GRPO scores sampled completions against the
  **gold answer** directly (`train_and_eval/train/grpo_train.py::reward_cadqa`). The current
  GRPO run does not initialize from the SFT adapter (`train_and_eval/train/grpo_train.py`
  loads `unsloth/gemma-4-E2B-it`), so "SFT then GRPO" is a stated goal, not the implemented
  chain. See [05-grpo.md](05-grpo.md#open-questions).
- **The merge step has no code in this repo.** Producing the **merged LLM model** from the
  **adapter** is described only in `docs/_archive/agent_handoff_2026-08-09.md` section 5
  (`PeftModel.from_pretrained` → `merge_and_unload` → `save_pretrained`). This is a code
  gap; `[unknown]` whether a script ever existed.
- **Rows reach three harnesses unchanged**: teacher sampling, GRPO, and eval all consume the
  same decoded CAD-QA dataset row shape via `train_and_eval/rows_loader.py::load_local_rows`.

## Stage IO contract

Single source of truth for artifact and field names. Step docs must match this table.

### `dataset file`

- **Producer:** `dataset_generation` (today `dataset/`). **Consumers:** 01, 05, 06.
- **Persisted:** `rows.parquet` or `rows.jsonl`.
- **Fields consumed** (`train_and_eval/rows_loader.py::RLRawRow`): `row_id`, `prompt`,
  `answer_format`, `gold_answer` (JSON-encoded string), `logical_hop_count`,
  `difficulty_bucket`, `geometry_hop_count`, `relation_families`; plus `split` and
  `release_ready` used for filtering.
- **Observed `release_10k` schema** (richer than consumed): includes `source_code`,
  `query_program`, `candidate_trace`, `measurement_scopes`, `static_hop_count`,
  `verifier_status`, `clue_map`, `evidence_tier`, `quarantine_reasons`. The fine-tuning
  pipeline reads only the consumed subset.
- The artifact's own contract is owned by the dataset docs, not here.

### `decoded CAD-QA dataset rows`

- **Producer:** 01 rows-loader. **Consumers:** 02, 05, 06.
- **Persisted:** no (in-memory Python `dict` per row).
- **Fields** (`train_and_eval/rows_loader.py::RLRawRow`, `model_dump`): `row_id`, `prompt`
  (with the `[answer contract]` suffix appended when `tool_suffix=True`), `answer_format`,
  `gold_answer` (decoded from its JSON encoding), `logical_hop_count`, `difficulty_bucket`,
  `geometry_hop_count`, `relation_families`.

### `agent training traces`

- **Producer:** 02 teacher-sampling. **Consumer:** 03 agent training trace normalization.
- **Persisted:** JSONL, e.g. `runs/gemma_bench/rl/sft_traces_final.jsonl`,
  `sft_traces_filtered3.jsonl`, `sft_traces_merged.jsonl`; published to HF
  `MRiabov/cadqa-rl-2000` as `sft_traces_v1` / `sft_traces_v2`.
- **Fields** (`train_and_eval/train/rejection_sample.py::Trace`): `row_id`, `hop`,
  `prompt`, `tool_name`, `trace` (flattened reasoning + tool calls + results), `gold`,
  `answer_format`, `compacted`, `prompt_tokens`, `completion_tokens`, `mode`
  (an **LLM harness mode**), `steps` (list of `TraceStep`; emptied when compacted).

### `sampling log`

- **Producer:** 02. **Consumer:** audit only.
- **Persisted:** JSONL, e.g. `sampling_log.jsonl`.
- **Fields** (`train_and_eval/train/rejection_sample.py::AttemptLog`): `hop`, `row_id`,
  `ok`, `parsed`, `tool_valid`, `compacted`, `tokens`, `cost`, `error`, `text`,
  `reasoning`, `tool_call`, `rounds` (list of `RoundLog{text, reasoning, tool_call,
  result}`). This is the A5 record: reasoning, output text, and tool call are distinct.

### `normalized text`

- **Producer:** 03 agent training trace normalization. **Consumer:** 04 SFT.
- **Persisted:** JSONL, e.g. `sft_texts.jsonl`.
- **Fields** (`train_and_eval/train/normalize_traces.py::TRACE_COLUMNS` plus `text`):
  `row_id`, `prompt`, `trace`, `hop`, `tool_name`, `answer_format`, `gold`, `compacted`,
  `mode`, and `text` — one pre-rendered gemma-native conversation string.

### `adapter`

- **Producer:** 04 SFT (`train_and_eval/train/sft_train.py::main` saves LoRA via
  `model.save_pretrained`). **Consumer:** merge step (no code), then 06/07.
- **Persisted:** directory of LoRA weights, e.g. `/root/cadqa-sft-final`.

### `merged model`

- **Producer:** out-of-band merge (no code). **Consumers:** 06, 07.
- **Persisted:** full bf16 directory, e.g. `/root/cadqa-sft-merged`.

### `eval result`

- **Producer:** 06 harness-modes. **Consumer:** analysis / reporting.
- **Persisted:** JSONL, e.g. `eval_heldout.jsonl`.
- **Fields** (`train_and_eval/eval/eval_bench.py::EvalRow`): `row_id`, `answer_format`,
  `gold`, `correct`, `tool_valid`, `tool_name`, `completion_tokens`, `completion`, `capped`,
  `tool_call`, `rounds` (list of `ToolRound{name, arguments, result}`).

### `vLLM checkpoint`

- **Producer:** 07 serving-vLLM. **Consumer:** batched eval / rollout.
- **Persisted:** a converted safetensors directory, e.g. `/root/cadqa-sft-merged-vllm3`.

## Shared tool-call contract

Defined once in `train_and_eval/tool_calls.py`; used by 02, 05, and 06. Step docs describe
how each stage uses it; they do not redefine it.

- **Answer format → tool** (`train_and_eval/tool_calls.py::FORMAT_TO_TOOL`): one **submit
  tool** per format — `candidate_label→submit_label`, `text→submit_text`,
  `integer→submit_integer`, `number→submit_number`, `coordinate→submit_coordinate`,
  `bbox→submit_bbox`, `json→submit_workplane`. Note `json` maps to a *CadQuery workplane* tool,
  not a generic JSON answer.
- **Typed arguments** (`train_and_eval/tool_calls.py::_ARGS_MODELS`) validated by Pydantic.
- **Gold comparison** (`train_and_eval/tool_calls.py::tool_call_matches`): exact for
  strings/ints, `1e-3` relative tolerance for floats (`_REL_TOL`).
- **The `[answer contract]` suffix** (`train_and_eval/tool_calls.py::tool_call_prompt_suffix`)
  tells the LLM model to end with the matching `submit_*` envelope. It is appended by 01 and by
  the teacher prompt (`train_and_eval/teacher.py::build_teacher_prompt`).
- **Non-answer tools**: `run_code` (sandboxed compute, owned by 06) and `compact_trace`
  (agent training trace compression, owned by 02).

## Step docs

| Step | Doc | Code |
|---|---|---|
| 01 | [01-rows-loader.md](01-rows-loader.md) | `train_and_eval/rows_loader.py` |
| 02 | [02-teacher-sampling.md](02-teacher-sampling.md) | `train_and_eval/teacher.py`, `train/rejection_sample.py`, `train/compact_agentic.py`, `train/gen_1hop_queries.py`, `train/export_rl_data.py`, `setup/publish_traces.py` |
| 03 | [03-trace-normalization.md](03-trace-normalization.md) | `train/normalize_traces.py`, `tool_calls.py` (rendering) | <!-- dont-say: allow -->
| 04 | [04-sft.md](04-sft.md) | `train/sft_train.py` |
| 05 | [05-grpo.md](05-grpo.md) | `train/grpo_train.py`, `reward_cadqa.py` |
| 06 | [06-harness-modes.md](06-harness-modes.md) | `eval/eval_bench.py`, `run_code_sandbox.py`, `tool_calls.py` (compute tool) |
| 07 | [07-serving-vllm.md](07-serving-vllm.md) | `setup/convert_for_vllm.py`, `eval/bench_vllm.py` |

## Open questions

- **Base LLM model identifier is inconsistent.** Code loads `unsloth/gemma-4-E2B-it`
  (`train_and_eval/train/sft_train.py::main`,
  `train_and_eval/train/grpo_train.py`), while the GRPO docstring says
  `google/gemma-4-E2B-it`. Which repo is canonical? `[unknown]`.
- **Dataset config is inconsistent across consumers.** 02 samples HF `v3_curriculum`
  (`train_and_eval/train/rejection_sample.py::Sampler.run`), 05 defaults to `v2_curriculum`
  (`train_and_eval/train/grpo_train.py`), 06 defaults to `v3_curriculum`
  (`train_and_eval/eval/eval_bench.py::main`). v2 has no 1-hop; v3 does. See the GRPO doc.
- **Hop-curriculum mismatch.** The teacher quotas and v3 include hop `1`
  (`train_and_eval/train/rejection_sample.py::DEFAULT_QUOTAS`), but the GRPO curriculum
  shares omit hop `1` and include hop `4`
  (`train_and_eval/train/grpo_train.py::HOP_SHARES`). The stated "0→1→2→3→5 ladder" is not
  what the GRPO code schedules.
- **No code produces `merged model`.** Name the stage, script it, or mark it out-of-scope.

## Resolved questions

_(none yet)_

## Extra deliverables - P2

- A runnable WHAT layer (`pipeline/streamlined/`) with `READ → TRANSFORM → WRITE` per step,
  per `plans/oct-7/restructure-docs.md` D14.
- A single orchestrator (the run-experiments skill references absent `scripts/` and
  `configs/`; see `docs/development-context.md`).
