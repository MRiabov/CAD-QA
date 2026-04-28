"""Validate a CAD-QA dataset directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cad_qa.jsonio import write_json
from cad_qa.validation import validate_dataset_dir


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    report = validate_dataset_dir(args.dataset_dir)
    if args.output is not None:
        write_json(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
