from pathlib import Path

from cad_qa.jsonio import read_json, write_json
from scripts.experiments.check_stop_gates import evaluate_stop_gates
from scripts.experiments.package_run_artifacts import package_artifacts
from scripts.experiments.upload_artifact_package import upload_artifact_package


def test_stop_gates_pass_and_fail(tmp_path: Path):
    stats = tmp_path / "dataset_stats.json"
    failure_report = tmp_path / "failure_report.json"
    sft = tmp_path / "sft_smoke.json"
    comparison = tmp_path / "comparison.json"
    write_json(stats, {"status": "pass", "row_count": 10})
    write_json(failure_report, {"trace_count": 10, "failure_count": 1})
    write_json(sft, {"status": "pass"})
    write_json(comparison, {"status": "pass"})

    passing = evaluate_stop_gates(
        dataset_stats_path=stats,
        failure_report_path=failure_report,
        sft_smoke_report_path=sft,
        experiment_comparison_path=comparison,
        min_rows=5,
        max_trace_failure_rate=0.2,
    )
    failing = evaluate_stop_gates(
        dataset_stats_path=stats,
        failure_report_path=failure_report,
        min_rows=20,
        max_trace_failure_rate=0.05,
    )

    assert passing["status"] == "pass"
    assert failing["status"] == "fail"


def test_package_run_artifacts_writes_manifest_and_archive(tmp_path: Path):
    run_dir = tmp_path / "run"
    output_dir = tmp_path / "package"
    write_json(run_dir / "metrics.json", {"accuracy": 1.0})
    (run_dir / "logs").mkdir()
    (run_dir / "logs" / "stdout.log").write_text("ok\n", encoding="utf-8")

    report = package_artifacts(
        [run_dir], output_dir=output_dir, archive_name="bundle.tar.gz"
    )

    manifest = read_json(output_dir / "artifact_manifest.json")
    assert report["file_count"] == 2
    assert manifest["archive"]["sha256"].startswith("sha256:")
    assert (output_dir / "bundle.tar.gz").exists()


def test_upload_artifact_package_stages_and_verifies_files(tmp_path: Path):
    run_dir = tmp_path / "run"
    package_dir = tmp_path / "package"
    destination_dir = tmp_path / "upload"
    write_json(run_dir / "metrics.json", {"accuracy": 1.0})
    package_artifacts([run_dir], output_dir=package_dir, archive_name="bundle.tar.gz")

    report = upload_artifact_package(package_dir, destination_dir=destination_dir)

    assert report["status"] == "pass"
    assert report["file_count"] == 2
    assert (destination_dir / "artifact_manifest.json").exists()
    assert (destination_dir / "bundle.tar.gz").exists()
    assert read_json(destination_dir / "upload_manifest.json")["status"] == "pass"
