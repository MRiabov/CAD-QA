"""Contract tests for the CI plan classifier.

The classifier decides which test suites start. A path it does not know must
wake every suite; silently skipping a suite is the expensive mistake.
"""

from __future__ import annotations

import pytest

from tools.ci_cd.ci_plan import JobPlan, Suite, changed_paths, plan, suites_for


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("generator/main.go", {Suite.GO}),
        (
            "generator/python/cadqa_dataset_generator/worker.py",
            {Suite.GO, Suite.PYTHON},
        ),
        ("generator/python/tests/test_worker.py", {Suite.GO, Suite.PYTHON}),
        ("contracts/worker/v1/envelope.schema.json", {Suite.GO, Suite.PYTHON}),
        ("tests/ci_cd/test_check_fanout.py", {Suite.PYTHON}),
        ("tools/ci_cd/check_dont_say.py", {Suite.PYTHON}),
        ("tests/manual_verification/test_dataset_browser.py", {Suite.PYTHON}),
        (
            "docs/dataset/implementation/pipeline/testing/golden/record.json",
            {Suite.GO},
        ),
        ("docs/glossary.md", set()),
        ("plans/nov-21/ci-contract.md", set()),
        ("generator/config/balance.yaml", {Suite.GO}),
        ("generator/config/release-checks.yaml", {Suite.GO}),
        ("generator/config/tolerance.yaml", {Suite.GO}),
        ("generator/config/prompts.yaml", {Suite.GO}),
        ("pyproject.toml", {Suite.GO, Suite.PYTHON}),
        ("uv.lock", {Suite.GO, Suite.PYTHON}),
        (".python-version", {Suite.GO, Suite.PYTHON}),
        (".github/workflows/ci.yml", {Suite.GO, Suite.PYTHON}),
        ("README.md", set()),
        (".rumdl.toml", set()),
    ],
)
def test_suites_for_known_paths(path: str, expected: set[Suite]) -> None:
    assert suites_for(path) == frozenset(expected)


def test_suites_for_unknown_path_is_none() -> None:
    assert suites_for("new-top-level/file.txt") is None


def test_empty_diff_wakes_both() -> None:
    assert plan([]) == JobPlan(go=True, python=True)


def test_unknown_path_wakes_both() -> None:
    assert plan(["generator/main.go", "new-top-level/file.txt"]) == JobPlan(
        go=True,
        python=True,
    )


def test_mixed_known_paths_union() -> None:
    assert plan(["generator/main.go", "tests/test_worker_cli.py"]) == JobPlan(
        go=True,
        python=True,
    )


def test_quality_only_diff_runs_neither() -> None:
    assert plan(["docs/glossary.md", "README.md"]) == JobPlan(go=False, python=False)


def test_go_only_diff_skips_python() -> None:
    assert plan(["generator/internal/run/run.go"]) == JobPlan(go=True, python=False)


def test_python_only_diff_skips_go() -> None:
    assert plan(["tests/ci_cd/test_ci_plan.py"]) == JobPlan(go=False, python=True)


def test_unknown_base_or_head_is_unknown() -> None:
    assert changed_paths("", "abc") is None
    assert changed_paths("abc", "") is None
    assert changed_paths("0" * 40, "abc") is None
