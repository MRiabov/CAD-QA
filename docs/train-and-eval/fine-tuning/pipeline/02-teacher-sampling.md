# 02 — teacher sampling

## Purpose

Produce **agent training traces** for `learn_the_cadqa_task` by sampling a **teacher** LLM model over
decoded CAD-QA dataset rows and keeping only attempts the Query verifier accepts (**rejection
sampling**), tagged with the release hop tier (`{2,3,4,5}`) for later tier gating; sampling does not
depend on row order.

## Inputs / outputs

- **In:** decoded CAD-QA dataset rows (01) **in the `sft_train` pool** — `prompt`, `answer_format`,
  `gold_answer`, `reasoning_hop_count`, `relation_families`, `measurement_scopes`. `rl_train` rows are
  **not** sampled for SFT; the RL gate uses their gold answers directly, and any teacher sampling of
  `rl_train` (a teacher ceiling or post-gate RFT) must never enter the SFT mix.
- **Teacher:** `deepseek/deepseek-v4.1-flash` via OpenRouter (FT-D2; bumped from the v4 preview).
- **Out `agent training traces`:** one per accepted `sft_train` row, `dataset_role=learn_the_cadqa_task`,
  carrying `answer_format`, `reasoning_hop_count`, `relation_families`, `measurement_scopes`, and
  reasoning / visible output / tool call kept distinct (A5).
- **Out `sampling log`:** one record per attempt (reasoning, output, tool call, rounds).

## Requirement

A kept **agent training trace** must contain a tool call `tool_call_matches` accepts against the row's gold; a rejected
attempt never enters the pool. **Only `sft_train` rows are sampled for SFT**; `rl_train` and `eval` rows
never enter the SFT trace pool (`../data.md` §5). **Coverage must be complete across the whole task space** — every Answer
format × Reasoning hop count × relation family × measurement scope present in the training set (each
task family; on the order of hundreds of combinations) — because a combination the teacher never
produces cannot be learned (the recorded `json`/`number` zero-coverage defect).

The coverage gate is enforced **offline** as the **dataset release report projected onto the sampling log**. It
consumes the set the dataset already commits to — intended release families
(`dataset/query/family_specs.yaml`;
`dataset/query/family_manifest.py::intended_family_coverage_report`) plus hop/scope coverage
(`dataset/release/release_report.py::release_balance_report`) — and reuses the same `_prompt_family()`
key, so an agent training trace's combination lines up with the row's. It reports `passes_*_sampling_coverage` in the
`release_balance_report` style rather than introducing a second taxonomy; the remaining choice is the
key's grain (Q1).

**Per-combination minima (2026-10-20).** `m_cover = 1` (every intended combination) and
`m_train = 8` (primary). The first run may ship `coverage_limited` with `m_cover = 1` and every
combination below 8 listed; it makes no per-combination learning claim. This gate is **pre-mix**: it
certifies the sampled pool, not the final training set. Stage 05 **re-runs the same projection after
`sample + mix`**; zero in an intended combination is a hard failure, and `< 8` is reported as
undercovered (`system.md` §7 step 5).

**A failed tier is a finding.** If the teacher cannot produce an accepted trace for a hop tier after the
planned attempts, record the tier, attempts, and failure reason in the sampling log and report it as a
finding to the owner — never a silent coverage miss. Do not advance past it or drop it without saying so.

## Bridge

Hard traces the small LLM model cannot imitate are rewritten into more learnable supervision (a
**Bridge**, `../system.md` §2) rather than fed as an unlearnable target.

## Verification

```bash
# end-to-end: a tiny targeted sample (needs OPENROUTER_API_KEY + network)
OPENROUTER_API_KEY=... uv run python train_and_eval/train/rejection_sample.py \
  --attempts-per-row 1 --target-count 2 --only-rows /tmp/ids.txt \
  --out /tmp/traces.jsonl --log /tmp/sampling.jsonl
```

## Open questions

- **Q1.** Coverage gate grain. *Direction:* the coverage gate is the **dataset release report projected onto the
  sampling log** (consume the intended-family/hop/scope set from `intended_family_coverage_report` +
  `release_balance_report`; reuse `_prompt_family()`; report `passes_*_sampling_coverage`) — not a new
  taxonomy. *Open:* key an agent training trace by the row's **primary measurement scope**, or **expand**
  each row into every `(relation_family × measurement_scope)` membership (a larger set)? This is a
  **gain** question, not a cost one: extra traces are cheap (~$10–25 per 1,000 off-peak, less via the
  `:batch` endpoint; `../training.md` §5.3), so decide on (1) the **incremental gain**, measurable only if
  the evaluation datasets cover the extra combinations, and (2) whether those combinations are
  **learnable** (FT-D15/Bridge). **Provisional: scope
  to the smaller set (primary scope)** until a measurable gain appears; measure first on the small test
  GPU (Modal, per-second, free credits), then scale.
- **Q2.** Teacher settings (temperature, attempts per row). The recorded **~23% success rate was the v4
  preview**; v4.1 is materially stronger, so re-measure success and per-combination coverage.
