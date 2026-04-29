"""Pretty-print JSONL files into JSON and prompt-readable Markdown."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SPLITS = ("train", "validation", "test_random", "test_operation_heldout")
SUMMARY_FIELDS = (
    "id",
    "task_type",
    "target_feature_id",
    "answer",
    "answer_type",
    "source_id",
    "split",
)


def read_jsonl(path: Path, *, limit: int | None = None) -> list[dict[str, Any]]:
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
            if limit is not None and len(records) >= limit:
                break
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


def expand_jsonl_paths(
    paths: list[Path], *, dataset_dir: Path | None, splits: list[str] | None
) -> list[Path]:
    jsonl_paths: list[Path] = []
    if dataset_dir is not None:
        split_names = splits or list(SPLITS)
        jsonl_paths.extend(
            dataset_dir / "jsonl" / f"{split}.jsonl" for split in split_names
        )
    for path in paths:
        if path.is_dir():
            jsonl_paths.extend(sorted(path.glob("*.jsonl")))
        else:
            jsonl_paths.append(path)
    return jsonl_paths


def pretty_print_jsonl(
    path: Path,
    output_dir: Path | None,
    prompt_field: str,
    *,
    limit: int | None = None,
) -> None:
    records = read_jsonl(path, limit=limit)
    resolved_output_dir = output_dir or path.parent / "pretty-print"
    json_path = resolved_output_dir / f"{path.stem}.json"
    markdown_path = resolved_output_dir / f"{path.stem}.md"

    write_pretty_json(records, json_path)
    write_markdown(records, markdown_path, prompt_field)

    print(f"Wrote {len(records)} records from {path}")
    print(f"- {json_path}")
    print(f"- {markdown_path}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Examples:\n"
            "  python -m scripts.dataset.pretty_print_jsonl --dataset-dir data/cadqa_smoke\n"
            "  python -m scripts.dataset.pretty_print_jsonl --dataset-dir data/cadqa_smoke "
            "--split validation --limit 25\n"
            "  python -m scripts.dataset.pretty_print_jsonl data/cadqa_smoke/jsonl/train.jsonl"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "jsonl_paths",
        nargs="*",
        type=Path,
        help="Input JSONL file(s), or directories containing JSONL files",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        help="Dataset export directory containing a jsonl/ split directory",
    )
    parser.add_argument(
        "--split",
        action="append",
        choices=SPLITS,
        help="Dataset split to pretty-print when --dataset-dir is used; repeat for multiple splits",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for generated files; defaults to <dataset-dir>/pretty-print or <input-dir>/pretty-print",
    )
    parser.add_argument(
        "--prompt-field",
        default="prompt",
        help="String field to render with real newlines in Markdown",
    )
    parser.add_argument(
        "--limit",
        type=_positive_int,
        help="Maximum records to read from each JSONL file",
    )
    args = parser.parse_args(argv)

    if args.dataset_dir is None and not args.jsonl_paths:
        parser.error("provide --dataset-dir or at least one JSONL path")
    if args.split and args.dataset_dir is None:
        parser.error("--split requires --dataset-dir")

    output_dir = args.output_dir
    if output_dir is None and args.dataset_dir is not None:
        output_dir = args.dataset_dir / "pretty-print"
    jsonl_paths = expand_jsonl_paths(
        args.jsonl_paths, dataset_dir=args.dataset_dir, splits=args.split
    )
    if not jsonl_paths:
        raise SystemExit("No JSONL files found")
    for path in jsonl_paths:
        if not path.exists():
            raise SystemExit(f"JSONL file does not exist: {path}")
        pretty_print_jsonl(path, output_dir, args.prompt_field, limit=args.limit)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


if __name__ == "__main__":
    main()
