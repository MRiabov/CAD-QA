# Fine-tuning and evaluation — testing

**Status:** active, 2026-10-10. New. Defines the integration and end-to-end tests for the training
pipeline and the local evaluation harness. It closes audit findings **LE-2** (no end-to-end test of our
own pipeline), **LE-4** (the supervised target and masking were untested), and **LE-5** (truncation was
untested) in [`plans/oct-10/llm-engineering-audit.md`](../../../plans/oct-10/llm-engineering-audit.md).

**Related docs.** [`training.md`](training.md) §2 (cookbook-first) and §7 (the P0 list);
[`system.md`](system.md) §7 (the `TrainingExample` record and converter);
[`pipeline/00-overview.md`](pipeline/00-overview.md) (the IO contract these tests pin);
[`../evaluation/plan.md`](../evaluation/plan.md) §4 (the one scorer);
[`../datasets.md`](../datasets.md) (DatasetRole); [`../../../tests/`](../../../tests/) (where the
tests live).

## The rule

> "I need to see at least one E2E test per one major feature (epic). E2E tests constitute: everything but
> external/paid mocked (DB, all code is not mocked)." — `AGENTS.md`

The fine-tuning + evaluation work is one epic. It is not accepted until:

1. every pipeline stage (01–07) has an adversarial **integration** test on its happy path, written
   **test-first**, pinning each pipeline stage's typed contract before that pipeline stage is implemented; and
2. one **full-DAG E2E test** runs loader → teacher → preparation → SFT → RL-readiness gate → evaluation
   on a 5-row fixture through the production code, with only external/paid mocked.

## What "everything but external/paid" means here

**Mocked (external/paid only):**

- the **teacher LLM provider** — a payload-aware scripted client returning schema-valid agent training
  traces the Query verifier accepts, plus at least one deliberately wrong agent training trace that
  **must** be rejected;
- the **External datasets** — pinned local slices of the tool-format, tool-loop, reasoning, Python, and
  CadQuery corpora, not live Hub pulls;
- **weights** — CI downloads **no weights**: the masking/tokenization layers need only the LFM2.5
  tokenizer + chat template (a few MB). Only the local GPU smoke (layer 6) loads a real checkpoint — the
  cookbook's LFM2.5-350M (350M **parameters**, ~0.7 GB in bf16), not 350 MB;
- the **served policy** during the RL-readiness gate — scripted completions, not a live vLLM endpoint.

**Real (never mocked):**

- the Dataset file fixture (`rows.parquet`) and the loader;
- the `TrainingExample` converter, the LFM2.5 chat template, and the tokenizer;
- the **one scorer** (evaluation, rejection sampling, reward);
- the persisted artifacts (Liquid `messages` Parquet/JSONL, the sampling log, the RL-readiness gate
  output);
- contamination/dedup, the coverage gate, and the serving parity harness;
- the trainer **code path** — a 1-step CPU run on the tiny LLM model.

## Test layers

| Layer | What it is | Mocked | Real | Acceptance |
|---|---|---|---|---|
| 1. Per-pipeline-stage adversarial integration | one pipeline stage (01–07) on adversarial happy-path inputs; asserts the durable output | teacher, External datasets, weights, served policy | the loader/converter/template/tokenizer/scorer, the artifacts | required per pipeline stage |
| 2. Failure-mode | proves a pipeline stage records a **typed failure** and a re-run recomputes only that pipeline stage | as layer 1 | as layer 1 | required per pipeline stage |
| 3. Full-DAG E2E | the 5-row fixture through the production code, stages 01–07 | as layer 1 | everything else | **the epic's E2E test** |
| 4. Masking/truncation fixture (CPU) | the LFM2.5 template + tokenizer assert assistant-only loss and target survival | weights | template, tokenizer | required (LE-4/LE-5) |
| 5. Real-teacher eval (not CI) | 3× real teacher on immutable rows; records the sampling log | nothing | real teacher provider | local only; CI never runs it |
| 6. GPU smoke (skipped without GPU) | a few real SFT steps on the tiny LLM model | teacher | trainer, GPU | skipped in CI |

Layers 1–4 are **CPU-only** and run on a laptop; layer 6 is the only GPU-shaped one and skips cleanly.
(Layer 4 is the LE-2 answer: the load-bearing assertions need no GPU.)

## The fixture and seeding contract

- a **5-row CAD-QA dataset fixture**, immutable, pinned by revision, covering at least one row per Answer
  format — `candidate_label`, `coordinate`, `text`, `number`, `integer`, `boolean`, `bbox`, and `json`
  (the `submit_workplane` tool) — so the format the legacy pool never covered is exercised;
- a **scripted teacher** keyed by prompt, returning accepted agent training traces and one rejected one;
- **local External-dataset slices** so 03 preparation has real mix inputs without a network call;
- the fixture **materializes real files** (the Dataset file, the External slices, the scripted responses)
  on disk; nothing is mocked at the storage layer.

## Assert-from-the-artifact rule

Every per-pipeline-stage test's **Then** asserts the durable artifact fetched back through the **next
pipeline stage's production read path** — never the in-memory return and never a test-specific read — so
a test cannot pass while the production read path is broken. Concretely, 03 asserts the Liquid `messages`
file by loading it the way 04 does; 05 asserts the RL-readiness gate output the way evaluation reads it.

## No-silent-data-loss

Any cap, minimum, filter, or sample records `{dropped, total, rate}` in the persisted artifact. A
truncation, a dedup drop, or a coverage miss with no logged rate is a test failure (the training-pipeline
invariant, [`system.md`](system.md) §7).

## Per-pipeline-stage test inventory

