"""Export the worker JSON Schema files from the Pydantic contract classes.

Run from the repository root::

    uv run python tools/contracts/export_worker_schemas.py
    uv run python tools/contracts/export_worker_schemas.py --check

``--check`` is the CI and pre-commit form: it exits non-zero when a checked-in
schema differs from the contract, so a contract change that was not exported
fails instead of drifting silently.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from cadqa_dataset_generator.contracts import SCHEMA_MODELS

REPO = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = REPO / "contracts" / "worker" / "v1"
SCHEMA_URI_ROOT = "https://github.com/MRiabov/CAD-QA/contracts/worker/v1"


def render_schema(stem: str, contract_model: type) -> str:
    """Return the canonical JSON text for one contract schema."""

    schema: dict[str, Any] = contract_model.model_json_schema(mode="validation")
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{SCHEMA_URI_ROOT}/{stem}.schema.json",
        **schema,
    }
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def schema_paths() -> dict[str, Path]:
    """Return the output path for each exported schema stem."""

    return {stem: SCHEMA_ROOT / f"{stem}.schema.json" for stem in sorted(SCHEMA_MODELS)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when a checked-in schema differs from the model",
    )
    args = parser.parse_args(argv)

    failures: list[str] = []
    for stem, path in schema_paths().items():
        rendered = render_schema(stem, SCHEMA_MODELS[stem])
        if args.check:
            if not path.exists():
                failures.append(f"missing {path.relative_to(REPO)}")
                continue
            if path.read_text(encoding="utf-8") != rendered:
                failures.append(f"stale {path.relative_to(REPO)}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        print(f"wrote {path.relative_to(REPO)}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        print(
            "run `uv run python tools/contracts/export_worker_schemas.py` "
            "and commit the result",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
