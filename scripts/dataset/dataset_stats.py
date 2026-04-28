"""Write dataset statistics and validation report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cad_qa.jsonio import read_json, write_json
from cad_qa.validation import validate_dataset_dir


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    report = validate_dataset_dir(args.dataset_dir)
    metadata_path = args.dataset_dir / "metadata.json"
    if metadata_path.exists():
        report["metadata"] = read_json(metadata_path)
    output = args.output or args.dataset_dir / "dataset_stats.json"
    write_json(output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
