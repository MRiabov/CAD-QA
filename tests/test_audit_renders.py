from pathlib import Path

from cad_qa.config import DatasetConfig
from cad_qa.export import export_smoke_dataset
from cad_qa.jsonio import read_json
from scripts.dataset.export_audit_renders import export_audit_renders


def test_audit_render_dry_run_manifest(tmp_path: Path):
    dataset_dir = tmp_path / "dataset"
    output_dir = tmp_path / "renders"
    export_smoke_dataset(output_dir=dataset_dir, config=DatasetConfig())

    report = export_audit_renders(
        dataset_dir,
        output_dir=output_dir,
        limit=1,
        views=["front", "top"],
        dry_run=True,
    )

    manifest = read_json(output_dir / "audit_render_manifest.json")
    assert report["dry_run"] is True
    assert manifest["render_count"] == 2
    assert {item["view"] for item in manifest["items"]} == {"front", "top"}
    assert manifest["items"][0]["status"] == "planned"
