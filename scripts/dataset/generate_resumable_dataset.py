"""Generate CAD-QA shards with cache-backed resumability."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from cad_qa.jsonio import read_json, write_json


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--auto-source-dir", action="store_true")
    parser.add_argument("--total-limit", type=int, required=True)
    parser.add_argument("--shard-size", type=int, default=25)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--trace-timeout-seconds", type=float, default=30.0)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--extra-cadquery", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = args.cache_dir or args.output_dir / "cache"
    shards_dir = args.output_dir / "shards"
    shards_dir.mkdir(exist_ok=True)
    summaries = []
    for offset in range(0, args.total_limit, args.shard_size):
        limit = min(args.shard_size, args.total_limit - offset)
        shard_name = f"shard_{offset:06d}_{offset + limit:06d}"
        shard_dir = shards_dir / shard_name
        status_path = shard_dir / "shard_status.json"
        if args.resume and status_path.exists():
            status = read_json(status_path)
            if status.get("status") == "completed":
                summaries.append(status)
                continue
        started = time.time()
        command = _generate_command(
            args, shard_dir / "dataset", cache_dir, offset, limit
        )
        result = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        shard_dir.mkdir(parents=True, exist_ok=True)
        (shard_dir / "stdout.log").write_text(result.stdout, encoding="utf-8")
        (shard_dir / "stderr.log").write_text(result.stderr, encoding="utf-8")
        status = {
            "schema": "cadqa_resumable_shard_status_v1",
            "shard": shard_name,
            "offset": offset,
            "limit": limit,
            "status": "completed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "elapsed_seconds": round(time.time() - started, 3),
            "command": command,
            "dataset_dir": str(shard_dir / "dataset"),
        }
        metadata_path = shard_dir / "dataset" / "metadata.json"
        if metadata_path.exists():
            metadata = read_json(metadata_path)
            status["row_count"] = metadata.get("row_count")
            status["source_count"] = metadata.get("source_count")
            status["failure_count"] = _line_count(
                shard_dir / "dataset" / "failure_manifest.jsonl"
            )
        write_json(status_path, status)
        summaries.append(status)
        if result.returncode != 0:
            break
    manifest = {
        "schema": "cadqa_resumable_generation_manifest_v1",
        "total_limit": args.total_limit,
        "shard_size": args.shard_size,
        "cache_dir": str(cache_dir),
        "shards": summaries,
        "completed": all(item.get("status") == "completed" for item in summaries),
    }
    write_json(args.output_dir / "resumable_generation_manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if not manifest["completed"]:
        raise SystemExit(1)


def _generate_command(
    args: argparse.Namespace,
    dataset_dir: Path,
    cache_dir: Path,
    offset: int,
    limit: int,
) -> list[str]:
    command = ["uv", "run"]
    if args.extra_cadquery:
        command.extend(["--extra", "cadquery"])
    command.extend(
        [
            "cadqa",
            "generate",
            "--output-dir",
            str(dataset_dir),
            "--offset",
            str(offset),
            "--limit",
            str(limit),
        ]
    )
    if args.source_dir is not None:
        command.extend(["--source-dir", str(args.source_dir)])
    if args.source_archive is not None:
        command.extend(["--source-archive", str(args.source_archive)])
    if args.auto_source_dir:
        command.append("--auto-source-dir")
    command.extend(
        [
            "--workers",
            str(args.workers),
            "--trace-timeout-seconds",
            str(args.trace_timeout_seconds),
            "--cache-dir",
            str(cache_dir),
        ]
    )
    return command


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


if __name__ == "__main__":
    main(sys.argv[1:])
