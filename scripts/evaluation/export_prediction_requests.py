"""Export provider-agnostic closed-book prediction requests from CAD-QA rows."""

from __future__ import annotations

import argparse
from pathlib import Path

from cad_qa.jsonio import read_jsonl, write_json, write_jsonl


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rows", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--system-prompt", default="Answer the CAD-QA question without executing code. Return only the requested structured answer.")
    args = parser.parse_args(argv)

    rows = read_jsonl(args.rows)
    requests = [
        {
            "row_id": row["id"],
            "task_type": row["task_type"],
            "split": row["split"],
            "prompt_hash": row.get("hashes", {}).get("prompt_hash"),
            "answer_type": row["answer_type"],
            "parse_policy": row["parse_policy"],
            "choices": row.get("choices"),
            "messages": [
                {"role": "system", "content": args.system_prompt},
                {"role": "user", "content": row["prompt"]},
            ],
        }
        for row in rows
    ]
    write_jsonl(args.output, requests)
    write_json(
        args.output.with_suffix(".report.json"),
        {
            "schema": "cadqa_prediction_request_report_v1",
            "input_rows": str(args.rows),
            "output": str(args.output),
            "request_count": len(requests),
        },
    )
    print({"request_count": len(requests), "output": str(args.output)})


if __name__ == "__main__":
    main()
