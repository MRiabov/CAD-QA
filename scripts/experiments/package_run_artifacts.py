"""Create a checksum manifest and optional tarball for run artifacts."""

from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path
import tarfile
from typing import Any

from cad_qa.hashing import sha256_bytes, sha256_json
from cad_qa.jsonio import write_json


DEFAULT_EXCLUDES = ("*.pyc", "__pycache__/*", ".DS_Store")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--archive-name", default="cadqa_artifacts.tar.gz")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--no-archive", action="store_true")
    args = parser.parse_args(argv)

    report = package_artifacts(
        args.inputs,
        output_dir=args.output_dir,
        archive_name=args.archive_name,
        excludes=[*DEFAULT_EXCLUDES, *args.exclude],
        write_archive=not args.no_archive,
    )
    print(report)


def package_artifacts(
    inputs: list[Path],
    *,
    output_dir: Path,
    archive_name: str = "cadqa_artifacts.tar.gz",
    excludes: list[str] | None = None,
    write_archive: bool = True,
) -> dict[str, Any]:
    excludes = excludes or list(DEFAULT_EXCLUDES)
    output_dir.mkdir(parents=True, exist_ok=True)
    files = _collect_files(inputs, excludes=excludes)
    entries = [_manifest_entry(path, inputs) for path in files]
    report = {
        "schema": "cadqa_artifact_retention_manifest_v1",
        "status": "pass",
        "input_paths": [str(path) for path in inputs],
        "file_count": len(entries),
        "total_bytes": sum(int(entry["bytes"]) for entry in entries),
        "files": entries,
        "manifest_hash": sha256_json(entries),
        "archive": None,
    }
    manifest_path = output_dir / "artifact_manifest.json"
    write_json(manifest_path, report)
    if write_archive:
        archive_path = output_dir / archive_name
        _write_archive(archive_path, files, inputs, manifest_path)
        report["archive"] = {
            "path": str(archive_path),
            "bytes": archive_path.stat().st_size,
            "sha256": sha256_bytes(archive_path.read_bytes()),
        }
        write_json(manifest_path, report)
    return report


def _collect_files(inputs: list[Path], *, excludes: list[str]) -> list[Path]:
    files: list[Path] = []
    for input_path in inputs:
        if input_path.is_file():
            candidates = [input_path]
        else:
            candidates = [path for path in input_path.rglob("*") if path.is_file()]
        for path in candidates:
            rel = _display_path(path, inputs)
            if not any(
                fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(path.name, pattern)
                for pattern in excludes
            ):
                files.append(path)
    return sorted(set(files), key=lambda path: str(path))


def _manifest_entry(path: Path, inputs: list[Path]) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "path": _display_path(path, inputs),
        "bytes": len(payload),
        "sha256": sha256_bytes(payload),
    }


def _write_archive(
    archive_path: Path, files: list[Path], inputs: list[Path], manifest_path: Path
) -> None:
    with tarfile.open(archive_path, "w:gz") as archive:
        for path in files:
            archive.add(path, arcname=_display_path(path, inputs))
        archive.add(manifest_path, arcname="artifact_manifest.json")


def _display_path(path: Path, inputs: list[Path]) -> str:
    resolved = path.resolve()
    for root in inputs:
        root_resolved = root.resolve()
        if root.is_file() and resolved == root_resolved:
            return root.name
        if root.is_dir():
            try:
                return str(Path(root.name) / resolved.relative_to(root_resolved))
            except ValueError:
                continue
    return str(path)


if __name__ == "__main__":
    main()
