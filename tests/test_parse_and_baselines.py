from cad_qa.baselines import run_baselines
from cad_qa.parse import grade_candidate


def test_numeric_four_sigfig_policy_accepts_rounded_answer():
    row = {"parse_policy": "numeric_4_sigfig_v1", "answer": 1234.567, "numeric_tolerance": 0.0}

    assert grade_candidate(row, "1235")["correct"]
    assert not grade_candidate(row, "1200")["correct"]


def test_bbox_policy_accepts_json_bbox():
    row = {
        "parse_policy": "strict_json_bbox_v1",
        "answer": {"min": [0.0, 0.0, 0.0], "max": [10.0, 20.0, 30.0]},
        "numeric_tolerance": 1e-6,
    }

    assert grade_candidate(row, '{"min":[0,0,0],"max":[10,20,30]}')["correct"]
    assert not grade_candidate(row, '{"min":[0,0,0],"max":[10,20,29]}')["correct"]


def test_oracle_baseline_scores_perfect():
    rows = [
        {
            "id": "a",
            "task_type": "operation_count",
            "split": "train",
            "parse_policy": "strict_integer_v1",
            "answer": 2,
            "answer_type": "integer",
            "labels": {},
        },
        {
            "id": "b",
            "task_type": "point_membership",
            "split": "train",
            "parse_policy": "strict_enum_v1",
            "answer": "inside",
            "choices": ["inside", "outside"],
            "answer_type": "enum",
            "labels": {},
        },
    ]

    result = run_baselines(rows)

    assert result["oracle"]["accuracy"] == 1.0
