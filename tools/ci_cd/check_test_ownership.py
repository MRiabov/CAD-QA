"""Admit a test file only at the root that owns its language.

The rule is in ``docs/dataset/implementation/python-and-golang.md#tests``:

- a Python test lives only under ``generator/python/tests/`` (the worker),
  ``tests/ci_cd/`` (the CI gates), or ``tests/manual_verification/`` (the
  devtools);
- no file sits directly in ``tests/``;
- a Go test sits beside a non-test ``.go`` file in the same directory.

Archived experiments are exempt: ``experiments/old/`` is kept to re-read old
runs and is not in ``testpaths``.

Run from the repository root:

    tools/ci_cd/check-test-ownership
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from tools.ci_cd.tracked_tree import tracked_paths

PYTHON_TEST_ROOTS = (
    "generator/python/tests/",
    "tests/ci_cd/",
    "tests/manual_verification/",
)
TESTS_ROOT = "tests/"
EXEMPT_PREFIXES = ("experiments/old/", ".agents/")


class Rule(StrEnum):
    """Why a test path is not admitted."""

    PYTHON_ROOT = "python-root"
    TESTS_FILE = "tests-file"
    GO_SIBLING = "go-sibling"


MESSAGES = {
    Rule.PYTHON_ROOT: (
        "python test outside the admitted roots: " + ", ".join(PYTHON_TEST_ROOTS)
    ),
    Rule.TESTS_FILE: (
        "file directly in tests/: put it in tests/ci_cd/ or tests/manual_verification/"
    ),
    Rule.GO_SIBLING: "Go test has no non-test .go file in its directory",
}


class Violation(BaseModel):
    """One test path that the rule does not admit."""

    model_config = ConfigDict(frozen=True)

    path: str = Field(min_length=1)
    rule: Rule


def is_python_test(path: str) -> bool:
    """Return whether pytest would collect the path by name."""

    name = Path(path).name
    return path.endswith(".py") and (
        name.startswith("test_") or name.endswith("_test.py")
    )


def go_files_by_directory(paths: Sequence[str]) -> dict[str, int]:
    """Return the number of non-test .go files per directory."""

    counts: dict[str, int] = defaultdict(int)
    for path in paths:
        if path.endswith(".go") and not path.endswith("_test.go"):
            counts[Path(path).parent.as_posix()] += 1
    return dict(counts)


def check(paths: Sequence[str]) -> list[Violation]:
    """Return every tracked test path that the language rule does not admit."""

    admitted = [path for path in paths if not path.startswith(EXEMPT_PREFIXES)]
    go_files = go_files_by_directory(admitted)
    rows: list[Violation] = []
    for path in admitted:
        if path.startswith(TESTS_ROOT) and path.count("/") == 1:
            rows.append(Violation(path=path, rule=Rule.TESTS_FILE))
            continue
        if is_python_test(path) and not path.startswith(PYTHON_TEST_ROOTS):
            rows.append(Violation(path=path, rule=Rule.PYTHON_ROOT))
            continue
        if (
            path.endswith("_test.go")
            and go_files.get(Path(path).parent.as_posix(), 0) == 0
        ):
            rows.append(Violation(path=path, rule=Rule.GO_SIBLING))
    return sorted(rows, key=lambda row: row.path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="repository root (default: the current directory)",
    )
    args = parser.parse_args(argv)

    paths = tracked_paths(args.root.resolve())
    rows = check(paths)

    if not rows:
        python_tests = sum(1 for path in paths if is_python_test(path))
        go_tests = sum(1 for path in paths if path.endswith("_test.go"))
        print(
            f"test ownership ok: {python_tests} python test(s), {go_tests} go test(s)"
        )
        return 0

    for row in rows:
        print(f"{row.path}: {MESSAGES[row.rule]}", file=sys.stderr)
    print(
        f"test ownership: {len(rows)} path(s) not admitted; see "
        "docs/dataset/implementation/python-and-golang.md#tests",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
