"""Export CAD-QA RL training data (prompt + gold + answer_format) for GRPO.

Usage (from repo root, python 3.12 venv):
    rtk uv run python runs/gemma_bench/rl/export_rl_data.py \
        --rows runs/current_cadevolve1000_10k_regen_20260613/release_10k/rows.parquet \
        --out runs/gemma_bench/rl/cadqa_rl \
        --train-size 2000

Writes:
    cadqa_rl/train.jsonl     - {row_id, prompt, answer_format, gold_answer, ...}
    cadqa_rl/heldout.jsonl   - rows excluded from train (reserved eval, includes
                               the bench slices so RL never trains on them)
    cadqa_rl/report.json     - stratification summary
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

# The 100-row bench slices used for baseline eval — never in RL training data.
BENCH_EVAL_ROW_IDS: set[str] = set()


def _load_bench_eval_ids(slices_dir: Path) -> set[str]:
    ids: set[str] = set()
    for f in [
        slices_dir / "release10k" / "public.jsonl",
        slices_dir / "rc10" / "rows.jsonl",
    ]:
        if f.exists():
            for line in f.open():
                ids.add(json.loads(line)["row_id"])
    return ids


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--train-size", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20260808)
    args = ap.parse_args()

    bench_ids = _load_bench_eval_ids(Path("runs/gemma_bench/slices"))
    t = pq.read_table(args.rows)
    names = set(t.column_names)
    rows: list[dict] = []
    for i in range(t.num_rows):
        rec = {c: t.column(c)[i].as_py() for c in names}
        if rec.get("split") != "train":
            continue
        if rec.get("gold_answer") is None or rec.get("prompt") is None:
            continue
        if rec.get("release_ready") is False:
            continue
        rows.append({
            "row_id": rec["row_id"],
            "prompt": rec["prompt"],
            "answer_format": rec["answer_format"],
            "gold_answer": rec["gold_answer"],
            "difficulty_bucket": rec.get("difficulty_bucket"),
            "logical_hop_count": rec.get("logical_hop_count"),
            "geometry_hop_count": rec.get("geometry_hop_count"),
            "relation_families": rec.get("relation_families"),
        })
    rng = random.Random(args.seed)
    train = [r for r in rows if r["row_id"] not in bench_ids]
    # heldout = bench-slice rows (reserved eval); keep it small
    heldout = [r for r in rows if r["row_id"] in bench_ids]
    rng.shuffle(train)
    train = train[: args.train_size]

    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "train.jsonl").open("w") as f:
        for r in train:
            f.write(json.dumps(r) + "\n")
    with (args.out / "heldout.jsonl").open("w") as f:
        for r in heldout:
            f.write(json.dumps(r) + "\n")
    report = {
        "train_size": len(train),
        "heldout_size": len(heldout),
        "train_by_format": dict(Counter(r["answer_format"] for r in train)),
        "train_by_difficulty": dict(Counter(r["difficulty_bucket"] for r in train)),
        "heldout_by_format": dict(Counter(r["answer_format"] for r in heldout)),
    }
    (args.out / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
