# Trust audit plan (Phase 0)

**Status:** active, 2026-10-08. Implements **Phase 0 — Trust audit** of
`docs/development-plan.md`. The owner-facing checklist is
`docs/_audit/owner-audit-todo.md` (group C); this plan is the program that closes it.

## Goal

Prove what the code actually does, so that every number produced later — baseline, training,
serving — is trustworthy, without spending GPU budget. Concretely: give every load-bearing
component a status (`verified`, `stale`, `missing`, `blocked`) backed by a recorded command
and a preserved artifact, and leave one runnable verification command per pipeline stage.

**Gate** (from `docs/development-plan.md`): every load-bearing component is `verified` or
explicitly `blocked`; no GPU budget is spent before the offline ledger is green.

## What "verified" means

A component is `verified` only when all of these hold:

1. A check **ran and passed** — not "the code exists".
2. It ran against a **immutable fixture or a named dataset revision**.
3. The **exact command** is recorded in the owning doc's `## Verification`.
4. The **artifact** (metrics, test output, report) is preserved and cited.
5. The status tag in the owning doc is promoted; a passing check is the only way up.

Anything else stays `exists` / `stale` / `missing` / `[blocked — needs <env>]`. Status tags are
defined in `docs/docs-conventions.md`.

## Scope and non-goals

**In scope:** the load-bearing claims under **Audit units** — grading and reward, the
`run_code` sandbox, serving parity, the training chain, environment and dataset
reproducibility, the dataset pipeline stages (A1–A7), and benchmark validity (prompt
clarity).

**Out of scope:** redesign and new capability. The audit **measures and records**; fixing a
defect it finds is a Phase 1/3 task or a decision taken in this plan. The audit does not
re-litigate decisions already recorded in `dataset/decisions.md`,
`train-and-eval/fine-tuning/decisions.md`, or the restructure plan.

## Method

- **Unit per claim.** One row per load-bearing claim: the claim, its code/artifact, the
  check, the evidence, the status. Not one row per file.
- **Offline first.** Every check that can run without a GPU runs first and is committed as a
  test or a `tools/` command. `uv run` locally; the run book's `rtk uv run` wrapper on the box.
- **Fixture first.** Checks assert on a small immutable fixture (a handful of rows covering every
  answer format) rather than the live dataset, so they are fast and deterministic.
- **GPU-gated checks are scripted, not skipped.** Parity and the SFT re-run are written now,
  marked `[blocked — needs GPU]`, and skip cleanly without CUDA. Running them is the **first
  authorized GPU spend**, after the offline ledger is green.
- **Evidence ledger.** Statuses, commands, and artifacts live in one ledger,
  `docs/_audit/trust-audit-ledger.md`, promoted to the thesis validation appendix at Phase 5.
  Each expensive run also gets a dated `docs/experiments/` record.
- **Findings become fixes.** A doc/code or check/code conflict is a finding: record it, fix one
  side, note it in the progress log. Never silently edit a doc to match a bug.

## Audit units

### A. Grading and reward (C1, C2)

| ID | Claim to verify | Code / artifact | Check | GPU |
|---|---|---|---|---|
| TA-A1 | The Query verifier's grader returns the gold answer exactly (accuracy 1.0) on the oracle key path | `cad_qa/evaluation/grade.py::grade_public_private`; `cad_qa/evaluation/parse.py::parse_answer` | immutable public/private fixture + gold submission → `grade_public_private`; assert accuracy 1.0 | no |
| TA-A2 | The grader agrees on **wrong** answers and on edge encodings (decomposed `cq.Plane` text, float formatting, whitespace), not only on the gold | same | fixture of near-miss and formatting variants; assert each verdict | no |
| TA-A3 | Eval grading and the GRPO reward agree | `train_and_eval/tool_calls.py::tool_call_matches` vs `train_and_eval/reward_cadqa.py::reward_cadqa` | parametrized fixture over every answer format, including the known divergences: `text` substring (`_reward_one`: `gold_str in pred`), float tolerance (`1e-6` absolute vs `1e-3` relative), and `boolean` (in the reward, absent from the typed contract) | no |
| TA-A4 | The Harbor grader and the local grader give identical verdicts | `cad_qa/evaluation/grade.py` / `parse.py` vs `train_and_eval/tool_calls.py` | shared fixture through both paths (promotes the harness P2 "Query verifier parity" item into the audit) | no |

### B. `run_code` sandbox (C3)

