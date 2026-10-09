# 02 — teacher sampling

## Purpose

Produce **agent training traces** for `learn_the_cadqa_task` by sampling a **teacher** LLM model over
decoded CAD-QA dataset rows and keeping only attempts the Query verifier accepts (**rejection
sampling**), ordered toward the **progressive curriculum** (0→1→2→3→5).

## Inputs / outputs

- **In:** decoded CAD-QA dataset rows (01) — `prompt`, `answer_format`, `gold_answer`,
  `reasoning_hop_count`.
- **Teacher:** `deepseek/deepseek-v4.1-flash` via OpenRouter (FT-D2; bumped from the v4 preview).
- **Out `agent training traces`:** one per accepted row, `dataset_role=learn_the_cadqa_task`, carrying
  `answer_format`, `reasoning_hop_count`, and reasoning / visible output / tool call kept distinct (A5).
- **Out `sampling log`:** one record per attempt (reasoning, output, tool call, rounds).

## Requirement

A kept **agent training trace** must contain a tool call `tool_call_matches` accepts against the row's gold; a rejected
attempt never enters the pool. **Coverage must be complete across the whole task space** — every Answer
format × Reasoning hop count × relation family × measurement scope present in the training set (each
task family; on the order of hundreds of combinations) — because a combination the teacher never
produces cannot be learned (the recorded `json`/`number` zero-coverage defect).

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

- **Q1.** Coverage gate: how is a floor **per task combination** — Answer format × Reasoning hop count ×
  relation family × measurement scope (each task family; order hundreds of combinations) — enforced
  offline from the sampling log?
- **Q2.** Teacher settings (temperature, attempts per row). The recorded **~23% success rate was the v4
  preview**; v4.1 is materially stronger, so re-measure success and per-combination coverage.
