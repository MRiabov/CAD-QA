"""Check the directory fanout of the tracked tree.

A directory's fanout is the number of immediate subdirectories that contain at
least one tracked file. Files do not count. The default limit is 10. The
repository root has a limit of 15. An explicit exception names a path, a limit
above 10 and at most 15, and a reason.

Run from the repository root:

    uv run python tools/ci_cd/check_fanout.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_LIMIT = 10
ROOT_LIMIT = 15
ROOT = "."


class FanoutException(BaseModel):
    """An explicit allowance for one directory."""

    model_config = ConfigDict(frozen=True)

    path: str = Field(min_length=1)
    limit: int = Field(gt=DEFAULT_LIMIT, le=ROOT_LIMIT)
    reason: str = Field(min_length=1)


class FanoutViolation(BaseModel):
    """One directory that exceeds its fanout limit."""

    model_config = ConfigDict(frozen=True)

    path: str
    fanout: int = Field(ge=0)
    limit: int = Field(gt=0)
    children: list[str]


# Add an exception only for a directory that genuinely needs the extra
# subdirectories. The limit is 11-15; the reason is reviewed with the code.
EXCEPTIONS: dict[str, FanoutException] = {}


def tracked_paths(root: Path) -> list[str]:
    """Return the repository-relative paths of every tracked file."""

    result = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def build_children(paths: Sequence[str]) -> dict[str, set[str]]:
    """Return immediate subdirectories keyed by their parent directory."""

    directories: set[str] = set()
    for path in paths:
        parent = Path(path).parent
        while parent != Path(ROOT):
            directories.add(parent.as_posix())
            parent = parent.parent

    children: dict[str, set[str]] = defaultdict(set)
    for directory in directories:
        children[Path(directory).parent.as_posix()].add(directory)
    return dict(children)


def limit_for(path: str) -> int:
    """Return the fanout limit for one directory."""

    if path == ROOT:
        return ROOT_LIMIT
    exception = EXCEPTIONS.get(path)
    if exception is not None:
        return exception.limit
    return DEFAULT_LIMIT


def violations(children: Mapping[str, set[str]]) -> list[FanoutViolation]:
    """Return every directory that exceeds its fanout limit."""

    rows: list[FanoutViolation] = []
    for path, names in children.items():
        limit = limit_for(path)
        if len(names) > limit:
            rows.append(
                FanoutViolation(
                    path=path,
                    fanout=len(names),
                    limit=limit,
                    children=sorted(Path(name).name for name in names),
                )
            )
    return sorted(rows, key=lambda row: (-row.fanout, row.path))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="repository root (default: the current directory)",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    paths = tracked_paths(root)
    children = build_children(paths)
    rows = violations(children)

    if not rows:
        print(
            f"fanout ok: {len(paths)} tracked files, {len(children)} directories "
            f"with children, default {DEFAULT_LIMIT}, root {ROOT_LIMIT}"
        )
        return 0

    for row in rows:
        print(
            f"{row.path}: {row.fanout} subdirectories > limit {row.limit}: "
            f"{', '.join(row.children)}",
            file=sys.stderr,
        )
    print(
        f"fanout: {len(rows)} directory(ies) exceed the limit; nest the "
        "subdirectories or add a reviewed exception in "
        "tools/ci_cd/check_fanout.py",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
