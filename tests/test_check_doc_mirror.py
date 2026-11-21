"""Tests for the doc-mirror check."""

from __future__ import annotations

from pathlib import Path

from tools.ci_cd.check_doc_mirror import (
    FindingType,
    Side,
    check,
    expected_docs,
)


def _pipeline(root: Path) -> Path:
    return root / "docs/dataset/implementation/pipeline"


def _write(path: Path, text: str = "# doc\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_repository_mirrors_are_complete() -> None:
    report = check()

    assert report.ok, [finding.model_dump() for finding in report.findings]
    assert report.docs_checked > 0
    assert report.dirs_checked > 0


def test_missing_test_counterpart_is_reported(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    _write(pipeline / "01a-read-metadata.md")
    _write(pipeline / "streamlined/01a-read-metadata.md")
    _write(pipeline / "testing/README.md")

    report = check(tmp_path)

    assert [
        (finding.finding_type, finding.side, finding.relative_path)
        for finding in report.findings
    ] == [
        (FindingType.MISSING_DOC, Side.TESTING, "01a-read-metadata.md"),
    ]


def test_missing_stage_folder_is_reported(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    _write(pipeline / "03-task-generation/03a-allocate/README.md")
    _write(pipeline / "streamlined/03-task-generation/03a-allocate/README.md")
    _write(pipeline / "testing/README.md")

    report = check(tmp_path)

    assert FindingType.MISSING_DIR in {
        finding.finding_type for finding in report.findings
    }


def test_unexpected_mirror_doc_is_reported(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    _write(pipeline / "streamlined/README.md")
    _write(pipeline / "testing/README.md")
    _write(pipeline / "streamlined/leftover.md")

    report = check(tmp_path)

    assert [
        (finding.finding_type, finding.side, finding.relative_path)
        for finding in report.findings
    ] == [
        (FindingType.UNEXPECTED_DOC, Side.STREAMLINED, "leftover.md"),
    ]


def test_allowed_additions_are_not_reported(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    _write(pipeline / "streamlined/README.md")
    _write(pipeline / "streamlined/models/03-task-generation.md")
    _write(pipeline / "testing/README.md")
    _write(pipeline / "testing/00-testing-strategy.md")
    _write(pipeline / "testing/fixtures/README.md")

    report = check(tmp_path)

    assert report.ok


def test_decision_and_algorithm_docs_are_exempt(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    _write(pipeline / "03-task-generation/decisions.md")
    _write(pipeline / "03-task-generation/algorithm/census.md")
    _write(pipeline / "streamlined/README.md")
    _write(pipeline / "testing/README.md")

    assert expected_docs(pipeline) == set()
    assert check(tmp_path).ok
