from cad_qa.baselines import baseline_predictions, run_baselines
from cad_qa.parse import grade_candidate


def test_numeric_four_sigfig_policy_accepts_rounded_answer():
    row = {
        "parse_policy": "numeric_4_sigfig_v1",
        "answer": 1234.567,
        "numeric_tolerance": 0.0,
    }

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


def test_strict_json_policy_accepts_exact_json():
    row = {
        "parse_policy": "strict_json_v1",
        "answer": {"feature_id": "wp0", "operation": "Workplane"},
    }

    assert grade_candidate(row, '{"operation":"Workplane","feature_id":"wp0"}')[
        "correct"
    ]
    assert not grade_candidate(row, '{"feature_id":"wp1","operation":"Workplane"}')[
        "correct"
    ]


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


def test_default_baselines_include_paper_shortcut_baselines():
    result = run_baselines([])

    assert "primitive_symbolic_volume" in result
    assert "aabb_point_membership" in result


def test_aabb_point_membership_uses_bbox_rows():
    rows = [
        {
            "id": "bbox",
            "source_id": "src",
            "target_feature_id": "wp1",
            "task_type": "bbox_after_step",
            "answer": {"min": [-1, -1, -1], "max": [1, 1, 1]},
        },
        {
            "id": "inside",
            "source_id": "src",
            "target_feature_id": "wp1",
            "task_type": "point_membership",
            "labels": {"point_query": {"target_feature_id": "wp1", "point": [0, 0, 0]}},
        },
        {
            "id": "boundary",
            "source_id": "src",
            "target_feature_id": "wp1",
            "task_type": "point_membership",
            "labels": {"point_query": {"target_feature_id": "wp1", "point": [1, 0, 0]}},
        },
        {
            "id": "outside",
            "source_id": "src",
            "target_feature_id": "wp1",
            "task_type": "point_membership",
            "labels": {"point_query": {"target_feature_id": "wp1", "point": [2, 0, 0]}},
        },
    ]

    predictions = baseline_predictions(rows, name="aabb_point_membership")

    assert predictions["inside"] == "inside"
    assert predictions["boundary"] == "on_boundary"
    assert predictions["outside"] == "outside"


def test_primitive_symbolic_volume_estimates_hole_delta_from_bbox():
    prompt = """Given the CadQuery script below.

```python
import cadquery as cq

wp0 = cq.Workplane("XY")
wp1 = wp0.box(10, 10, 10)
wp2 = wp1.faces(">Z").workplane()
wp3 = wp2.hole(2)
result = wp3
```"""
    rows = [
        {
            "id": "bbox",
            "source_id": "src",
            "target_feature_id": "wp3",
            "task_type": "bbox_after_step",
            "answer": {"min": [-5, -5, -5], "max": [5, 5, 5]},
            "prompt": prompt,
        },
        {
            "id": "delta",
            "source_id": "src",
            "target_feature_id": "wp3",
            "task_type": "signed_volume_delta",
            "answer": -31.41592653589793,
            "answer_type": "number",
            "numeric_tolerance": 1e-6,
            "parse_policy": "numeric_4_sigfig_v1",
            "prompt": prompt,
        },
    ]

    predictions = baseline_predictions(rows, name="primitive_symbolic_volume")

    assert grade_candidate(rows[1], predictions["delta"])["correct"]
