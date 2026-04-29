"""Stage packaged experiment artifacts to a destination directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
from typing import Any

from cad_qa.hashing import sha256_bytes
from cad_qa.jsonio import read_json, write_json


DEFAULT_PATTERNS = ("artifact_manifest.json", "*.tar.gz")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_dir", type=Path)
    parser.add_argument("--destination-dir", type=Path, required=True)
    parser.add_argument("--pattern", action="append", default=[])
    args = parser.parse_args(argv)

    report = upload_artifact_package(
        args.package_dir,
        destination_dir=args.destination_dir,
        patterns=[*DEFAULT_PATTERNS, *args.pattern],
    )
    print(json.dumps(report, indent=2, sort_keys=True))


def upload_artifact_package(
    package_dir: Path, *, destination_dir: Path, patterns: list[str] | None = None
) -> dict[str, Any]:
    """Copy package files to a destination and verify their checksums."""

    patterns = patterns or list(DEFAULT_PATTERNS)
    if not package_dir.is_dir():
        raise ValueError(f"package_dir is not a directory: {package_dir}")
    destination_dir.mkdir(parents=True, exist_ok=True)
    files = _selected_files(package_dir, patterns)
    copied = []
    for source in files:
        relative = source.relative_to(package_dir)
        destination = destination_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        source_hash = sha256_bytes(source.read_bytes())
        destination_hash = sha256_bytes(destination.read_bytes())
        copied.append(
            {
                "path": str(relative),
                "source": str(source),
                "destination": str(destination),
                "bytes": destination.stat().st_size,
                "sha256": destination_hash,
                "verified": source_hash == destination_hash,
            }
        )
    source_manifest = package_dir / "artifact_manifest.json"
    report = {
        "schema": "cadqa_artifact_upload_manifest_v1",
        "status": "pass"
        if copied and all(item["verified"] for item in copied)
        else "fail",
        "package_dir": str(package_dir),
        "destination_dir": str(destination_dir),
        "file_count": len(copied),
        "files": copied,
        "source_artifact_manifest_hash": _manifest_hash(source_manifest),
    }
    write_json(destination_dir / "upload_manifest.json", report)
    return report


def _selected_files(package_dir: Path, patterns: list[str]) -> list[Path]:
    files: set[Path] = set()
    for pattern in patterns:
        files.update(path for path in package_dir.glob(pattern) if path.is_file())
    return sorted(files, key=lambda path: str(path))


def _manifest_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    value = read_json(path)
    manifest_hash = value.get("manifest_hash") if isinstance(value, dict) else None
    return str(manifest_hash) if manifest_hash else sha256_bytes(path.read_bytes())


if __name__ == "__main__":
    main()
