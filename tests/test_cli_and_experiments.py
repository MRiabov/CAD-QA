from pathlib import Path

from cad_qa.cli import main as cadqa_main
from scripts.experiments.run_experiment_suite import main as experiment_main


def test_cli_smoke_validate_and_baseline(tmp_path: Path):
    dataset_dir = tmp_path / "dataset"
    baseline_dir = tmp_path / "baselines"

    assert cadqa_main(["smoke", "--output-dir", str(dataset_dir)]) == 0
    assert cadqa_main(["validate", str(dataset_dir)]) == 0
    assert (
        cadqa_main(
            [
                "baseline",
                str(dataset_dir / "jsonl" / "train.jsonl"),
                "--output-dir",
                str(baseline_dir),
            ]
        )
        == 0
    )
    assert (baseline_dir / "baseline_metrics.json").exists()


def test_experiment_runner_dry_run(tmp_path: Path, capsys):
    manifest = tmp_path / "suite.yaml"
    manifest.write_text(
        """
version: 1
runs:
  - name: first
    kind: smoke
    command: [python, --version]
    output_dir: runs/first
  - name: second
    kind: smoke
    depends_on: [first]
    command: [python, --version]
    output_dir: runs/second
""",
        encoding="utf-8",
    )

    experiment_main(
        [str(manifest), "--run", "second", "--with-dependencies", "--dry-run"]
    )
    output = capsys.readouterr().out
    assert '"first"' in output
    assert '"second"' in output
