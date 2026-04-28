"""Run a restartable CAD-QA experiment manifest."""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
import json
from pathlib import Path
import subprocess
import time
from typing import Any

import yaml

from cad_qa.jsonio import write_json


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--runs-dir", type=Path, default=Path("runs"))
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--run", action="append")
    parser.add_argument("--with-dependencies", action="store_true")
    parser.add_argument("--skip-dependencies", action="store_true")
    parser.add_argument("--no-fail-fast", action="store_true")
    args = parser.parse_args(argv)

    manifest = _load_manifest(args.manifest)
    runs = _select_runs(manifest["runs"], names=args.run or [], with_dependencies=args.with_dependencies)
    if args.list:
        print(json.dumps({"runs": [_planned_run(run, args.runs_dir) for run in runs]}, indent=2, sort_keys=True))
        return
    summary = []
    for run in runs:
        run_dir = Path(run.get("output_dir") or args.runs_dir / run["name"])
        if args.dry_run:
            summary.append({"name": run["name"], "status": "dry_run", "command": run.get("command", [])})
            continue
        if not args.skip_dependencies:
            missing = _missing_dependencies(run, manifest["runs"], args.runs_dir)
            if missing:
                item = {"name": run["name"], "status": "incomplete", "reason": f"missing_dependencies:{','.join(missing)}"}
                summary.append(item)
                if not args.no_fail_fast:
                    break
                continue
        item = _execute_run(run, run_dir, resume=args.resume)
        summary.append(item)
        if item["status"] != "completed" and not args.no_fail_fast:
            break
    print(json.dumps({"runs": summary}, indent=2, sort_keys=True))
    if any(item["status"] not in {"completed", "dry_run"} for item in summary):
        raise SystemExit(1)


def _load_manifest(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("runs"), list):
        raise ValueError(f"invalid experiment manifest: {path}")
    return data


def _select_runs(runs: list[dict[str, Any]], *, names: list[str], with_dependencies: bool) -> list[dict[str, Any]]:
    ordered = _topological_runs(runs)
    if not names:
        return ordered
    wanted = set(names)
    if with_dependencies:
        by_name = {run["name"]: run for run in runs}
        queue = deque(names)
        while queue:
            name = queue.popleft()
            for dep in by_name[name].get("depends_on", []) or []:
                if dep not in wanted:
                    wanted.add(dep)
                    queue.append(dep)
    return [run for run in ordered if run["name"] in wanted]


def _topological_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name = {run["name"]: run for run in runs}
    indegree = {name: 0 for name in by_name}
    children: dict[str, list[str]] = defaultdict(list)
    for run in runs:
        for dep in run.get("depends_on", []) or []:
            children[dep].append(run["name"])
            indegree[run["name"]] += 1
    queue = deque([name for name, degree in indegree.items() if degree == 0])
    ordered_names: list[str] = []
    while queue:
        name = queue.popleft()
        ordered_names.append(name)
        for child in children[name]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if len(ordered_names) != len(runs):
        raise ValueError("experiment manifest contains a dependency cycle")
    return [by_name[name] for name in ordered_names]


def _missing_dependencies(run: dict[str, Any], all_runs: list[dict[str, Any]], runs_dir: Path) -> list[str]:
    by_name = {item["name"]: item for item in all_runs}
    missing = []
    for dep in run.get("depends_on", []) or []:
        dep_run = by_name[dep]
        dep_dir = Path(dep_run.get("output_dir") or runs_dir / dep)
        if not (dep_dir / "run_status.json").exists():
            missing.append(dep)
    return missing


def _execute_run(run: dict[str, Any], run_dir: Path, *, resume: bool) -> dict[str, Any]:
    status_path = run_dir / "run_status.json"
    if resume and status_path.exists():
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if status.get("status") == "completed":
            return {"name": run["name"], "status": "completed", "resumed": True}
    run_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    command = [str(item) for item in run.get("command", [])]
    started = time.time()
    with (logs_dir / "stdout.log").open("w", encoding="utf-8") as stdout, (logs_dir / "stderr.log").open("w", encoding="utf-8") as stderr:
        process = subprocess.run(command, stdout=stdout, stderr=stderr, text=True, check=False)
    status = {
        "name": run["name"],
        "kind": run.get("kind"),
        "status": "completed" if process.returncode == 0 else "failed",
        "returncode": process.returncode,
        "command": command,
        "elapsed_seconds": round(time.time() - started, 3),
        "expected_artifacts": run.get("artifacts", []),
        "missing_artifacts": _missing_artifacts(run, run_dir),
    }
    if status["missing_artifacts"] and process.returncode == 0:
        status["status"] = "incomplete"
    write_json(status_path, status)
    return status


def _missing_artifacts(run: dict[str, Any], run_dir: Path) -> list[str]:
    missing = []
    for artifact in run.get("artifacts", []) or []:
        if not (run_dir / artifact).exists():
            missing.append(artifact)
    return missing


def _planned_run(run: dict[str, Any], runs_dir: Path) -> dict[str, Any]:
    return {
        "name": run["name"],
        "kind": run.get("kind"),
        "depends_on": run.get("depends_on", []),
        "run_dir": str(Path(run.get("output_dir") or runs_dir / run["name"])),
        "command": run.get("command", []),
    }


if __name__ == "__main__":
    main()
