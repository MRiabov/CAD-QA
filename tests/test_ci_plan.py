"""Contract tests for the CI plan classifier.

The classifier decides which test suites start. A path it does not know must
wake every suite; silently skipping a suite is the expensive mistake.
"""

from __future__ import annotations

import pytest

from tools.ci_plan import JobPlan, Suite, changed_paths, plan, suites_for


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("generator/main.go", {Suite.GO}),
        ("cadqa_dataset_generator/cli.py", {Suite.GO, Suite.PYTHON}),
        ("contracts/worker/v1/envelope.schema.json", {Suite.GO, Suite.PYTHON}),
        ("tests/test_worker_cli.py", {Suite.PYTHON}),
        ("tools/ci_cd/check_dont_say.py", {Suite.PYTHON}),
        (
            "docs/dataset/implementation/pipeline/testing/golden/record.json",
            {Suite.PYTHON},
        ),
        ("docs/glossary.md", set()),
        ("plans/nov-21/ci-contract.md", set()),
        ("balance.yaml", {Suite.GO}),
        ("checks.yaml", {Suite.GO}),
        ("tolerance.yaml", {Suite.GO}),
        ("prompts.yaml", {Suite.GO, Suite.PYTHON}),
        ("prompt-templates.yaml", {Suite.GO, Suite.PYTHON}),
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
    assert plan(["tests/test_ci_plan.py"]) == JobPlan(go=False, python=True)


def test_unknown_base_or_head_is_unknown() -> None:
    assert changed_paths("", "abc") is None
    assert changed_paths("abc", "") is None
    assert changed_paths("0" * 40, "abc") is None