| ID | Claim to verify | Code / artifact | Check | GPU |
|---|---|---|---|---|
| TA-B1 | `run_code` cannot reach the network, cannot import `cadquery` / `os` / `subprocess` / `socket`, writes no files, and is timeout-bounded | `train_and_eval/run_code_sandbox.py`; `train_and_eval/tool_calls.py::execute_code` | `uv run pytest train_and_eval/eval/test_tool_calls.py -k "run_code or execute_code" -q`, plus a new explicit no-network assertion | no |
| TA-B2 | "Accidental-misuse guard, not a security boundary" is acceptable for the stated threat model | D-E3 (`train-and-eval/evaluation/harness.md`) | owner decision, not a check | decision |

### C. Serving parity (C4)

| ID | Claim to verify | Code / artifact | Check | GPU |
|---|---|---|---|---|
| TA-C1 | A served vLLM checkpoint is numerically equivalent to the transformers model it was merged from (greedy parity on a fixed prompt set) | `train_and_eval/setup/convert_for_vllm.py`; `train_and_eval/eval/bench_vllm.py` | new parity test (same prompts, compare argmax tokens / logprobs at tolerance); skips without CUDA | yes |
| TA-C2 | Conversion is asserted, not hand-checked: the output key set matches vLLM's Gemma4 expectation and `unique_kv_layers` is read from the checkpoint config | `train_and_eval/setup/convert_for_vllm.py::main` | offline assertion on a tiny fixture checkpoint; remove the hardcoded `15` | no |
| TA-C3 | The smoke script measures the converted checkpoint with `llm.chat` (not raw string prompts against the base model) | `train_and_eval/eval/bench_vllm.py` | code fix + re-record throughput | yes |

### D. Training chain (C5–C7)

| ID | Claim to verify | Code / artifact | Check | GPU |
|---|---|---|---|---|
| TA-D1 | Is the SFT prompt masked (completion-only loss)? | `train_and_eval/train/sft_train.py::main` (`build_dataset`) plus the trainer/collator default | trace the labels the trainer sees on a tiny CPU run; record masked vs unmasked | no |
| TA-D2 | A tracked step produces the merged model from the adapter | none today (documented gap) | write `train_and_eval/setup/merge_adapter.py` + a test, or record the manual step and mark the stage | no |
| TA-D3 | Confirm GRPO loads the base model, not the SFT adapter, and record the intended chain | `train_and_eval/train/grpo_train.py` | code inspection; decide SFT→GRPO vs parallel consumers | no |
| TA-D4 | Consumers agree on the dataset config and the hop curriculum | stage 02/05/06; `HOP_SHARES`, `DEFAULT_QUOTAS` | code inspection; pick v2 or v3 and one ladder; record a decision (feeds Phase 1) | no |
| TA-D5 | One canonical base LLM model identifier | `sft_train.py`, `grpo_train.py` (`unsloth/` vs `google/`) | code inspection; pick one | no |

### E. Reproducibility and environment (C8, C9)

| ID | Claim to verify | Code / artifact | Check | GPU |
|---|---|---|---|---|
| TA-E1 | The environment that produced the recorded results is reproducible from tracked files | `runs/gemma_bench/rl/env/*` (untracked) | move the pins under `train_and_eval/requirements/`; prove tracking with `git check-ignore`; reconcile the cited vs compiled versions | no |
| TA-E2 | Dataset revisions are pinned to hashes, not config names | HF `MRiabov/cadqa-rl-2000` | resolve the `revision` for each config; record in a tracked file | net |
| TA-E3 | Every reported number has a run manifest (env, seed, dataset revision, command, checksums) | none today | build the generator (fine-tuning P2, promoted to audit P1) | no |

### F. Dataset pipeline (A1–A7 and cross-stage)

| ID | Claim to verify | Code / artifact | Check | GPU |
|---|---|---|---|---|
| TA-F0 | The audit environment imports the generation stack | `.venv` | `uv sync`; `uv run python -c "import cadquery, pyarrow"` | no |
| TA-F1–F7 | Each stage A1–A7 meets its stated requirement on a immutable small slice | `cad_qa/` (immutable) | the per-stage command in `docs/dataset/requirements.md`; capture the artifacts | no |
| TA-F8 | The trusted path contains no LLM model or network call | `cad_qa/` | search `cad_qa/` for `openrouter`, `requests`, `httpx`, `openai` | no |
| TA-F9 | Public rows never expose a private Query verifier field | `cad_qa/dataset/public.py::PUBLIC_FIELDS` | `uv run cadqa dataset export-public-private` and inspect the report | no |

### G. Regression floor

