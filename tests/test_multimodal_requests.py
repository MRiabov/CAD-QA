from pathlib import Path

from cad_qa.config import DatasetConfig
from cad_qa.export import export_smoke_dataset
from cad_qa.jsonio import read_json, read_jsonl
from scripts.dataset.export_audit_renders import export_audit_renders
from scripts.evaluation.export_multimodal_prediction_requests import (
    main as multimodal_main,
)


def test_export_multimodal_prediction_requests(tmp_path: Path):
    dataset_dir = tmp_path / "dataset"
    render_dir = tmp_path / "renders"
    output = tmp_path / "requests.jsonl"
    export_smoke_dataset(output_dir=dataset_dir, config=DatasetConfig())
    export_audit_renders(dataset_dir, output_dir=render_dir, limit=2, dry_run=True)

    multimodal_main(
        [
            str(dataset_dir / "jsonl" / "validation.jsonl"),
            "--render-manifest",
            str(render_dir / "audit_render_manifest.json"),
            "--output",
            str(output),
        ]
    )

    requests = read_jsonl(output)
    report = read_json(output.with_suffix(".report.json"))
    assert requests
    assert report["request_count"] == len(requests)
    assert all(request["media"][0]["type"] == "image/svg+xml" for request in requests)
