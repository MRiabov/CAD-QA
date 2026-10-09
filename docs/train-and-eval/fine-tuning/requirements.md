# Fine-tuning — requirements (intended vs verified)

**Status:** active, 2026-10-07. This is a summary; the authoritative requirement for each
pipeline stage is its `pipeline/` step doc. Environment facts are marked where they conflict.

## How to read this

Each row states the **intended** requirement for a pipeline stage, whether it is **verified**, and the
evidence. "Verified" means a check ran and passed in this audit (2026-10-07) or is recorded
as a passed run in the repository; everything else is marked. No pipeline stage currently claims an
end-to-end result on an immutable held-out split.

## Intended vs verified by pipeline stage

| Pipeline stage | Intended requirement | Verified? | Evidence |
|---|---|---|---|
| 01 rows-loader | A dataset file maps to decoded CAD-QA dataset rows with the correct `[answer contract]` and decoded gold for every format | **Yes** | 36/36 tests in `train_and_eval/test_rows_loader.py` + `train_and_eval/eval/test_tool_calls.py`; real `release_10k` artifact loads (10,000 rows) |
| 02 teacher-sampling | Kept agent training traces carry a tool call the Query verifier accepts; per-format coverage is complete | No | Code present (`rejection_sample.py`, `teacher.py`); `build_teacher_prompt` unit-tested; `json`/`number` teacher coverage was 0 historically |
| 03 agent training trace normalization | Traces render to the native gemma format | Partial | Rendering primitives verified (`test_render_helpers`, `test_run_code_roundtrip_in_trace_steps`); full `normalize_traces.py` needs the gemma processor |
| 04 SFT | Adapter beats the base LLM model without over-generation | No | Code present (`sft_train.py`); historical 50% / 41.7% on 12 rows; no immutable held-out result |
| 05 GRPO | Reward faithful; policy improves without collapse | Partial | Reward grading unit-tested; training loop unrun; first historical run collapsed at hop 2 |
| 06 harness-modes | Same grading across `no_tools`/`numpy`/`cadquery`; `run_code` round-trip | Partial | Sandbox and compute tool verified offline; full loop needs GPU; `cadquery` mode not implemented |
| 07 serving-vllm | Served checkpoint is numerically equivalent to the merged LLM model | No | Conversion code present; no parity check; throughput smoke exists but uses stale raw-prompt calls |

## Cross-cutting requirements

| Requirement | Intended | Verified? | Evidence |
|---|---|---|---|
| Every LLM call records reasoning + output + tool call distinctly (A5) | Yes | By design, unrun | `AttemptLog` (`rejection_sample.py`) and `EvalRow` (`eval_bench.py`) carry all three; no logged production run was inspected in this audit |
| No silent data loss (rejected rows, failed runs recorded) | Yes | Partial | Sampling log records every attempt; eval writes per-row results; rejected traces are not persisted as a corpus |
| Determinism (seeds, dataset revision, exact command) | Yes | No | Seeds exist (`seed=3407`, `42`, `20260808`) but no run manifest; dataset revisions are HF config names, not hashes |
| Grader must equal the reward | Yes | No | Eval uses `tool_call_matches`; GRPO uses `reward_cadqa` with a different fallback parser; `text` uses substring presence |
| No LLM model in the trusted grading path | Yes | By design, unrun | Grading is exact-match code (`tool_call_matches`, `reward_cadqa`); the teacher only produces SFT traces, not evaluated answers |

## Environment

- **Python:** 3.12 (`uv.lock`; `requires-python >=3.11` in `pyproject.toml`).
- **Package manager:** `uv`. The run-experiments skill and runbooks use a `rtk uv run` wrapper.
- **GPU:** training and eval require a CUDA GPU. No live box exists at this commit
  (`docs/development-context.md`); the 2026-08 runs used a single RTX 4080S 32 GB.
- **Credentials:** `OPENROUTER_API_KEY` (teacher); HF access for `MRiabov/cadqa-rl-2000`.
- **Pins are not in the repo.** The compiled pins live under `runs/gemma_bench/rl/env/`
  (`requirements.path1.txt`, `requirements.rl2/rl5/rl6.txt`), but `runs/` is gitignored
  (`.gitignore`), so they are untracked. The repo cannot reproduce its training environment
  from tracked files.
- **Pins conflict with the narrative.** The untracked pins show `transformers==5.5.0`,
  `trl==0.22.2`, `torch==2.10.0`, `unsloth==2026.4.8` for `path1`, and
  `transformers==4.56.2` with `vllm==0.15.1`/`0.17.0` for `rl5`/`rl6`. The narrative docs
  cite trl 1.9.2 / transformers 5.14.1 / vLLM 0.26. Both cannot be the environment that
  produced the results; `[unknown]` which did.

## What "done" would require

1. The dataset is immutable with tagged revisions; a group-safe held-out split independent of the
   agent training trace set.
2. Every pipeline stage's end-to-end check run and recorded, including parity, sandbox, and
   per-format teacher coverage.
3. SFT **and** GRPO documented as one measured chain (or the two avoided as a chain).
4. Reward and eval grading proven to agree.
5. Run manifests (env pin, seed, dataset revision, command, checksums) for every reported
   number.

## Open questions

- **Q1.** Should the untracked environment pins be moved into the repo (for example
  `train_and_eval/requirements/`) so the environment is reproducible?
- **Q2.** Should there be a single tracked environment for the whole fine-tuning surface, or separate
  SFT and serving environments (the current split is unsloth-stack vs vLLM-stack)?
- **Q3.** Is `docs/_archive/rl_runbook.md` (Unsloth Studio route) still the intended production path, or is
  `train_and_eval/` the only path? `[unknown]`.
- **Q4.** Should Phase 3 swap the base LLM model? External evidence
  (`../../prior-art.md`, "External evidence on fine-tuning small LLM models") says base rank does
  not predict fine-tuned rank and family choice matters less than fine-tuning, so the recorded
  "effort without gain" is more likely a recipe/data problem. Decide whether to fix the recipe
  on gemma-4-E2B first, or run a fixed recipe across 3–4 bases in parallel.

## Resolved questions

None yet.

## Extra deliverables - P2

- A checker that asserts eval grading and GRPO reward agree on a fixture set.
- A run-manifest generator.
