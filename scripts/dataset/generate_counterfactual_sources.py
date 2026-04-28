"""Generate grouped numeric-parameter counterfactual CadQuery source variants."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

from cad_qa.counterfactuals import numeric_parameter_variants
from cad_qa.jsonio import write_json
from cad_qa.source import discover_cadevolve_sources, normalize_archive_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--max-variants-per-source", type=int, default=4)
    parser.add_argument("--relative-delta", type=float, default=0.1)
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    source_files = discover_cadevolve_sources(args.source_dir)[: args.limit]
    manifest_rows = []
    for relative_path in source_files:
        code = (args.source_dir / relative_path).read_text(encoding="utf-8", errors="replace")
        variants = numeric_parameter_variants(
            code,
            relative_delta=args.relative_delta,
            max_variants=args.max_variants_per_source,
        )
        for variant in variants:
            output_path = args.output_dir / "sources" / variant.variant_id / normalize_archive_path(relative_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(variant.variant_code, encoding="utf-8")
            manifest_rows.append(
                {
                    **asdict(variant),
                    "original_relative_path": normalize_archive_path(relative_path),
                    "variant_relative_path": str(output_path.relative_to(args.output_dir)).replace("\\", "/"),
                }
            )
    manifest = {
        "schema": "cadqa_counterfactual_source_manifest_v1",
        "source_dir": str(args.source_dir),
        "relative_delta": args.relative_delta,
        "source_count": len(source_files),
        "variant_count": len(manifest_rows),
        "variants": manifest_rows,
    }
    write_json(args.output_dir / "counterfactual_manifest.json", manifest)
    print(manifest)


if __name__ == "__main__":
    main()
