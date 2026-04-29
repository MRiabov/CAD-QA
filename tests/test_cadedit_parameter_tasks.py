from pathlib import Path

from cad_qa.counterfactuals import numeric_parameter_variants
from cad_qa.jsonio import read_json, read_jsonl, write_json
from cad_qa.validation import validate_record_file
from scripts.dataset.materialize_cadedit_parameter_tasks import main as cadedit_main


def test_materialize_cadedit_parameter_edit_direction_rows(tmp_path: Path):
    code = "import cadquery as cq\nresult = cq.Workplane('XY').box(10, 20, 3)\n"
    variants = numeric_parameter_variants(code, relative_delta=0.1, max_variants=1)
    manifest = {
        "schema": "cadqa_counterfactual_source_manifest_v1",
        "variants": [
            {
                **variant.__dict__,
                "original_relative_path": "example.py",
                "variant_relative_path": f"sources/{variant.variant_id}/example.py",
            }
            for variant in variants
        ],
    }
    manifest_path = tmp_path / "counterfactual_manifest.json"
    output_dir = tmp_path / "cadedit"
    write_json(manifest_path, manifest)

    cadedit_main([str(manifest_path), "--output-dir", str(output_dir)])

    rows = []
    for path in sorted((output_dir / "jsonl").glob("*.jsonl")):
        assert validate_record_file(path, "row")["status"] == "pass"
        rows.extend(read_jsonl(path))
    metadata = read_json(output_dir / "metadata.json")
    assert metadata["row_count"] == 6
    assert {
        row["answer"] for row in rows if row["task_type"] == "parameter_edit_direction"
    } == {"increase", "decrease"}
    assert {row["task_type"] for row in rows} == {
        "parameter_edit_direction",
        "counterfactual_parameter",
        "multi_step_edit_plan",
    }
    assert all(
        "steps" in row["answer"]
        for row in rows
        if row["task_type"] == "multi_step_edit_plan"
    )