| Test | Contract | Key assertions |
|---|---|---|
| `test_01_loader_decodes_all_answer_formats` | [`pipeline/01-rows-loader.md`](pipeline/01-rows-loader.md) | decoded `gold_answer` + `[answer contract]`; **every** Answer format maps to one `submit_*` tool incl. `boolean`/`entity_id`; rows missing `prompt`/`gold_answer` and non-release-ready rows dropped **and counted** |
| `test_02_rejection_sampling` | [`pipeline/02-teacher-sampling.md`](pipeline/02-teacher-sampling.md) | only Query-verifier-accepted agent training traces kept; a rejected attempt never enters the pool; the sampling log records reasoning, output, and tool call **distinctly** (A5); the coverage gate runs on the projected universe |
| `test_03_converter_masks_non_assistant_turns` | [`pipeline/03-preparation.md`](pipeline/03-preparation.md), [`system.md`](system.md) §7 | **highest-risk**: `messages` is authoritative; assistant reasoning + the tool call are loss-bearing, system/user/tool-response turns are masked; the final `submit_*` survives tokenization; evaluation/held-out rows hard-excluded; dedup recorded |
| `test_04_sft_cpu_smoke` (layer 6 skips) | [`pipeline/04-sft.md`](pipeline/04-sft.md) | the config sets `assistant_only_loss: true`; the LLM adapter is saved; a second run with the same seed is identical |
| `test_05_rl_gate_tiers` | [`pipeline/05-rl-readiness-gate.md`](pipeline/05-rl-readiness-gate.md) | scripted policy rollouts → `pass@1` + CI; per-row chance test + **pooled tier-level** chance-corrected rate (`p_chance` per row; α=0.05 table); `0/8` not unreachable; unbiased `pass@k` only when `k<n`; no tier from a screen-only row; no weights updated |
| `test_06_harness_modes` | [`pipeline/06-harness-modes.md`](pipeline/06-harness-modes.md), [`../evaluation/plan.md`](../evaluation/plan.md) §4 | `numpy` and `no_tools` graded by the **one scorer**; the oracle is a key-path check; off-oracle wrong-answer/formatting fixtures fail as expected |
| `test_07_serving_parity` | [`pipeline/07-serving.md`](pipeline/07-serving.md) | the LLM adapter loads via HF Transformers (the reference runtime); a parity check runs only for a non-Transformers runtime (argmax agreement on a fixed prompt set) |
| `test_train_and_eval_e2e_pipeline` | [`pipeline/00-overview.md`](pipeline/00-overview.md) | the full chain, below |

## End-to-end test

`test_train_and_eval_e2e_pipeline` — the epic's E2E test.

**Given** the 5-row fixture, the scripted teacher, and the local External-dataset slices;

**When** the DAG runs loader → teacher → preparation → SFT (1-step CPU) → RL-readiness gate → evaluation;

**Then**

- every pipeline stage's durable artifact exists and is read back through the next pipeline stage's
  production read path;
- the Liquid `messages` set has assistant-only loss: reasoning and the tool call are supervised, tool
  responses are masked (asserted at the token/label level, not assumed);
- no agent training trace is truncated past its final `submit_*` call; traces above the 16,384-token
  admission window are rejected, not truncated, and counted;
- the 5 rows' Answer formats all appear (incl. `submit_workplane`);
- every evaluation/held-out row is excluded from the mix (contamination is a hard failure);
- the coverage gate passes and is re-checked **after** sample + mix; an intended combination dropped by
  the mix is a hard failure, and a first-run mix with every combination at least 1 but some `< 8` is
  accepted only as `coverage_limited` (listed, not silently passed);
- two runs with the same seed are byte-identical (determinism);
- zero live calls to any external provider (the teacher/weights mocks' live-call counters are zero).

## The high-risk assertions, and why this doc exists

- **Masking (LE-4).** smoltalk has no tools and no tool-role turns, so its reproduction cannot exercise
  `render_tool_calls`. This fixture is the only test that does.
- **Truncation (LE-5).** A multi-round agent training trace can fill the window; right-truncation would
  silently drop the only supervised target.
- **Contamination.** One leaked row from an evaluation dataset invalidates the thesis number.
- **Coverage after mix (LE-7).** `sample + mix` is where coverage can be destroyed; the coverage gate
  must be re-checked there.
- **One scorer (D-E8).** Evaluation, rejection sampling, and reward share one implementation.

## TDD workflow (per pipeline stage)

1. define each pipeline stage's typed models from the IO contract in [`pipeline/00-overview.md`](pipeline/00-overview.md);
2. write each pipeline stage's adversarial integration test **first** (red);
3. implement that pipeline stage until green;
4. add the failure-mode test;
5. no `skip`/`xfail` and no weakened assertions — the only permitted `skip` is the GPU marker (layer 6).

## How tests run

- `uv run pytest tests/integration/train_and_eval -n auto` — CPU-only, no network, no GPU;
- the GPU smoke is marked and skipped unless a GPU is present;
- the real-teacher eval (layer 5) is local-only and never runs in CI.

## Where it lives

`tests/integration/train_and_eval/` — mirrors each `pipeline/NN-*.md` doc one-to-one, plus
`test_train_and_eval_e2e_pipeline.py`.

## Open questions

- **Q1.** Does the GPU smoke (layer 6) run in CI when a GPU is available, or only on demand?

## Resolved questions

- **Q2.** *(2026-10-10)* Is the E2E test runnable without a GPU? Yes — layers 1–4 are CPU-only; the only
  GPU-shaped piece (layer 6) is skipped or reduced to a 1-step CPU run on the tiny LLM model.
