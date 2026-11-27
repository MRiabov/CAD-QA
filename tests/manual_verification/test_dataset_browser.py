"""Tests for the dataset browser API and scene cache."""

from __future__ import annotations

import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools" / "manual-verification"
sys.path.insert(0, str(TOOLS))

from dataset_browser import TaskIndex, build_handler
from task_oracles import load_oracle_rows
from task_release import load_release_rows, prompt_preview
from task_scene import PrimitiveKind

PROGRAM = """import cadquery as cq

result = cq.Workplane("XY").box(10, 20, 5)
"""

TASKS = (
    (
        "cadqatask:aaa",
        "train",
        "main",
        "edge",
        "length",
        "How long is the target edge?",
        "1000",
    ),
    (
        "cadqatask:bbb",
        "test",
        "warmup",
        "face",
        "area",
        "What is the target face area?",
        "600",
    ),
    (
        "cadqatask:ccc",
        "train",
        "main",
        "edge",
        "length",
        "How long is the other target edge?",
        "400",
    ),
)


def prompt(question: str) -> str:
    return (
        "Directions use the program frame.\n\n"
        "```python\n" + PROGRAM + "```\n\n" + question + "\n"
    )


def write_release(path: Path) -> None:
    answer = pa.struct([("kind", pa.string()), ("number_text", pa.string())])
    tolerance = pa.struct(
        [("kind", pa.string()), ("value_text", pa.string()), ("unit", pa.string())]
    )
    clue_reduction = pa.struct(
        [("clue_type", pa.string()), ("clue_reduction_form", pa.string())]
    )
    choice = pa.struct([("label", pa.string()), ("candidate", pa.string())])
    table = pa.table(
        {
            "task_id": [task[0] for task in TASKS],
            "split": [task[1] for task in TASKS],
            "subset": [task[2] for task in TASKS],
            "prompt": [prompt(task[5]) for task in TASKS],
            "prompt_sha256": [f"{index:064x}" for index in range(1, 4)],
            "program_id": ["cadqaprog:shared"] * 3,
            "program_sha256": ["b" * 64] * 3,
            "cadevolve_program_family_id": ["family"] * 3,
            "task_reasoning_step_count": [1, 2, 3],
            "target_category": [task[3] for task in TASKS],
            "clue_types": pa.array([[]] * 3, type=pa.list_(pa.string())),
            "clue_reduction_form_profile": pa.array(
                [[]] * 3, type=pa.list_(clue_reduction)
            ),
            "answer_format": ["number"] * 3,
            "answer_meaning": [task[4] for task in TASKS],
            "geometry_required": [True] * 3,
            "gold_answer": pa.array(
                [{"kind": "number", "number_text": task[6]} for task in TASKS],
                type=answer,
            ),
            "tolerance": pa.array(
                [{"kind": "absolute", "value_text": "0.5", "unit": "millimetre"}] * 3,
                type=tolerance,
            ),
            "scoring_rule": ["numeric_tolerance"] * 3,
            "answer_sha256": ["c" * 64] * 3,
            "choices": pa.array([[]] * 3, type=pa.list_(choice)),
        }
    )
    pq.write_table(table, path)


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


@pytest.fixture()
def index(tmp_path: Path) -> TaskIndex:
    table = tmp_path / "release.parquet"
    write_release(table)
    return TaskIndex(load_release_rows(table), tmp_path / "cache", "release")


@pytest.fixture()
def origin(tmp_path: Path, index: TaskIndex) -> str:
    dist = tmp_path / "dist"
    server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(index, dist))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as response:
        return __import__("json").loads(response.read())


def get_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.read().decode("utf-8")


def test_prompt_preview_strips_the_program_fence() -> None:
    preview = prompt_preview(prompt("How long is the target edge?"))
    assert preview == "How long is the target edge?"
    assert "Directions" not in preview
    assert "import cadquery" not in preview


def test_page_filters_and_paginates(index: TaskIndex) -> None:
    page = index.page(
        offset=0,
        limit=2,
        search="",
        split="",
        subset="",
        target_category="",
        answer_meaning="",
        order="file",
        seed="0",
    )
    assert page.total == 3
    assert [task.task_id for task in page.tasks] == ["cadqatask:aaa", "cadqatask:bbb"]

    train = index.page(
        offset=0,
        limit=50,
        search="",
        split="train",
        subset="",
        target_category="",
        answer_meaning="",
        order="file",
        seed="0",
    )
    assert train.total == 2

    area = index.page(
        offset=0,
        limit=50,
        search="area",
        split="",
        subset="",
        target_category="",
        answer_meaning="",
        order="file",
        seed="0",
    )
    assert [task.task_id for task in area.tasks] == ["cadqatask:bbb"]

    random_page = index.page(
        offset=0,
        limit=50,
        search="",
        split="",
        subset="",
        target_category="",
        answer_meaning="",
        order="random",
        seed="seed",
    )
    assert {task.task_id for task in random_page.tasks} == {
        "cadqatask:aaa",
        "cadqatask:bbb",
        "cadqatask:ccc",
    }


