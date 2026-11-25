"""Verify the task-construction oracles with their gold queries.

Run by hand from the repository root:

    uv run python tools/manual-verification/verify_task_oracles.py
    uv run python tools/manual-verification/verify_task_oracles.py --record box-volume
    uv run python tools/manual-verification/verify_task_oracles.py --write

``--write`` records the environment and the observed stdout in each record. It
never changes the answer: a query whose output differs from ``expected_stdout``
is a failure, and the record is left alone.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from task_oracle_runner import (
    current_environment,
    load_oracles,
    query_sha256,
    run_gold_query,
)
from task_oracle_schema import GoldQueryStatus

DEFAULT_DIR = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "dataset"
    / "implementation"
    / "pipeline"
    / "testing"
    / "oracles"
    / "task-construction"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--directory",
        type=Path,
        default=DEFAULT_DIR,
        help="task-construction oracle directory",
    )
    parser.add_argument("--record", help="verify one slug")
    parser.add_argument(
        "--write",
        action="store_true",
        help="record the environment and the observed stdout",
    )
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args(argv)

    records = load_oracles(args.directory)
    if args.record:
        records = [item for item in records if item[1].slug == args.record]
        if not records:
            print(f"no record with slug {args.record!r}", file=sys.stderr)
            return 2
    if not records:
        print(f"no records under {args.directory}", file=sys.stderr)
        return 2

    failures = 0
    for path, oracle in records:
        try:
            actual = run_gold_query(oracle, timeout=args.timeout)
        except Exception as error:  # noqa: BLE001 - the CLI reports every failure
            failures += 1
            print(f"FAIL {oracle.slug}: {error}")
            continue

        expected = oracle.gold_query.expected_stdout
        if actual != expected:
            failures += 1
            print(f"FAIL {oracle.slug}: expected {expected!r}, got {actual!r}")
            continue

        print(f"ok   {oracle.slug}: {actual}")
        if args.write:
            oracle.environment = current_environment()
            oracle.gold_query.sha256 = query_sha256(oracle)
            oracle.verification.gold_query.status = GoldQueryStatus.PASSED
            oracle.verification.gold_query.stdout = actual
            oracle.verification.gold_query.checked_at = dt.date.today().isoformat()
            path.write_text(oracle.model_dump_json(indent=2) + "\n", encoding="utf-8")
            print(f"     wrote {path}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
