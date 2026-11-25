# CAD-QA RL (GRPO) Runbook

Purpose: post-train a small model (target: `google/gemma-4-E2B-it`, 2B active)
on CAD-QA with a **verifiable exact-match reward**, then evaluate against the
baseline slices. The training runtime is Unsloth Studio (Vast container, set up
separately); this repo provides the data + reward + eval tooling.

## Training data (HuggingFace)

**https://huggingface.co/datasets/MRiabov/cadqa-rl-2000**

```python
from datasets import load_dataset

ds = load_dataset("MRiabov/cadqa-rl-2000")  # splits: train (2000), validation (98)
```

- `train` — 2000 rows `{row_id, prompt, answer_format, gold_answer,
  difficulty_bucket, logical_hop_count, geometry_hop_count, relation_families}`.
  Sampled from `release_10k` train split; **bench-slice rows excluded** (no
  train/eval leakage).
- `validation` — 98 bench-slice rows (eval; do NOT train on them).
- `gold_answer` is JSON-encoded in parquet (`"wp15"`, `[1.0, 2.0, 3.0]`);
  `reward_cadqa.py` decodes it automatically.
- Local source + regeneration:
  `rtk uv run python runs/gemma_bench/rl/export_rl_data.py --rows <release_10k>/rows.parquet --out runs/gemma_bench/rl/cadqa_rl --train-size 2000`

## Reward

- `runs/gemma_bench/rl/reward_cadqa.py` — **self-contained** (no repo imports;
  embed in the training notebook). Mirrors the repo grader exactly
  (`parse_answer` + exact match; validated: oracle=1.0, h1=0.14).

## Reward contract

```python
from reward_cadqa import reward_cadqa
reward_cadqa(gold_answer, answer_format, completion) -> 0.0 | 1.0
```

Per GRPO step: for each rollout prompt, score the sampled completions against
`gold_answer` (decoded) using the row's `answer_format`. Unparseable output =
0.0. For candidate_label/entity_id answers the raw completion is matched
directly; strip markdown fences / extra prose in the notebook's completion
extraction before scoring (mirror the bench runner's `_strip_special`).

## Unsloth Studio steps

1. Load the model: `unsloth/gemma-4-E2B-it` (Unsloth Studio's model picker;
   their Gemma-4 E2B notebook covers load + GRPO).
2. Dataset: upload `train.jsonl` (HF `datasets` can load JSONL directly) or
   paste rows; the training loop needs `prompt`, `answer_format`, `gold_answer`.
3. Reward: copy `reward_cadqa.py` into the notebook/recipe and register a
   function that calls `reward_cadqa(row["gold_answer"], row["answer_format"], completion)`.
4. GRPO config: start with a small subset (e.g. 256 rows), 4 rollouts/step,
   `beta` default; a 2B model fits 16 GB VRAM comfortably.
5. Save the LoRA adapter; export/merge.

## Evaluation (post-training)

Run the bench runner (h1, closed-book) on the same slices used for the baseline:

```bash
# on the training/eval box with the merged model:
CADQA_MODEL_ID=<path-to-merged> CADQA_RUN_H3=0 CADQA_SLICES=both \
  python3 runs/gemma_bench/local_run.py   # or via the notebook on Unsloth Studio
```

Then grade locally:
```bash
rtk uv run cadqa evaluation grade --rows runs/gemma_bench/slices/rc10/rows.jsonl \
  --responses <out>/responses_h1_rc10.jsonl --out <out>/grade_rl_rc10
rtk uv run cadqa evaluation grade-private \
  --public runs/gemma_bench/slices/release10k/public.jsonl \
  --private runs/gemma_bench/slices/release10k/private.jsonl \
  --responses <out>/responses_h1_release10k.jsonl --out <out>/grade_rl_rel
```

Baseline to beat (Gemma-4-E2B-it, closed-book, this repo's slices):
rc10 30% (random ~4%), release10k 14% (random ~13%).
