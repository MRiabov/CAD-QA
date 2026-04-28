import tarfile
from pathlib import Path

from cad_qa.config import DatasetConfig
from cad_qa.source import load_source_archive


def test_loads_bounded_cadevolve_archive_subset(tmp_path: Path):
    archive_path = tmp_path / "cadevolve.tar"
    source_path = tmp_path / "source_cadquery.py"
    source_path.write_text("import cadquery as cq\nresult = cq.Workplane('XY')\n", encoding="utf-8")
    with tarfile.open(archive_path, "w") as archive:
        archive.add(source_path, arcname="./CADEvolve-C/demo/source_cadquery.py")
        archive.add(source_path, arcname="./CADEvolve-G/not_executable.py")

    records = load_source_archive(archive_path, config=DatasetConfig())

    assert len(records) == 1
    assert records[0].source == "cadevolve"
    assert records[0].normalized_archive_member_path == "CADEvolve-C/demo/source_cadquery.py"
    assert records[0].hashes["normalized_source_code_hash"].startswith("sha256:")