| ID | Claim to verify | Code / artifact | Check | GPU |
|---|---|---|---|---|
| TA-G0 | rows-loader and tool-call contract tests pass | `train_and_eval/rows_loader.py`, `tool_calls.py` | `uv run pytest train_and_eval` (36 passed, 2026-10-07) — C10, done | no |
| TA-G1 | The dataset test suite is green | `tests/test_graph_first_pipeline.py` | 5 failures today (2 flaky, 3 stale prompt-text / `validate_rows`); decide fix-test vs fix-template | no |

### H. Benchmark validity

| ID | Claim to verify | Code / artifact | Check | GPU |
|---|---|---|---|---|
| TA-H1 | Every public prompt is unambiguous to a careful human reader | `prompt-templates.yaml`; `cad_qa/prompts/render.py` | owner reads rendered samples per family; an unclear question is a defect; the resulting pass is the Phase 1 freeze gate | no |

## Deliverables

1. `docs/_audit/trust-audit-ledger.md` — the status ledger: one row per unit above (claim,
   command, evidence, status).
2. `tests/audit/` — the offline checks: grading/reward agreement, sandbox no-network,
   conversion assertion, and GPU parity tests that skip without CUDA.
3. `train_and_eval/requirements/` — tracked pins plus a dataset-revision file; a run-manifest
   generator.
4. `train_and_eval/setup/merge_adapter.py` — the missing merge step, or a recorded gap.
5. Updated `## Verification` and `## Current status` in every pipeline step doc, carrying the
   command that was actually run.
6. A findings list feeding Phase 1/3 (grader unification, prompt masking, config/hop
   reconciliation, prompt clarity).

## Ordering and parallelism

- **Wave 1 (offline, parallel):** A, B, C2, D1–D5, E1, E3, F0–F9, G1. Units are independent;
  fan out to subagents where a unit is self-contained.
- **Wave 2 (network, small):** E2 (HF revision pin).
- **Wave 3 (GPU — the first authorized spend, after Wave 1 is green):** C1, C3, and the SFT
  re-run; each becomes a dated `docs/experiments/` record.
- A unit's status is updated only with its evidence; the ledger is committed as units land.

## Acceptance criteria (the gate)

1. Every unit above has a status in the ledger: `verified`, or `blocked` with an explicit
   reason (for example `[blocked — needs GPU]`).
2. Every pipeline stage has a real `## Verification` command that reproduces its status.
3. Grading is trustworthy: oracle identity passes, the grader is correct off the oracle path,
   and eval / reward / Harbor agree on the fixture — or the divergence is a recorded,
   scheduled fix.
4. `run_code` isolation is either proven for the stated threat model or explicitly accepted as
   out of scope by decision.
5. The environment is reproducible from tracked files; every dataset revision is a hash.
6. The `tests/` and `train_and_eval/` suites are green.
7. No GPU budget was spent before the offline ledger was green.

## Decisions

- **D-TA1 — Evidence lives in a throwaway ledger, promoted later.** Statuses, commands, and
  artifacts go in `docs/_audit/trust-audit-ledger.md`; the canonical version becomes the
  thesis validation appendix (Phase 5). Rationale: the ledger churns; `_audit/` is excluded
  from lint.
- **D-TA2 — GPU-gated checks are scripted and `blocked`, not skipped.** Rationale: the Phase 0
  rule forbids unscheduled GPU spend, so a written, skipping test is the deliverable and
  running it is the first authorized spend.
- **D-TA3 — The audit measures grader divergence; unifying grading is a separate decision.**
  Rationale: `grade_public_private`, `tool_call_matches`, and `reward_cadqa` are three
  implementations by design (D-E2); the audit quantifies disagreement, then we decide.
- **D-TA4 — Fixtures are immutable and format-complete.** One small fixture covering every answer
  format is the unit of grading trust and is committed with the checks.
- **D-TA5 — The audit writes no behaviour change to the immutable `cad_qa/`.** Findings against
  the generation package are recorded for Phase 1; only tests, commands, and docs are added
  now.

## Open questions

- Is "no network, no files, timeout" a sufficient sandbox claim, or is kernel isolation
  required before any external claim (TA-B2)?
- Parity precision: argmax token ids, or logprobs within a tolerance (TA-C1)?
- Which environment is canonical: one tracked stack, or separate SFT and serving environments
  (see `train-and-eval/fine-tuning/requirements.md#environment`)?
- Does the GPU parity + SFT re-run happen in Phase 0 (the first spend) or at the top of
  Phase 1?

## Progress log

- **2026-10-08** — plan authored. Nothing run yet; the ledger is empty. Baseline:
  `train_and_eval` 36 passed; `tests/test_graph_first_pipeline.py` 5 failed.
