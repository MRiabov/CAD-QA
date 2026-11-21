"""Which CI test suites a diff can reach, decided before they start.

The ``quality-and-plan`` job always runs: it owns the checks that read the tree
rather than the changed lines, and it computes this plan. The plan decides
whether the Go and Python suites start.

Classification fails open. A path no rule claims, an empty diff, or a diff that
cannot be read wakes every suite. Skipping a suite that should have run is the
expensive mistake; running one that need not have is the cheap one. A new
top-level path therefore costs a full run until this table learns about it.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from enum import StrEnum

from pydantic import BaseModel, Field


class Suite(StrEnum):
    """A test suite the CI can start."""

    GO = "go"
    PYTHON = "python"


class JobPlan(BaseModel):
    """The test suites the CI should start.

    Both fields default to true: the fail-open plan. Construct it without
    arguments when the diff is unknown.
    """

    go: bool = Field(default=True, description="Start the Go suite.")
    python: bool = Field(default=True, description="Start the Python suite.")


# A path maps to the suites it can reach. Paths not listed here are unknown and
# wake every suite; keep this table in step with the CI contract.
GO_ONLY_PATHS = frozenset({"balance.yaml", "checks.yaml", "tolerance.yaml"})
BOTH_PATHS = frozenset(
    {
        "prompts.yaml",
        "prompt-templates.yaml",
        "pyproject.toml",
        "uv.lock",
        ".python-version",
    }
)
# Known paths that only the always-on quality job needs.
QUALITY_ONLY_PREFIXES = (
    "docs/",
    "plans/",
    "specs/",
    "experiments/",
    ".agents/",
)
QUALITY_ONLY_PATHS = frozenset(
    {
        ".gitignore",
        "README.md",
        "epics-and-stories.md",
        "epics-and-stories.yaml",
        "human-paper-spec.md",
        "overnight-task.md",
        ".rumdl.toml",
        ".pre-commit-config.yaml",
    }
)


def suites_for(path: str) -> frozenset[Suite] | None:
    """The suites a repository-relative path can reach.

    ``None`` means the path is unknown, which the caller treats as "wake every
    suite". A known path with no test coverage returns the empty set.
    """

    match path:
        case _ if path.startswith("generator/"):
            return frozenset({Suite.GO})
        case _ if path.startswith("cadqa_dataset_generator/"):
            # The Go bridge test starts the Python worker as a child process.
            return frozenset({Suite.GO, Suite.PYTHON})
        case _ if path.startswith("contracts/"):
            # The Python validator and the generated Go types both read these.
            return frozenset({Suite.GO, Suite.PYTHON})
        case _ if path.startswith(("tests/", "tools/")):
            return frozenset({Suite.PYTHON})
        case _ if path.startswith("docs/dataset/implementation/pipeline/testing/"):
            # Golden records and fixtures are read by the Python tests.
            return frozenset({Suite.PYTHON})
        case _ if path.startswith(QUALITY_ONLY_PREFIXES):
            return frozenset()
        case _ if path.startswith(".github/workflows/"):
            return frozenset({Suite.GO, Suite.PYTHON})
        case _ if path in GO_ONLY_PATHS:
            return frozenset({Suite.GO})
        case _ if path in BOTH_PATHS:
            return frozenset({Suite.GO, Suite.PYTHON})
        case _ if path in QUALITY_ONLY_PATHS:
            return frozenset()
        case _:
            return None


def plan(paths: Sequence[str]) -> JobPlan:
    """The suites the given changed paths require.

    An empty sequence is an unknown diff, not a change that touches nothing: it
    wakes every suite. A path with no rule does the same.
    """

    if not paths:
        return JobPlan()

    suites: set[Suite] = set()
    for path in paths:
        reached = suites_for(path)
        if reached is None:
            return JobPlan()
        suites.update(reached)

    return JobPlan(go=Suite.GO in suites, python=Suite.PYTHON in suites)


def changed_paths(base: str, head: str) -> list[str] | None:
    """The paths between two commits, or ``None`` when the diff is unknown."""

    if not base or not head or set(base) == {"0"}:
        return None

    completed = subprocess.run(
        ["git", "diff", "--name-only", base, head],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        print(
            f"cannot diff {base}..{head}: {completed.stderr.strip()}",
            file=sys.stderr,
        )
        return None

    return [line for line in completed.stdout.splitlines() if line]


def main(argv: Sequence[str] | None = None) -> int:
    """Print the plan as JSON and, for the workflow, as step outputs."""

    parser = argparse.ArgumentParser(
        prog="ci_plan",
        description="Decide which CI test suites a diff can reach.",
    )
    parser.add_argument("--base", default="", help="base commit; empty means unknown")
    parser.add_argument("--head", default="", help="head commit; empty means unknown")
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="append go=... and python=... to GITHUB_OUTPUT",
    )
    args = parser.parse_args(argv)

    paths = changed_paths(args.base, args.head)
    job_plan = JobPlan() if paths is None else plan(paths)
    if paths is not None:
        print(f"changed paths: {len(paths)}", file=sys.stderr)
    print(job_plan.model_dump_json())

    if args.github_output:
        output = os.environ.get("GITHUB_OUTPUT")
        if not output:
            parser.error("--github-output needs GITHUB_OUTPUT")
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"go={str(job_plan.go).lower()}\n")
            handle.write(f"python={str(job_plan.python).lower()}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
