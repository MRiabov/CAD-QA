"""Tests for the test-ownership admission check."""

from __future__ import annotations

from pathlib import Path

from tools.ci_cd.check_test_ownership import (
    PYTHON_TEST_ROOTS,
    Rule,
    check,
    is_python_test,
    tracked_paths,
)


def rows_for(paths: list[str]) -> list[tuple[str, Rule]]:
    return [(row.path, row.rule) for row in check(paths)]


def test_python_tests_are_admitted_in_each_root() -> None:
    paths = [f"{root}test_example.py" for root in PYTHON_TEST_ROOTS]

    assert rows_for(paths) == []


def test_root_tests_file_is_rejected() -> None:
    assert rows_for(["tests/test_example.py"]) == [
        ("tests/test_example.py", Rule.TESTS_FILE)
    ]


def test_any_file_directly_in_tests_is_rejected() -> None:
    assert rows_for(["tests/data.json"]) == [("tests/data.json", Rule.TESTS_FILE)]


def test_python_test_outside_a_root_is_rejected() -> None:
    rows = rows_for(
        [
            "docs/test_example.py",
            "generator/python/cadqa_dataset_generator/test_worker.py",
        ]
    )

    assert rows == [
        ("docs/test_example.py", Rule.PYTHON_ROOT),
        (
            "generator/python/cadqa_dataset_generator/test_worker.py",
            Rule.PYTHON_ROOT,
        ),
    ]


def test_go_test_beside_code_is_admitted() -> None:
    assert (
        rows_for(
            ["generator/internal/run/run.go", "generator/internal/run/run_test.go"]
        )
        == []
    )


def test_go_test_without_a_non_test_file_is_rejected() -> None:
    assert rows_for(["generator/internal/empty/empty_test.go"]) == [
        ("generator/internal/empty/empty_test.go", Rule.GO_SIBLING)
    ]


def test_a_test_file_does_not_count_as_a_go_sibling() -> None:
    assert rows_for(
        [
            "generator/internal/empty/a_test.go",
            "generator/internal/empty/b_test.go",
        ]
    ) == [
        ("generator/internal/empty/a_test.go", Rule.GO_SIBLING),
        ("generator/internal/empty/b_test.go", Rule.GO_SIBLING),
    ]


def test_archived_experiments_are_exempt() -> None:
    assert rows_for(["experiments/old/scratch/test_scratch.py"]) == []


def test_pytest_name_detection() -> None:
    assert is_python_test("a/test_example.py")
    assert is_python_test("a/example_test.py")
    assert not is_python_test("a/example.py")


def test_repository_is_admitted() -> None:
    root = Path(__file__).resolve().parents[2]

    assert check(tracked_paths(root)) == []
