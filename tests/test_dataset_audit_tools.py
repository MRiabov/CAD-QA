from pathlib import Path

from cad_qa.config import DatasetConfig
from cad_qa.export import export_smoke_dataset
from cad_qa.jsonio import read_jsonl, write_jsonl
from scripts.dataset.failure_report import build_failure_report
from scripts.dataset.manual_audit_sample import build_audit_sample
from scripts.dataset.reproducibility_audit import compare_dataset_exports


def test_manual_audit_sample_covers_task_buckets(tmp_path: Path):
    export_smoke_dataset(output_dir=tmp_path, config=DatasetConfig())

    sample, report = build_audit_sample(tmp_path, rows_per_bucket=1, max_rows=100)

    label_rows = [row for row in sample if row["audit_kind"] == "label"]
    assert report["label_sample_count"] == len(label_rows)
    assert {row["task_type"] for row in label_rows} >= {
        "operation_count",
        "bbox_after_step",
    }
    assert all("audit_fields" in row for row in sample)


def test_failure_report_summarizes_failure_manifest(tmp_path: Path):
    export_smoke_dataset(output_dir=tmp_path, config=DatasetConfig())
    source_id = read_jsonl(tmp_path / "jsonl" / "train.jsonl")[0]["source_id"]
    write_jsonl(
        tmp_path / "failure_manifest.jsonl",
        [
            {
                "source_id": source_id,
                "trace_id": "trace-1",
                "failure_reason": "trace timed out after 30 seconds",
                "execution_status": "timeout",
                "operation_graph_status": "ok",
            }
        ],
    )

    report = build_failure_report(tmp_path)

    assert report["status"] == "has_failures"
    assert report["failure_counts_by_category"] == {"timeout": 1}
    assert report["failures"][0]["public_rows_for_source"] > 0


def test_reproducibility_audit_passes_for_identical_exports(tmp_path: Path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    export_smoke_dataset(output_dir=left, config=DatasetConfig())
    export_smoke_dataset(output_dir=right, config=DatasetConfig())

    report = compare_dataset_exports(left, right)

    assert report["status"] == "pass"


def test_reproducibility_audit_fails_on_row_drift(tmp_path: Path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    export_smoke_dataset(output_dir=left, config=DatasetConfig())
    export_smoke_dataset(output_dir=right, config=DatasetConfig())
    train_path = right / "jsonl" / "train.jsonl"
    rows = read_jsonl(train_path)
    rows[0]["prompt"] = rows[0]["prompt"] + " drift"
    write_jsonl(train_path, rows)

    report = compare_dataset_exports(left, right)

    assert report["status"] == "fail"
    assert report["row_diff"]["content_mismatches"]
