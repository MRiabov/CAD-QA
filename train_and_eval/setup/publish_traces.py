"""Publish SFT traces to HF (durable store) — replaces the old gitignored runs/ copies.

Usage:
  python publish_traces.py --traces sft_traces_merged.jsonl --config sft_traces_v2
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from datasets import Dataset, load_dataset


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", type=Path, required=True)
    ap.add_argument("--config", default="sft_traces_v2", help="HF config name on MRiabov/cadqa-rl-2000")
    ap.add_argument("--repo", default="MRiabov/cadqa-rl-2000")
    args = ap.parse_args()

    rows = [json.loads(l) for l in args.traces.read_text().splitlines() if l.strip()]
    ds = Dataset.from_list(rows)
    ds.push_to_hub(args.repo, config_name=args.config, split="train")
    print(f"pushed {len(rows)} traces to {args.repo}:{args.config}")


if __name__ == "__main__":
    main()
