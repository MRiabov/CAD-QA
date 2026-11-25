"""Check, record, and accept the task-construction oracles.

Run by hand from the repository root:

    uv run python tools/manual-verification/verify_task_oracles.py
    uv run python tools/manual-verification/verify_task_oracles.py --record box-volume
    uv run python tools/manual-verification/verify_task_oracles.py --write
    uv run python tools/manual-verification/verify_task_oracles.py --accept --by MRiabov

The check executes every selected record's gold query and compares the printed
line with ``expected_stdout``. It writes nothing, and it never changes the
answer. ``--write`` records the environment, the observed stdout, and the date
on the records that pass, rewriting only the files whose bytes change.
``--accept`` records a human acceptance and runs no gold query, so accepting a
reviewed record costs one kernel import for the version stamp rather than one
query per record.
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
    run_gold_queries,
    write_record,
)
from task_oracle_schema import (
    Environment,
    GoldQueryStatus,
    TaskOracle,
    VerificationStatus,
)

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

Record = tuple[Path, TaskOracle]


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    records = [
        record
        for record in load_oracles(args.directory)
        if args.record is None or record[1].slug == args.record
    ]
    if args.record is not None and not records:
        print(f"no record with slug {args.record!r}", file=sys.stderr)
        return 2
    if not records:
        print(f"no records under {args.directory}", file=sys.stderr)
        return 2

    if args.accept:
        return _accept(records, by=args.by, at=args.at or _today())
    return _check(records, write=args.write, timeout=args.timeout)


def _check(records: list[Record], *, write: bool, timeout: int) -> int:
    """Run every gold query and report each result as one line."""

    runs = run_gold_queries([oracle for _, oracle in records], timeout=timeout)
    environment = current_environment() if write else None
    failures = 0
    for (path, oracle), run in zip(records, runs, strict=True):
        if run.error is not None:
            failures += 1
            print(f"FAIL {oracle.slug}: {run.error}")
            continue
        expected = oracle.gold_query.expected_stdout
        if run.stdout != expected:
            failures += 1
            print(f"FAIL {oracle.slug}: expected {expected!r}, got {run.stdout!r}")
            continue
        print(f"ok   {oracle.slug}: {run.stdout}")
        if environment is not None:
            _record(path, oracle, run.stdout, environment)
    return 1 if failures else 0


def _record(
    path: Path, oracle: TaskOracle, stdout: str, environment: Environment
) -> None:
    """Stamp the machine check; reopen a record whose environment moved."""

    moved = oracle.environment != environment
    oracle.environment = environment
    oracle.gold_query.sha256 = query_sha256(oracle)
    check = oracle.verification.gold_query
    check.status = GoldQueryStatus.PASSED
    check.stdout = stdout
    check.checked_at = _today()
    reopened = moved and oracle.verification.status == VerificationStatus.VERIFIED
    if reopened:
        oracle.verification.status = VerificationStatus.PROPOSED
        oracle.verification.verified_by = None
        oracle.verification.verified_at = None
    written = write_record(path, oracle)
    print(f"     {'wrote' if written else 'unchanged'} {path}")
    if reopened:
        print(f"     reopened {oracle.slug}: the environment changed, review it again")


def _accept(records: list[Record], *, by: str, at: str) -> int:
    """Record a human acceptance without executing any geometry."""

    environment = current_environment()
    failures = 0
    for path, oracle in records:
        blocker = _acceptance_blocker(oracle, environment)
        if blocker is not None:
            failures += 1
            print(f"FAIL {oracle.slug}: {blocker}")
            continue
        oracle.verification.status = VerificationStatus.VERIFIED
        oracle.verification.verified_by = by
        oracle.verification.verified_at = at
        print(f"ok   {oracle.slug}: accepted by {by} on {at}")
        written = write_record(path, oracle)
        print(f"     {'wrote' if written else 'unchanged'} {path}")
    return 1 if failures else 0


def _acceptance_blocker(oracle: TaskOracle, environment: Environment) -> str | None:
    """Why this record cannot be accepted yet, or ``None``."""

    check = oracle.verification.gold_query
    if check.status != GoldQueryStatus.PASSED:
        return f"the gold query is {check.status.value}; run --write first"
    if check.stdout != oracle.gold_query.expected_stdout:
        return "the recorded stdout differs from expected_stdout; run --write first"
    if oracle.environment != environment:
        return (
            "the recorded environment differs from the current one; run --write first"
        )
    return None


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--directory",
        type=Path,
        default=DEFAULT_DIR,
        help="task-construction oracle directory",
    )
    parser.add_argument("--record", help="check one slug")
    parser.add_argument(
        "--write",
        action="store_true",
        help=(
            "record the environment and the observed stdout; a verified record "
            "whose environment moved is reopened"
        ),
    )
    parser.add_argument(
        "--accept",
        action="store_true",
        help="record a human acceptance; runs no gold query",
    )
    parser.add_argument("--by", help="the person accepting the record")
    parser.add_argument(
        "--at", help="the acceptance date, YYYY-MM-DD; defaults to today"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help=(
            "seconds one gold query may take, including the first one's kernel import"
        ),
    )
    args = parser.parse_args(argv)
    if args.write and args.accept:
        parser.error("--write and --accept are separate steps")
    if args.accept and not args.by:
        parser.error("--accept needs --by")
    if args.by and not args.accept:
        parser.error("--by only applies to --accept")
    if args.at and not args.accept:
        parser.error("--at only applies to --accept")
    if args.by is not None and not 1 <= len(args.by) <= 200:
        parser.error("--by needs 1 to 200 characters")
    if args.at is not None:
        try:
            dt.date.fromisoformat(args.at)
        except ValueError:
            parser.error("--at needs a YYYY-MM-DD date")
    if args.timeout < 1:
        parser.error("--timeout needs at least one second")
    return args


def _today() -> str:
    return dt.date.today().isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
