"""Build few-shot closed-book prediction requests using train rows only."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from cad_qa.jsonio import read_jsonl, write_json, write_jsonl


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-rows", type=Path, required=True)
    parser.add_argument("--eval-rows", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shots", type=int, default=3)
    args = parser.parse_args(argv)

    train_rows = read_jsonl(args.train_rows)
    eval_rows = read_jsonl(args.eval_rows)
    examples_by_task = _examples_by_task(train_rows, args.shots)
    requests = []
    for row in eval_rows:
        examples = examples_by_task.get(str(row["task_type"]), train_rows[: args.shots])
        requests.append(
            {
                "row_id": row["id"],
                "task_type": row["task_type"],
                "split": row["split"],
                "prompt_hash": row.get("hashes", {}).get("prompt_hash"),
                "answer_type": row["answer_type"],
                "parse_policy": row["parse_policy"],
                "choices": row.get("choices"),
                "messages": [
                    {
                        "role": "system",
                        "content": "Answer the CAD-QA question without executing code. Use the examples only for answer formatting.",
                    },
                    {"role": "user", "content": _fewshot_prompt(examples, row)},
                ],
                "fewshot_row_ids": [example["id"] for example in examples],
            }
        )
    write_jsonl(args.output, requests)
    write_json(
        args.output.with_suffix(".report.json"),
        {
            "schema": "cadqa_fewshot_request_report_v1",
            "train_rows": str(args.train_rows),
            "eval_rows": str(args.eval_rows),
            "output": str(args.output),
            "shots": args.shots,
            "request_count": len(requests),
        },
    )
    print({"request_count": len(requests), "output": str(args.output)})


def _examples_by_task(rows: list[dict[str, Any]], shots: int) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        result.setdefault(str(row["task_type"]), [])
        if len(result[str(row["task_type"])]) < shots:
            result[str(row["task_type"])].append(row)
    return result


def _fewshot_prompt(examples: list[dict[str, Any]], row: dict[str, Any]) -> str:
    parts = ["Examples:"]
    for example in examples:
        parts.append(f"Question:\n{example['prompt']}\nAnswer:\n{_answer_text(example['answer'])}")
    parts.append(f"Question:\n{row['prompt']}\nAnswer:")
    return "\n\n".join(parts)


def _answer_text(answer: Any) -> str:
    if isinstance(answer, dict):
        import json

        return json.dumps(answer, sort_keys=True, separators=(",", ":"))
    return str(answer)


if __name__ == "__main__":
    main()
