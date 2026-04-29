"""Export optional render-backed CAD-QA prediction requests."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from cad_qa.jsonio import read_json, read_jsonl, write_json, write_jsonl


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rows", type=Path)
    parser.add_argument("--render-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--system-prompt",
        default="Answer the CAD-QA question using the code and optional render. Return only the requested structured answer.",
    )
    args = parser.parse_args(argv)

    rows = read_jsonl(args.rows)
    render_manifest = read_json(args.render_manifest)
    renders_by_source = _renders_by_source(render_manifest)
    requests = []
    skipped = 0
    for row in rows:
        render = renders_by_source.get(str(row.get("source_id")))
        if render is None:
            skipped += 1
            continue
        requests.append(
            {
                "row_id": row["id"],
                "task_type": row["task_type"],
                "split": row["split"],
                "prompt_hash": row.get("hashes", {}).get("prompt_hash"),
                "answer_type": row["answer_type"],
                "parse_policy": row["parse_policy"],
                "choices": row.get("choices"),
                "render_id": render["render_id"],
                "media": [
                    {
                        "type": "image/svg+xml",
                        "path": render["svg_path"],
                        "render_id": render["render_id"],
                    }
                ],
                "messages": [
                    {"role": "system", "content": args.system_prompt},
                    {"role": "user", "content": row["prompt"]},
                ],
            }
        )
    write_jsonl(args.output, requests)
    report = {
        "schema": "cadqa_multimodal_prediction_request_report_v1",
        "input_rows": str(args.rows),
        "render_manifest": str(args.render_manifest),
        "output": str(args.output),
        "request_count": len(requests),
        "skipped_without_render": skipped,
    }
    write_json(args.output.with_suffix(".report.json"), report)
    print(report)


def _renders_by_source(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for item in manifest.get("items", []):
        if not isinstance(item, dict) or item.get("status") not in {
            "rendered",
            "planned",
        }:
            continue
        source_id = item.get("source_id")
        if source_id:
            result.setdefault(str(source_id), item)
    return result


if __name__ == "__main__":
    main()
