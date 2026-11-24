"""Tests for the directory fanout check."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pytest
from pydantic import ValidationError

from tools.ci_cd.check_fanout import (
    DEFAULT_LIMIT,
    EXCEPTIONS,
    ROOT_LIMIT,
    FanoutException,
    build_children,
    limit_for,
    tracked_paths,
    violations,
)


def test_build_children_counts_directories_only() -> None:
    children = build_children(["a/b/c.py", "a/d.py", "e.py"])

    assert children == {".": {"a"}, "a": {"a/b"}}


def test_default_limit_is_ten() -> None:
    assert limit_for("a") == DEFAULT_LIMIT


def test_root_has_the_root_limit() -> None:
    assert limit_for(".") == ROOT_LIMIT


def test_violation_reports_the_path_and_children() -> None:
    children = {"x": {f"d{index}" for index in range(DEFAULT_LIMIT + 1)}}

    rows = violations(children)

    assert len(rows) == 1
    assert rows[0].path == "x"
    assert rows[0].fanout == DEFAULT_LIMIT + 1
    assert rows[0].limit == DEFAULT_LIMIT
    assert rows[0].children == sorted(f"d{index}" for index in range(DEFAULT_LIMIT + 1))


def test_root_allows_fifteen() -> None:
    children = {".": {f"d{index}" for index in range(ROOT_LIMIT)}}

    assert violations(children) == []


def test_root_over_fifteen_is_a_violation() -> None:
    children = {".": {f"d{index}" for index in range(ROOT_LIMIT + 1)}}

    rows = violations(children)

    assert len(rows) == 1
    assert rows[0].path == "."
    assert rows[0].limit == ROOT_LIMIT


def test_exception_allows_more(monkeypatch: pytest.MonkeyPatch) -> None:
    path = "x"
    limit = DEFAULT_LIMIT + 2
    monkeypatch.setitem(
        EXCEPTIONS,
        path,
        FanoutException(path=path, limit=limit, reason="test exception"),
    )
    children = {path: {f"d{index}" for index in range(limit)}}

    assert violations(children) == []


def test_exception_limit_is_bounded() -> None:
    with pytest.raises(ValidationError):
        FanoutException(path="x", limit=DEFAULT_LIMIT, reason="too low")
    with pytest.raises(ValidationError):
        FanoutException(path="x", limit=ROOT_LIMIT + 1, reason="too high")


def test_repository_fanout() -> None:
    root = Path(__file__).resolve().parents[2]

    paths = tracked_paths(root)

    assert paths
    assert violations(build_children(paths)) == []


def test_planned_file_tree_fanout() -> None:
    root = Path(__file__).resolve().parents[2]
    text = (root / "docs/dataset/implementation/file-trees.md").read_text(
        encoding="utf-8"
    )
    section = text.split("## Go module", 1)[1].split("```text", 1)[1].split("```", 1)[0]

    stack: list[str] = []
    children: dict[str, set[str]] = defaultdict(set)
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped or "/" not in stripped:
            continue
        token = stripped.split()[0]
        if not token.endswith("/"):
            continue
        depth = (len(line) - len(line.lstrip(" "))) // 2
        stack = stack[:depth]
        parent = "/".join(stack) if stack else "."
        children[parent].add(token.rstrip("/"))
        stack.append(token.rstrip("/"))

    over = {
        parent: sorted(names)
        for parent, names in children.items()
        if len(names) > DEFAULT_LIMIT
    }

    assert over == {}
