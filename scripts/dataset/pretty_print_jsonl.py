"""Pretty-print JSONL files into JSON and prompt-readable Markdown."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SUMMARY_FIELDS = (
    "id",
    "task_type",
    "target_feature_id",
    "answer",
    "answer_type",
    "source_id",
    "split",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(record, dict):
                raise SystemExit(f"{path}:{line_number}: expected a JSON object")
            records.append(record)
    return records


def write_pretty_json(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def markdown_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def write_markdown(records: list[dict[str, Any]], path: Path, prompt_field: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for index, record in enumerate(records, start=1):
            record_id = record.get("id", f"record-{index}")
            handle.write(f"# Record {index}: {record_id}\n\n")
            for field in SUMMARY_FIELDS:
                if field in record:
                    handle.write(f"- {field}: {markdown_value(record[field])}\n")

            prompt = record.get(prompt_field)
            if prompt is not None:
                handle.write(f"\n## {prompt_field}\n\n")
                handle.write(markdown_value(prompt))
                handle.write("\n")

            handle.write("\n---\n")
            if index != len(records):
                handle.write("\n")


def expand_jsonl_paths(paths: list[Path]) -> list[Path]:
    jsonl_paths: list[Path] = []
    for path in paths:
        if path.is_dir():
            jsonl_paths.extend(sorted(path.glob("*.jsonl")))
        else:
            jsonl_paths.append(path)
    return jsonl_paths


def pretty_print_jsonl(path: Path, output_dir: Path | None, prompt_field: str) -> None:
    records = read_jsonl(path)
    resolved_output_dir = output_dir or path.parent / "pretty-print"
    json_path = resolved_output_dir / f"{path.stem}.json"
    markdown_path = resolved_output_dir / f"{path.stem}.md"

    write_pretty_json(records, json_path)
    write_markdown(records, markdown_path, prompt_field)

    print(f"Wrote {len(records)} records from {path}")
    print(f"- {json_path}")
    print(f"- {markdown_path}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "jsonl_paths",
        nargs="+",
        type=Path,
        help="Input JSONL file(s), or directories containing JSONL files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for generated files; defaults to <input-dir>/pretty-print",
    )
    parser.add_argument(
        "--prompt-field",
        default="prompt",
        help="String field to render with real newlines in Markdown",
    )
    args = parser.parse_args(argv)

    jsonl_paths = expand_jsonl_paths(args.jsonl_paths)
    if not jsonl_paths:
        raise SystemExit("No JSONL files found")
    for path in jsonl_paths:
        pretty_print_jsonl(path, args.output_dir, args.prompt_field)


if __name__ == "__main__":
    main()
