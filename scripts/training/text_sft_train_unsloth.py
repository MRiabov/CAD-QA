"""Answer-only SFT entrypoint.

This script intentionally gates real training when GPU-only dependencies are
missing. It preserves a structured result so the experiment runner can record
why the canary did not launch on a local CPU machine.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

from cad_qa.jsonio import read_jsonl, write_json


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sft-dir", type=Path)
    parser.add_argument("--model", default="unsloth/Qwen3.5-4B")
    parser.add_argument("--max-train-rows", type=int, default=256)
    parser.add_argument("--max-eval-rows", type=int, default=64)
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--per-device-train-batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--dry-run", action="store_true")
    args, _unknown = parser.parse_known_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    sft_dir = args.sft_dir or args.output_dir / "sft_dataset"
    train_count = _row_count(sft_dir / "train.jsonl")
    eval_count = _row_count(sft_dir / "validation.jsonl")
    result = {
        "schema": "cadqa_unsloth_sft_result_v1",
        "status": "dry_run" if args.dry_run else "gated",
        "model": args.model,
        "dataset_dir": str(args.dataset_dir),
        "sft_dir": str(sft_dir),
        "train_count": train_count,
        "eval_count": eval_count,
        "max_steps": args.max_steps,
        "reason": None,
    }
    if args.dry_run:
        result["reason"] = "dry_run_requested"
        write_json(args.output_dir / "train_result.json", result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    missing = [name for name in ("torch", "transformers", "trl", "unsloth") if importlib.util.find_spec(name) is None]
    if missing:
        result["reason"] = f"missing_training_dependencies:{','.join(missing)}"
        write_json(args.output_dir / "train_result.json", result)
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(2)
    result["status"] = "not_implemented"
    result["reason"] = "real_unsloth_training_loop_is_not_checked_in_yet"
    write_json(args.output_dir / "train_result.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(2)


def _row_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(read_jsonl(path))


if __name__ == "__main__":
    main(sys.argv[1:])
