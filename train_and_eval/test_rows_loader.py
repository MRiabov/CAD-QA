"""Tests for rows_loader.py — local graph-first artifact -> harness row shape."""

import json
import os as _os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # train_and_eval root

import pytest

from rows_loader import load_local_rows

RELEASE_10K = Path(
    "runs/current_cadevolve1000_10k_regen_20260613/release_10k/rows.parquet"
)


def _write_jsonl(records: list[dict]) -> Path:
    path = Path(tempfile.mkdtemp()) / "rows.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
    return path


@pytest.fixture(scope="module")
def release_rows() -> list[dict]:
    if not RELEASE_10K.exists():
        pytest.skip("release_10k artifact not present")
    return load_local_rows(RELEASE_10K)


def test_loads_train_split_only(release_rows):
    assert len(release_rows) > 9000  # full train split; exact count depends on the artifact
    assert all(r["answer_format"] in {"candidate_label", "coordinate", "text"} for r in release_rows)
    assert all(r["logical_hop_count"] in {2, 3, 4, 5} for r in release_rows)


def test_gold_decoded(release_rows):
    sample = next(r for r in release_rows if r["answer_format"] == "candidate_label")
    assert isinstance(sample["gold_answer"], str)  # JSON-encoded '"A"' -> 'A'
    coord = next(r for r in release_rows if r["answer_format"] == "coordinate")
    assert isinstance(coord["gold_answer"], list)
    assert len(coord["gold_answer"]) == 3


def test_tool_suffix_appended_and_opt_out(release_rows):
    assert all("[answer contract]" in r["prompt"] for r in release_rows)
    plain = load_local_rows(RELEASE_10K, tool_suffix=False)
    assert all("[answer contract]" not in r["prompt"] for r in plain)
    assert len(plain) == len(release_rows)


def test_split_filter():
    records = [
        {"row_id": "a", "prompt": "p", "answer_format": "text",
         "gold_answer": '"wp1"', "split": "train", "logical_hop_count": 2},
        {"row_id": "b", "prompt": "p", "answer_format": "text",
         "gold_answer": '"wp2"', "split": "test", "logical_hop_count": 2},
        {"row_id": "c", "prompt": "p", "answer_format": "text",
         "gold_answer": '"wp3"', "split": "train", "logical_hop_count": 2,
         "release_ready": False},
    ]
    path = _write_jsonl(records)
    rows = load_local_rows(path, split="train")
    assert [r["row_id"] for r in rows] == ["a"]


def test_jsonl_gold_decoding_and_suffix():
    path = _write_jsonl([
        {"row_id": "x", "prompt": "Identify the target.",
         "answer_format": "coordinate", "gold_answer": "[-1.5, 0, 2.25]",
         "split": "train", "logical_hop_count": 3},
    ])
    rows = load_local_rows(path)
    assert rows[0]["gold_answer"] == [-1.5, 0, 2.25]
    assert "submit_coordinate" in rows[0]["prompt"]


def test_max_rows():
    rows = load_local_rows(RELEASE_10K, max_rows=5) if RELEASE_10K.exists() else _write_jsonl([
        {"row_id": f"r{i}", "prompt": "p", "answer_format": "text",
         "gold_answer": '"x"', "split": "train"} for i in range(10)
    ])
    assert len(rows) == 5


def test_loader_gold_grades_via_tool_call_matches():
    """Decoded loader gold must grade via tool_call_matches for all formats."""
    from tool_calls import extract_tool_call, format_to_tool, tool_call_matches

    records = [
        {"row_id": "l1", "prompt": "p", "answer_format": "candidate_label",
         "gold_answer": '"A"', "split": "train", "logical_hop_count": 2},
        {"row_id": "l2", "prompt": "p", "answer_format": "coordinate",
         "gold_answer": "[-47.584951, 0, -127.964585]", "split": "train", "logical_hop_count": 2},
        {"row_id": "l3", "prompt": "p", "answer_format": "text",
         "gold_answer": '"wp7"', "split": "train", "logical_hop_count": 2},
    ]
    rows = load_local_rows(_write_jsonl(records))
    calls = {
        "candidate_label": '{"name": "submit_label", "arguments": {"label": "A"}}',
        "coordinate": '{"name": "submit_coordinate", "arguments": {"value": [-47.585, 0, -127.965]}}',
        "text": '{"name": "submit_text", "arguments": {"text": "wp7"}}',
    }
    for row in rows:
        tool = format_to_tool(row["answer_format"])
        parsed = extract_tool_call(calls[row["answer_format"]], tool)
        assert parsed is not None
        # decoded gold (from the loader) passes straight into the matcher
        assert tool_call_matches(parsed[0], parsed[1], row["gold_answer"], row["answer_format"])



