"""Validate the checked-in extraction-graph oracles against their schema."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ORACLE_DIR = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "dataset"
    / "implementation"
    / "pipeline"
    / "testing"
    / "oracles"
    / "extraction-graph"
)
SCHEMA_DIR = Path(__file__).resolve().parents[1] / "tools" / "manual-verification"
sys.path.insert(0, str(SCHEMA_DIR))

from extraction_oracle_schema import (
    CadGraphEntityKind,
    Oracle,
    OracleKind,
    OracleScope,
    VerificationStatus,
)

SHA256 = re.compile(r"^[0-9a-f]{64}$")


def load_oracles() -> list[tuple[Path, Oracle]]:
    paths = sorted(ORACLE_DIR.glob("*.json"))
    assert paths, f"no extraction-graph oracles under {ORACLE_DIR}"
    records: list[tuple[Path, Oracle]] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n"), f"{path.name}: oracle needs a trailing newline"
        records.append((path, Oracle.model_validate(json.loads(text))))
    return records


def test_oracles_are_discoverable() -> None:
    seen: set[str] = set()
    for path, oracle in load_oracles():
        assert path.stem == oracle.slug, (
            f"{path.name}: file stem does not match slug {oracle.slug!r}"
        )
        assert oracle.slug not in seen, f"{path.name}: duplicate slug {oracle.slug!r}"
        seen.add(oracle.slug)


def test_oracle_model() -> None:
    for path, oracle in load_oracles():
        assert oracle.oracle_kind == OracleKind.EXTRACTION_GRAPH, (
            f"{path.name}: oracle_kind must be extraction-graph"
        )
        assert oracle.scope == OracleScope.FINAL_STATE, (
            f"{path.name}: unsupported scope {oracle.scope!r}"
        )
        if oracle.verification.status == VerificationStatus.VERIFIED:
            assert oracle.verification.verified_by, (
                f"{path.name}: a verified oracle needs verified_by"
            )
            assert oracle.verification.verified_at, (
                f"{path.name}: a verified oracle needs verified_at"
            )

        covers = oracle.covers
        for name, values in (
            ("entity_kinds", covers.entity_kinds),
            ("relation_kinds", covers.relation_kinds),
            ("measurement_kinds", covers.measurement_kinds),
        ):
            assert values, f"{path.name}: covers.{name} must be non-empty"
            assert list(values) == sorted(set(values)), (
                f"{path.name}: covers.{name} must be sorted and unique"
            )

        expected = oracle.expected
        assert {entity.entity_kind for entity in expected.entities} <= set(
            covers.entity_kinds
        ), f"{path.name}: an entity kind is missing from covers.entity_kinds"
        assert {relation.relation_kind for relation in expected.relations} <= set(
            covers.relation_kinds
        ), f"{path.name}: a relation kind is missing from covers.relation_kinds"
        assert {
            measurement.measurement_kind for measurement in expected.measurements
        } <= set(covers.measurement_kinds), (
            f"{path.name}: a measurement kind is missing from covers.measurement_kinds"
        )


def test_oracle_program_identity() -> None:
    for path, oracle in load_oracles():
        text = oracle.program.text
        assert "\r" not in text, f"{path.name}: program text contains a carriage return"
        assert text.endswith("\n"), (
            f"{path.name}: program text needs one trailing newline"
        )
        assert not text.endswith("\n\n"), (
            f"{path.name}: program text has two trailing newlines"
        )

        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert SHA256.match(oracle.program.program_sha256), (
            f"{path.name}: program_sha256 is not a lower-case SHA-256"
        )
        assert oracle.program.program_sha256 == digest, (
            f"{path.name}: program_sha256 does not match the program text"
        )
        assert oracle.program.program_id == f"cadqaprog:{digest}", (
            f"{path.name}: program_id does not match program_sha256"
        )


def test_oracle_references_resolve() -> None:
    for path, oracle in load_oracles():
        expected = oracle.expected
        local_ids = [entity.local_id for entity in expected.entities]
        assert len(local_ids) == len(set(local_ids)), f"{path.name}: duplicate local_id"
        known = set(local_ids)

        for relation in expected.relations:
            assert relation.from_local_id in known, (
                f"{path.name}: relation subject {relation.from_local_id!r} is unknown"
            )
            assert relation.to_local_id in known, (
                f"{path.name}: relation object {relation.to_local_id!r} is unknown"
            )
        for measurement in expected.measurements:
            assert measurement.subject_local_id in known, (
                f"{path.name}: measurement subject {measurement.subject_local_id!r} "
                f"is unknown"
            )


def test_oracle_descriptors_are_unique() -> None:
    for path, oracle in load_oracles():
        keys = Counter(
            (entity.entity_kind, entity.descriptor.model_dump_json())
            for entity in oracle.expected.entities
        )
        collisions = [key for key, count in keys.items() if count > 1]
        assert not collisions, (
            f"{path.name}: descriptors resolve to several entities: {collisions}"
        )


def test_oracle_entity_kinds_are_closed() -> None:
    for path, oracle in load_oracles():
        for entity in oracle.expected.entities:
            assert isinstance(entity.entity_kind, CadGraphEntityKind), (
                f"{path.name}: entity {entity.local_id!r} has an unknown kind"
            )
