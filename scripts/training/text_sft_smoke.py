"""Cheap local smoke check for answer-only SFT JSONL files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cad_qa.jsonio import read_jsonl, write_json


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sft-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    train = (
        read_jsonl(args.sft_dir / "train.jsonl")
        if (args.sft_dir / "train.jsonl").exists()
        else []
    )
    validation = (
        read_jsonl(args.sft_dir / "validation.jsonl")
        if (args.sft_dir / "validation.jsonl").exists()
        else []
    )
    errors = []
    for split_name, rows in (("train", train), ("validation", validation)):
        for index, row in enumerate(rows, start=1):
            messages = row.get("messages")
            if not isinstance(messages, list) or len(messages) != 2:
                errors.append(f"{split_name}:{index}:messages")
            elif (
                messages[0].get("role") != "user"
                or messages[1].get("role") != "assistant"
            ):
                errors.append(f"{split_name}:{index}:roles")
            elif not messages[0].get("content") or not messages[1].get("content"):
                errors.append(f"{split_name}:{index}:empty_content")
    report = {
        "status": "pass" if not errors else "fail",
        "train_count": len(train),
        "validation_count": len(validation),
        "errors": errors,
    }
    output = args.output or args.sft_dir / "text_sft_smoke_report.json"
    write_json(output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