def test_detail_has_program_and_diagnostics(index: TaskIndex) -> None:
    task = index.detail("cadqatask:aaa")
    assert task.answer == "1000"
    assert "result = cq.Workplane" in task.program
    assert {entry.label for entry in task.diagnostics} >= {"task_id", "tolerance"}


def test_scene_is_cached_by_program(index: TaskIndex, tmp_path: Path) -> None:
    pytest.importorskip("cadquery")
    first = index.scene("cadqatask:aaa")
    second = index.scene("cadqatask:bbb")
    primitive_kinds = {part.primitive_kind for part in first.parts}
    assert primitive_kinds == {PrimitiveKind.TRIANGLES, PrimitiveKind.LINES}
    assert first.triangle_count > 0
    assert first.parts[0].positions == second.parts[0].positions
    assert len(list((tmp_path / "cache").glob("*.json"))) == 1


def test_api_serves_tasks_and_detail(origin: str) -> None:
    facets = get_json(f"{origin}/api/facets")
    assert facets["task_count"] == 3

    page = get_json(f"{origin}/api/tasks?limit=2")
    assert page["total"] == 3
    assert len(page["tasks"]) == 2

    task = get_json(f"{origin}/api/tasks/cadqatask%3Aaaa")
    assert task["answer"] == "1000"
    assert "How long is the target edge?" in task["prompt"]


def test_api_serves_the_scene(origin: str) -> None:
    pytest.importorskip("cadquery")
    scene = get_json(f"{origin}/api/tasks/cadqatask%3Aaaa/scene")
    assert scene["triangle_count"] > 0
    assert {part["primitive_kind"] for part in scene["parts"]} == {
        "triangles",
        "lines",
    }


def test_api_rejects_an_unknown_task(origin: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as error:
        get_json(f"{origin}/api/tasks/cadqatask%3Amissing")
    assert error.value.code == 404


def test_static_fallback_names_the_build_step(origin: str) -> None:
    page = get_text(f"{origin}/")
    assert "Dataset browser is not built" in page
    assert "pnpm build" in page


def test_static_serves_the_built_index(tmp_path: Path, index: TaskIndex) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(
        "<html>dataset browser shell</html>", encoding="utf-8"
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(index, dist))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        origin = f"http://127.0.0.1:{server.server_port}"
        assert "dataset browser shell" in get_text(f"{origin}/")
        assert "dataset browser shell" in get_text(f"{origin}/tasks/anything")
        with pytest.raises(urllib.error.HTTPError) as error:
            get_text(f"{origin}/favicon.ico")
        assert error.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_gold_index_serves_the_checked_in_records(tmp_path: Path) -> None:
    index = TaskIndex(load_oracle_rows(ORACLES), tmp_path / "cache", "gold")

    assert index.facets.input_kind == "gold"
    assert index.facets.task_count == 13
    assert index.facets.splits == ["gold"]
    assert index.facets.subsets == ["oracle"]

    detail = index.detail("box-with-hole-topology-change")
    assert detail.prompt is None
    assert detail.answer == "2"
    assert detail.oracle is not None
    assert detail.oracle.verification.status.value == "verified"
    assert detail.oracle.gold_query.expected_stdout == "2"
    assert detail.oracle.task.target_category.value == "operation"
    assert (
        detail.oracle.task.question == "How many faces does the cutBlind operation add?"
    )

    page = index.page(
        offset=0,
        limit=50,
        search="topology",
        split="",
        subset="",
        target_category="",
        answer_meaning="",
        order="file",
        seed="0",
    )
    assert [task.task_id for task in page.tasks] == ["box-with-hole-topology-change"]
    assert page.tasks[0].preview == "How many faces does the cutBlind operation add?"


def test_gold_scene_renders_the_program(tmp_path: Path) -> None:
    pytest.importorskip("cadquery")
    index = TaskIndex(load_oracle_rows(ORACLES), tmp_path / "cache", "gold")

    first = index.scene("box-volume")
    second = index.scene("box-face-count")

    assert first.triangle_count > 0
    assert first.parts[0].positions == second.parts[0].positions
    assert len(list((tmp_path / "cache").glob("*.json"))) == 1
