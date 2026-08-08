# RL Checkpoint — 2026-08-08

Checkpoint of the gemma-4-E2B RL (GRPO) effort on CAD-QA. State as of 2026-08-08.

## Goal

RL fine-tune `unsloth/gemma-4-E2B-it` on CAD-QA so the model answers CAD questions (entity ids,
numbers, bboxes, JSON) better than the closed-book base model. Curriculum by hop count
(0 → 2 → 3 → 4 → 5) since 1-hop does not exist in the current synthesis (see below).

## Baseline (measured, closed-book)

| Slice | Hops | Base gemma-4-E2B accuracy |
|---|---|---|
| rc10 (100 rows) | 0 | **30%** |
| release10k (from `cadqa_feature_provenance_choice`) | 2–5 | **14%** (≈ random) |

Reward function reproduces the baseline exactly: `reward_cadqa` mean 0.143 on `cadqa-rl-2000`.

## Dataset (HF: `MRiabov/cadqa-rl-2000`)

- **v1**: 2000 rows (2–5 hop) + validation 98. Original export.
- **v2_curriculum** (current): 2100 rows = 100 × 0-hop (rc10 slice) + 2000 × 2–5 hop.
  - `gold_answer` normalized to JSON strings (rc10 golds are mixed types: str/dict/int/float —
    bbox/json golds are dicts, number/integer are ints/floats; pyarrow `from_list` rejects mixed).
  - columns: `row_id`, `prompt`, `answer_format`, `gold_answer`, `logical_hop_count`.
- **1-hop**: does NOT exist in the current synthesis. Verified: 15,615 freshly synthesized queries
  over 100 graphs → hop distribution {2:357, 3:1924, 4:8903, 5:4431}, **0 one-hop**.
  Old synthesis (May 2026) had exactly one 1-hop template (`argmax origin_z over workplane`,
  e.g. `highest_workplane` → gold `workplane:wp35`), but only ran over ~3 graphs → 6 stale rows.
  - **Fresh 1-hop generation in progress**: 13 clause-less aggregation templates × 400 graphs =
    5,200 queries at `/tmp/1hop_queries.jsonl` (templates: argmax/argmin over origin_z/area/
    bbox_center_{x,z}/distance_to_origin/bbox_delta_max_span, target workplane/face,
    `reject_unless_unique=true`, `min_individual_clause_candidates=3`).
    Materialization (`cadqa dataset materialize --queries ... --graphs
    runs/current_cadevolve1000_10k_regen_20260613/graph`) NOT yet completed — smoke run was
    interrupted. No cadquery needed: golds resolve from graph measurements.

## Environment (box: RTX 4080 Super 32 GB, Vast instance 47199082)

- SSH: `root@175.155.64.174 -p 19599` (key `~/.ssh/vastai_wireseghr`).
- Venv `/root/cadqa-rl-venv` — **canonical Unsloth E2B-RL recipe** (from the official
  "Gemma 4 E2B RL Sudoku Game" notebook), NOT the earlier hand-pinned franken-env:
  - `unsloth` (git-main), `trl>=0.28`, `transformers>=5.5.0`, `tokenizers>=0.22,<=0.23`, `timm`,
    `torch>=2.8`, `triton>=3.4` + triton_kernels from git. Built via `uv`.
  - **No vLLM** — gemma-4 is not loadable by vLLM (`transformers<5` constraint in every vLLM
    version; gemma-4 needs transformers 5.x). RL runs with `fast_inference=False`
    (Unsloth's own generation) and 16-bit LoRA (`load_in_4bit=False`).
- Scripts in `/root/cadqa-bench/`: `grpo_train.py`, `reward_cadqa.py`, `run_grpo_final.sh`,
  `notebook_env.sh`; log `grpo_final.log`; checkpoints `save_strategy="no"` (none saved!).
- Copies of the scripts live in repo: `runs/gemma_bench/rl/`.

## Training config (grpo_train.py)

- Model: `unsloth/gemma-4-E2B-it-unsloth-bnb-4bit`... NOTE: final config loads bf16
  (`load_in_4bit=False`) via `FastVisionModel.from_pretrained`, 16-bit LoRA rank 32, grad ckpt.
- `max_seq_length=16384`, `max_completion_length=8192`, `num_generations=2`, `per_device_train_batch_size=4`,
  LR 3e-4, `beta=1.0` (KL), `loss_type="grpo"`, `shuffle_dataset=False` (curriculum order honored).
- Curriculum: buckets by `logical_hop_count`, ordered 0→2→3→4→5, each weighted to its share of
  `N_ROWS` (=2000 → 300 curriculum-ordered rows); 0-hop: 100 rows → 75 steps; 2: 17→30; 3: 291→45;
  4: 1354→75; 5: 338→75.
- Reward: exact-match per format — candidate_label/entity_id/text: substring/equality after
  `_strip_special`; number/integer: float/int compare; bbox/json: regex extraction then compare.
  `_decode_gold` double-decodes JSON-encoded golds. Verified NOT buggy (no empty-gold match;
  per-format short completions score correctly).

## Status: first training run — COLLAPSED at the 2-hop cliff

- 143/300 steps, still RUNNING at checkpoint (wasting ~$0.30/h; recommendation: kill or let it finish).
- **0-hop stage (75 steps):** reward → 1.0 — the model produced *correct* short answers
  (verified per-format, not a reward bug). But policy collapsed: entropy ~0, completions → 2 tokens.
- **hop=2 stage:** reward → 0, entropy dead (≈1e-5), `mean_len` 7, `frac_reward_zero_std=1`.
  The 0-hop shortcut does not transfer; with entropy ~0 there is no exploration left, so GRPO
  cannot recover → run is effectively stuck.
- **Diagnosis:** sparse exact-match reward + steep 0→2 difficulty jump → shortcut learning then
  collapse. The 1-hop bridge (in progress) is the direct mitigation, plus reward shaping
  (partial credit) and/or stronger entropy/KL control.

## Next steps

1. Finish 1-hop materialization → publish `v3_curriculum` (0/1/2–5) → retrain with the 0→1→2→3→4→5 ladder.
2. Fix collapse: reward shaping (partial credit for structure/format), consider `entropy` term or
   higher `beta`; verify entropy recovers in the 1-hop stage.
3. Deliverable per user steer: bench gemma-4-E2B on the dataset (done: 30% / 14% baselines);
   SFT only if "e2b must not know cadquery" turns out to be a genuine requirement.
4. Save checkpoints (`save_strategy="steps"`) — current run saves nothing.

## Caveats

- Local graph artifacts: only 4 shards (400 graphs) of the 1000-graph regen exist under
  `runs/current_cadevolve1000_10k_regen_20260613/graph/` — 1-hop coverage limited to 400 graphs.
- The 1-hop query generator and materialize smoke outputs live in `/tmp` (ephemeral) — move into
  `runs/gemma_bench/rl/` before reboot.
- The training box is a rented Vast instance; verify it is still rented before resuming.
