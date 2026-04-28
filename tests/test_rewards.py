from pathlib import Path

from cad_qa.jsonio import read_json, read_jsonl, write_jsonl
from cad_qa.rewards import score_candidate_records, score_candidate
from scripts.training.score_rejection_sampling_candidates import main as reward_main


def test_score_candidate_rewards_parse_pass_and_failures():
    row = {"id": "r1", "parse_policy": "strict_integer_v1", "answer": 3}

    assert score_candidate(row, "3")["reward"] == 1.0
    assert score_candidate(row, "4")["reward"] == -0.25
    assert score_candidate(row, "about 3")["reward"] == -1.0


def test_score_candidate_records_selects_best_bounded_candidate():
    rows = [{"id": "r1", "task_type": "operation_count", "split": "train", "parse_policy": "strict_integer_v1", "answer": 2}]
    candidates = [
        {"row_id": "r1", "candidate_id": "bad", "candidate": "1"},
        {"row_id": "r1", "candidate_id": "good", "candidate": "2"},
        {"row_id": "r1", "candidate_id": "skipped", "candidate": "2"},
    ]

    scored, report = score_candidate_records(rows, candidates, max_candidates_per_row=2)

    assert len(scored) == 2
    assert report["skipped"] == {"max_candidates_per_row": 1}
    assert report["selected_accuracy"] == 1.0


def test_reward_scoring_script_writes_artifacts(tmp_path: Path):
    rows = tmp_path / "rows.jsonl"
    candidates = tmp_path / "candidates.jsonl"
    output_dir = tmp_path / "rewards"
    write_jsonl(rows, [{"id": "r1", "task_type": "point_membership", "split": "validation", "parse_policy": "strict_enum_v1", "answer": "inside", "choices": ["inside", "outside"]}])
    write_jsonl(candidates, [{"row_id": "r1", "candidate": "inside"}])

    reward_main(["--rows", str(rows), "--candidates", str(candidates), "--output-dir", str(output_dir)])

    assert read_json(output_dir / "reward_report.json")["selected_accuracy"] == 1.0
    assert read_jsonl(output_dir / "selected_candidates.jsonl")[0]["reward"] == 1.0
