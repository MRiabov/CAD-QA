"""Tests for the gold-query batch runner and the check, record, and accept verbs."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools" / "manual-verification"
sys.path.insert(0, str(TOOLS))

import task_oracle_runner
from task_oracle_runner import (
    GoldQueryRun,
    GoldQueryScript,
    current_environment,
    load_oracles,
    run_scripts,
    write_record,
)
from task_oracle_schema import GoldQueryStatus, VerificationStatus
from verify_task_oracles import main

ORACLES = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "dataset"
    / "implementation"
    / "pipeline"
    / "testing"
    / "oracles"
    / "task-construction"
)


requires_kernel = pytest.mark.skipif(
    importlib.util.find_spec("OCP") is None,
    reason="the check imports CadQuery and OCP",
)


def script(slug: str, body: str) -> GoldQueryScript:
    return GoldQueryScript(slug=slug, script=body)


def count_spawns(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Record each child the runner starts, and delegate to the real one."""

    spawns: list[list[str]] = []
    spawn = subprocess.Popen

    def counting(*args: object, **kwargs: object) -> subprocess.Popen[str]:
        spawns.append(list(args[0]))  # type: ignore[call-overload]
        return spawn(*args, **kwargs)  # type: ignore[call-overload]

    monkeypatch.setattr(task_oracle_runner.subprocess, "Popen", counting)
    return spawns


def copy_record(tmp_path: Path, slug: str = "box-volume") -> Path:
    target = tmp_path / f"{slug}.json"
    target.write_text(
        (ORACLES / f"{slug}.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return target


def test_a_batch_runs_every_script_in_one_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spawns = count_spawns(monkeypatch)

    runs = run_scripts(
        [script("first", 'print("a")'), script("second", 'print("b")')], timeout=30
    )

    assert [run.stdout for run in runs] == ["a", "b"]
    assert [run.error for run in runs] == [None, None]
    assert len(spawns) == 1


def test_a_failing_script_is_a_row_and_the_batch_continues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spawns = count_spawns(monkeypatch)

    runs = run_scripts(
        [
            script("first", 'print("a")'),
            script("broken", 'raise ValueError("boom")'),
            script("last", 'print("c")'),
        ],
        timeout=30,
    )

    assert [run.slug for run in runs] == ["first", "broken", "last"]
    assert runs[1].stdout is None
    assert runs[1].error is not None and "boom" in runs[1].error
    assert runs[2].stdout == "c"
    assert len(spawns) == 1


def test_a_query_that_prints_two_lines_fails() -> None:
    runs = run_scripts([script("chatty", 'print("a")\nprint("b")')], timeout=30)

    assert runs[0].error is not None
    assert "2 non-empty lines" in runs[0].error


def test_a_hanging_script_is_reported_and_the_rest_still_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spawns = count_spawns(monkeypatch)

    runs = run_scripts(
        [script("stuck", "while True:\n    pass\n"), script("after", 'print("done")')],
        timeout=1,
    )

    assert [run.slug for run in runs] == ["stuck", "after"]
    assert runs[0].error is not None and "no result within 1s" in runs[0].error
    assert runs[1].stdout == "done"
    assert len(spawns) == 2


def test_a_run_carries_either_stdout_or_an_error() -> None:
    with pytest.raises(ValueError):
        GoldQueryRun(slug="both", stdout="a", error="b")
    with pytest.raises(ValueError):
        GoldQueryRun(slug="neither")


def test_write_leaves_an_unchanged_record_alone(tmp_path: Path) -> None:
    path = copy_record(tmp_path)
    before = path.read_text(encoding="utf-8")
    ((_, oracle),) = load_oracles(tmp_path)

    assert write_record(path, oracle) is False
    assert path.read_text(encoding="utf-8") == before


def test_write_adds_the_trailing_newline_the_loader_requires(tmp_path: Path) -> None:
    path = copy_record(tmp_path)
    ((_, oracle),) = load_oracles(tmp_path)
    oracle.verification.gold_query.checked_at = "2026-11-24"

    assert write_record(path, oracle) is True
    assert path.read_text(encoding="utf-8").endswith("}\n")
    assert len(load_oracles(tmp_path)) == 1


@requires_kernel
def test_check_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = copy_record(tmp_path)
    before = path.read_bytes()

    assert main(["--directory", str(tmp_path)]) == 0

    assert path.read_bytes() == before
    assert capsys.readouterr().out.startswith("ok   box-volume: 1000")


@requires_kernel
def test_accept_records_the_human_decision(tmp_path: Path) -> None:
    path = copy_record(tmp_path)
    ((_, oracle),) = load_oracles(tmp_path)
    oracle.environment = current_environment()
    oracle.verification.status = VerificationStatus.PROPOSED
    oracle.verification.verified_by = None
    oracle.verification.verified_at = None
    write_record(path, oracle)

    assert (
        main(
            [
                "--directory",
                str(tmp_path),
                "--accept",
                "--by",
                "tester",
                "--at",
                "2026-11-25",
            ]
        )
        == 0
    )

    ((_, accepted),) = load_oracles(tmp_path)
    assert accepted.verification.status == VerificationStatus.VERIFIED
    assert accepted.verification.verified_by == "tester"
    assert accepted.verification.verified_at == "2026-11-25"


@requires_kernel
def test_accept_refuses_a_record_whose_check_did_not_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = copy_record(tmp_path)
    ((_, oracle),) = load_oracles(tmp_path)
    oracle.environment = current_environment()
    oracle.verification.gold_query.status = GoldQueryStatus.NOT_RUN
    write_record(path, oracle)
    before = path.read_bytes()

    assert main(["--directory", str(tmp_path), "--accept", "--by", "tester"]) == 1

    assert path.read_bytes() == before
    assert "run --write first" in capsys.readouterr().out


@requires_kernel
def test_accept_refuses_a_record_from_another_environment(tmp_path: Path) -> None:
    path = copy_record(tmp_path)
    ((_, oracle),) = load_oracles(tmp_path)
    oracle.environment.python_version = "0.0.1"
    oracle.verification.status = VerificationStatus.PROPOSED
    write_record(path, oracle)

    assert main(["--directory", str(tmp_path), "--accept", "--by", "tester"]) == 1
    assert json.loads(path.read_text(encoding="utf-8"))["verification"]["status"] == (
        "proposed"
    )


@requires_kernel
def test_write_reopens_a_verified_record_whose_environment_moved(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = copy_record(tmp_path)
    ((_, oracle),) = load_oracles(tmp_path)
    oracle.environment.ocp_version = "0.0.1"
    oracle.verification.status = VerificationStatus.VERIFIED
    oracle.verification.verified_by = "tester"
    oracle.verification.verified_at = "2026-11-25"
    write_record(path, oracle)

    assert main(["--directory", str(tmp_path), "--write"]) == 0

    ((_, recorded),) = load_oracles(tmp_path)
    assert recorded.verification.status == VerificationStatus.PROPOSED
    assert recorded.verification.verified_by is None
    assert recorded.verification.verified_at is None
    assert recorded.environment == current_environment()
    assert "reopened box-volume" in capsys.readouterr().out
