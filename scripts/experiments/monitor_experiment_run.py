"""Print status for CAD-QA experiment run directories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs_dir", type=Path, nargs="?", default=Path("runs"))
    args = parser.parse_args(argv)
    statuses = []
    for path in sorted(args.runs_dir.glob("*/run_status.json")):
        statuses.append(json.loads(path.read_text(encoding="utf-8")))
    print(json.dumps({"runs": statuses}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
