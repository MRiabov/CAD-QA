"""Build a proposed extraction-graph oracle from a CadQuery program.

This is a manual-verification devtool, not pipeline code. It executes the
program with plain CadQuery and OCP, derives the final-state graph that `02c`
must build, and writes a ``proposed`` oracle record for a human to verify.

Usage:
    uv run python tools/manual-verification/build_extraction_oracle.py \
      --program path/to/program.py \
      --slug rotated-box \
      --out docs/dataset/implementation/pipeline/testing/oracles/extraction-graph/rotated-box.json
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import json
import math
from collections import defaultdict
from itertools import pairwise
from pathlib import Path
from typing import Any

import cadquery as cq
from cadquery_method_specs import METHOD_SPECS
from extraction_oracle_schema import (
    AttributeName,
    BoundingBox,
    CadGraphEntity,
    CadGraphEntityKind,
    Covers,
    Descriptor,
    Environment,
    Exclusion,
    Expected,
    FeatureKind,
    FilterName,
    Measurement,
    MeasurementKind,
    MethodSpec,
    Oracle,
    OracleKind,
    OracleScope,
    Point3D,
    Program,
    Relation,
    RelationKind,
    Verification,
    VerificationStatus,
)
from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = 1


class Assignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: int = Field(ge=0)
    target: str = Field(min_length=1)
    method: str = Field(min_length=1)
    spec: MethodSpec


def canonical_decimal(value: float) -> str:
    """Round to 9 places, half-to-even, and emit the canonical decimal string."""

    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"non-finite value: {value!r}")
    rounded = round(value, 9)
    if rounded == 0:
        return "0"
    text = f"{rounded:.9f}".rstrip("0").rstrip(".")
    return text


def centroid_filters(values: Any) -> dict[FilterName, str]:
    return {
        FilterName.CENTROID_X: canonical_decimal(float(values[0])),
        FilterName.CENTROID_Y: canonical_decimal(float(values[1])),
        FilterName.CENTROID_Z: canonical_decimal(float(values[2])),
    }


def point3d(values: Any) -> Point3D:
    return Point3D(
        x=canonical_decimal(float(values[0])),
        y=canonical_decimal(float(values[1])),
        z=canonical_decimal(float(values[2])),
    )


def point_json(values: Any) -> str:
    return point3d(values).model_dump_json()


def bbox_json(shape: Any) -> str:
    box = shape.BoundingBox()
    return BoundingBox(
        min=Point3D(
            x=canonical_decimal(box.xmin),
            y=canonical_decimal(box.ymin),
            z=canonical_decimal(box.zmin),
        ),
        max=Point3D(
            x=canonical_decimal(box.xmax),
            y=canonical_decimal(box.ymax),
            z=canonical_decimal(box.zmax),
        ),
    ).model_dump_json()


def method_name(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    raise ValueError(f"unsupported callee: {ast.dump(func)}")


def read_assignments(text: str) -> list[Assignment]:
    module = ast.parse(text)
    assignments: list[Assignment] = []
    order = 0
    for stmt in module.body:
        if not isinstance(stmt, ast.Assign):
            continue
        if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
            raise ValueError(f"assignment {order} is not a single Name target")
        if not isinstance(stmt.value, ast.Call):
            raise TypeError(f"assignment {order} is not a call")
        name = method_name(stmt.value)
        if name not in METHOD_SPECS:
            raise ValueError(f"assignment {order} uses an unsupported method: {name}")
        assignments.append(
            Assignment(
                order=order,
                target=stmt.targets[0].id,
                method=name,
                spec=METHOD_SPECS[name],
            )
        )
        order += 1
    return assignments


def execute(text: str) -> dict[str, Any]:
    namespace: dict[str, Any] = {}
    exec(compile(text, "<oracle>", "exec"), namespace)  # noqa: S102 - trusted fixture
    return namespace


def state_shape(namespace: dict[str, Any], assignment: Assignment) -> cq.Shape | None:
    if not assignment.spec.state_producing:
        return None
    value = namespace[assignment.target]
    if not isinstance(value, cq.Workplane):
        raise TypeError(f"{assignment.target} is not a Workplane")
    shape = value.val()
    if shape is None or len(shape.Solids()) < 1:
        raise ValueError(f"{assignment.target} did not produce a solid")
    return shape


def edge_key(edge: cq.Edge) -> tuple[str, ...]:
    # A face may return the same edge with the opposite orientation, so sort
    # the endpoints before building the key.
    start = edge.startPoint()
    end = edge.endPoint()
    center = edge.Center()
    first, second = sorted(
        [
            (
                canonical_decimal(start.x),
                canonical_decimal(start.y),
                canonical_decimal(start.z),
            ),
            (
                canonical_decimal(end.x),
                canonical_decimal(end.y),
                canonical_decimal(end.z),
            ),
        ]
    )
    return (
        *first,
        *second,
        canonical_decimal(center.x),
        canonical_decimal(center.y),
        canonical_decimal(center.z),
        canonical_decimal(edge.Length()),
    )


def build_oracle(slug: str, text: str) -> Oracle:
    text = text if text.endswith("\n") else text + "\n"
    program_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assignments = read_assignments(text)
    namespace = execute(text)

    states: list[tuple[Assignment, cq.Shape]] = []
    for assignment in assignments:
        shape = state_shape(namespace, assignment)
        if shape is not None:
            states.append((assignment, shape))
    if not states:
        raise ValueError("program produced no solid state")
    final_assignment, final_shape = states[-1]

    entities: list[CadGraphEntity] = []
    relations: list[Relation] = []
    measurements: list[Measurement] = []

    entities.append(
        CadGraphEntity(
            local_id="program",
            entity_kind=CadGraphEntityKind.CADQUERY_PROGRAM,
            descriptor=Descriptor(
                category=CadGraphEntityKind.CADQUERY_PROGRAM,
                filters={"program_sha256": program_sha256},
            ),
            attributes={AttributeName.NORMALIZATION_VERSION: "1"},
        )
    )

    operation_local: dict[int, str] = {}
    for assignment in assignments:
        local_id = f"operation:{assignment.order:03d}"
        operation_local[assignment.order] = local_id
        entities.append(
            CadGraphEntity(
                local_id=local_id,
                entity_kind=CadGraphEntityKind.OPERATION,
                descriptor=Descriptor(
                    category=CadGraphEntityKind.OPERATION,
                    filters={
                        FilterName.ORDER: str(assignment.order),
                        FilterName.METHOD: assignment.method,
                    },
                ),
                attributes={
                    AttributeName.OPERATION_KIND: assignment.spec.operation_kind.value,
                    AttributeName.RESULT_VAR: assignment.target,
                },
            )
        )

    feature_local: dict[int, str] = {}
    region_local: dict[int, str] = {}
    for assignment in assignments:
        if not assignment.spec.state_producing:
            continue
        feature_kind = assignment.spec.feature_kind
        if feature_kind is None:
            raise ValueError(f"state-producing {assignment.method} has no feature kind")
        local_id = f"feature:{assignment.order:03d}"
        feature_local[assignment.order] = local_id
        entities.append(
            CadGraphEntity(
                local_id=local_id,
                entity_kind=CadGraphEntityKind.FEATURE,
                descriptor=Descriptor(
                    category=CadGraphEntityKind.FEATURE,
                    filters={
                        FilterName.OPERATION_ORDER: str(assignment.order),
                        FilterName.FEATURE_KIND: feature_kind.value,
                    },
                ),
                attributes={
                    AttributeName.FEATURE_KIND: feature_kind.value,
                },
            )
        )
        if feature_kind in (
            FeatureKind.ADD_MATERIAL,
            FeatureKind.REMOVE_MATERIAL,
            FeatureKind.CONSTRUCTION,
        ):
            sign = "removed" if feature_kind == FeatureKind.REMOVE_MATERIAL else "added"
            region_id = f"region:{assignment.order:03d}:{sign}"
            region_local[assignment.order] = region_id
            entities.append(
                CadGraphEntity(
                    local_id=region_id,
                    entity_kind=CadGraphEntityKind.REGION,
                    descriptor=Descriptor(
                        category=CadGraphEntityKind.REGION,
                        filters={
                            FilterName.FEATURE_OPERATION_ORDER: str(assignment.order),
                            FilterName.REGION_SIGN: sign,
                        },
                    ),
                    attributes={AttributeName.REGION_SIGN: sign},
                )
            )

    state_id = f"state:{final_assignment.order:03d}"
    entities.append(
        CadGraphEntity(
            local_id=state_id,
            entity_kind=CadGraphEntityKind.SOLID_STATE,
            descriptor=Descriptor(
                category=CadGraphEntityKind.SOLID_STATE,
                filters={
                    FilterName.OPERATION_ORDER: str(final_assignment.order),
                    FilterName.IS_FINAL: "true",
                },
            ),
            attributes={AttributeName.IS_FINAL: "true"},
        )
    )

    for previous, current in pairwise(assignments):
        relations.append(
            Relation(
                relation_kind=RelationKind.BEFORE,
                from_local_id=operation_local[previous.order],
                to_local_id=operation_local[current.order],
                evidence_rule="operation_order",
            )
        )
        relations.append(
            Relation(
                relation_kind=RelationKind.AFTER,
                from_local_id=operation_local[current.order],
                to_local_id=operation_local[previous.order],
                evidence_rule="operation_order",
            )
        )

    for assignment in assignments:
        if assignment.order in feature_local:
            relations.append(
                Relation(
                    relation_kind=RelationKind.CREATES,
                    from_local_id=operation_local[assignment.order],
                    to_local_id=feature_local[assignment.order],
                    evidence_rule="solid_state_producing_operation",
                )
            )
        if assignment.order == final_assignment.order:
            relations.append(
                Relation(
                    relation_kind=RelationKind.CREATES,
                    from_local_id=operation_local[assignment.order],
                    to_local_id=state_id,
                    evidence_rule="captured_state",
                )
            )
        if assignment.order in region_local:
            relation_kind = (
                "removes_material"
                if "removed" in region_local[assignment.order]
                else "adds_material"
            )
            relations.append(
                Relation(
                    relation_kind=relation_kind,
                    from_local_id=feature_local[assignment.order],
                    to_local_id=region_local[assignment.order],
                    evidence_rule="feature_kind",
                )
            )
            relations.append(
                Relation(
                    relation_kind=RelationKind.PART_OF,
                    from_local_id=region_local[assignment.order],
                    to_local_id=feature_local[assignment.order],
                    evidence_rule="region_derivation",
                )
            )

    face_local: list[str] = []
    edge_local: list[str] = []
    vertex_local: list[str] = []

    for index, face in enumerate(final_shape.Faces()):
        local_id = f"face:{index:03d}"
        face_local.append(local_id)
        entities.append(
            CadGraphEntity(
                local_id=local_id,
                entity_kind=CadGraphEntityKind.FACE,
                descriptor=Descriptor(
                    category=CadGraphEntityKind.FACE,
                    filters={
                        FilterName.GEOMETRY_SURFACE_KIND: face.geomType().lower(),
                        FilterName.AREA: canonical_decimal(face.Area()),
                        **centroid_filters(face.Center().toTuple()),
                    },
                ),
                attributes={AttributeName.FACE_SURFACE_KIND: face.geomType().lower()},
            )
        )
        relations.append(
            Relation(
                relation_kind=RelationKind.HAS_FACE,
                from_local_id=state_id,
                to_local_id=local_id,
                evidence_rule="state_entity_table",
            )
        )
        measurements.extend(
            [
                Measurement(
                    measurement_kind=MeasurementKind.AREA,
                    subject_local_id=local_id,
                    value=canonical_decimal(face.Area()),
                    unit="square_millimetre",
                ),
                Measurement(
                    measurement_kind=MeasurementKind.BOUNDING_BOX,
                    subject_local_id=local_id,
                    value=bbox_json(face),
                    unit="millimetre",
                ),
                Measurement(
                    measurement_kind=MeasurementKind.CENTROID,
                    subject_local_id=local_id,
                    value=point_json(face.Center().toTuple()),
                    unit="millimetre",
                ),
            ]
        )

    for index, edge in enumerate(final_shape.Edges()):
        local_id = f"edge:{index:03d}"
        edge_local.append(local_id)
        entities.append(
            CadGraphEntity(
                local_id=local_id,
                entity_kind=CadGraphEntityKind.EDGE,
                descriptor=Descriptor(
                    category=CadGraphEntityKind.EDGE,
                    filters={
                        FilterName.CURVE_KIND: edge.geomType().lower(),
                        FilterName.LENGTH: canonical_decimal(edge.Length()),
                        **centroid_filters(edge.Center().toTuple()),
                    },
                ),
                attributes={AttributeName.EDGE_CURVE_KIND: edge.geomType().lower()},
            )
        )
        measurements.extend(
            [
                Measurement(
                    measurement_kind=MeasurementKind.LENGTH,
                    subject_local_id=local_id,
                    value=canonical_decimal(edge.Length()),
                    unit="millimetre",
                ),
                Measurement(
                    measurement_kind=MeasurementKind.BOUNDING_BOX,
                    subject_local_id=local_id,
                    value=bbox_json(edge),
                    unit="millimetre",
                ),
                Measurement(
                    measurement_kind=MeasurementKind.CENTROID,
                    subject_local_id=local_id,
                    value=point_json(edge.Center().toTuple()),
                    unit="millimetre",
                ),
            ]
        )

    for index, vertex in enumerate(final_shape.Vertices()):
        local_id = f"vertex:{index:03d}"
        vertex_local.append(local_id)
        entities.append(
            CadGraphEntity(
                local_id=local_id,
                entity_kind=CadGraphEntityKind.VERTEX,
                descriptor=Descriptor(
                    category=CadGraphEntityKind.VERTEX,
                    filters=centroid_filters(vertex.toTuple()),
                ),
                attributes={},
            )
        )
        measurements.append(
            Measurement(
                measurement_kind=MeasurementKind.CENTROID,
                subject_local_id=local_id,
                value=point_json(vertex.toTuple()),
                unit="millimetre",
            )
        )

    # Face -> edge incidence from the kernel.
    face_by_edge: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for face_index, face in enumerate(final_shape.Faces()):
        for edge in face.Edges():
            key = edge_key(edge)
            face_by_edge[key].append(face_local[face_index])
            relations.append(
                Relation(
                    relation_kind=RelationKind.HAS_EDGE,
                    from_local_id=face_local[face_index],
                    to_local_id=edge_local[_edge_index(edge, final_shape)],
                    evidence_rule="face_has_edge",
                )
            )

    # Face adjacency from a shared edge.
    seen_pairs: set[tuple[str, str]] = set()
    for faces in face_by_edge.values():
        unique = sorted(set(faces))
        for left_index, left in enumerate(unique):
            for right in unique[left_index + 1 :]:
                pair = (left, right)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                relations.append(
                    Relation(
                        relation_kind=RelationKind.ADJACENT_TO,
                        from_local_id=left,
                        to_local_id=right,
                        evidence_rule="face_adjacent_to_face",
                    )
                )

    # Edge -> vertex incidence and endpoints.
    for index, edge in enumerate(final_shape.Edges()):
        local_id = edge_local[index]
        for vertex in edge.Vertices():
            relations.append(
                Relation(
                    relation_kind=RelationKind.HAS_VERTEX,
                    from_local_id=local_id,
                    to_local_id=vertex_local[_vertex_index(vertex, final_shape)],
                    evidence_rule="edge_has_vertex",
                )
            )
        for end, position in (("start", edge.startPoint()), ("end", edge.endPoint())):
            endpoint_id = f"endpoint:{index:03d}:{end}"
            entities.append(
                CadGraphEntity(
                    local_id=endpoint_id,
                    entity_kind=CadGraphEntityKind.EDGE_ENDPOINT,
                    descriptor=Descriptor(
                        category=CadGraphEntityKind.EDGE_ENDPOINT,
                        filters={
                            FilterName.EDGE_LOCAL_ID: local_id,
                            FilterName.END: end,
                        },
                    ),
                    attributes={AttributeName.END: end},
                )
            )
            relations.append(
                Relation(
                    relation_kind=RelationKind.ENDPOINT_OF,
                    from_local_id=endpoint_id,
                    to_local_id=local_id,
                    evidence_rule="edge_endpoint",
                )
            )

    measurements.extend(
        [
            Measurement(
                measurement_kind=MeasurementKind.VOLUME,
                subject_local_id=state_id,
                value=canonical_decimal(final_shape.Volume()),
                unit="cubic_millimetre",
            ),
            Measurement(
                measurement_kind=MeasurementKind.BOUNDING_BOX,
                subject_local_id=state_id,
                value=bbox_json(final_shape),
                unit="millimetre",
            ),
            Measurement(
                measurement_kind=MeasurementKind.CENTROID,
                subject_local_id=state_id,
                value=point_json(final_shape.Center().toTuple()),
                unit="millimetre",
            ),
            Measurement(
                measurement_kind=MeasurementKind.FACE_COUNT,
                subject_local_id=state_id,
                value=str(len(face_local)),
                unit="unitless",
            ),
            Measurement(
                measurement_kind=MeasurementKind.EDGE_COUNT,
                subject_local_id=state_id,
                value=str(len(edge_local)),
                unit="unitless",
            ),
            Measurement(
                measurement_kind=MeasurementKind.VERTEX_COUNT,
                subject_local_id=state_id,
                value=str(len(vertex_local)),
                unit="unitless",
            ),
            Measurement(
                measurement_kind=MeasurementKind.VALIDITY,
                subject_local_id=state_id,
                value="true" if final_shape.isValid() else "false",
                unit="unitless",
            ),
        ]
    )

    covers = Covers(
        entity_kinds=sorted({entity.entity_kind for entity in entities}),
        relation_kinds=sorted({relation.relation_kind for relation in relations}),
        measurement_kinds=sorted(
            {measurement.measurement_kind for measurement in measurements}
        ),
    )

    return Oracle(
        schema_version=SCHEMA_VERSION,
        oracle_kind=OracleKind.EXTRACTION_GRAPH,
        slug=slug,
        scope=OracleScope.FINAL_STATE,
        verification=Verification(
            status=VerificationStatus.PROPOSED,
            verified_by=None,
            verified_at=None,
            rationale=(
                "Machine-derived from plain CadQuery and OCP. A human must review the "
                "entities and incidence against the program text before this record gates a release."
            ),
        ),
        program=Program(
            program_id=f"cadqaprog:{program_sha256}",
            program_sha256=program_sha256,
            text=text,
        ),
        environment=Environment(
            cadquery_version=importlib.metadata.version("cadquery"),
            ocp_version=importlib.metadata.version("cadquery-ocp"),
            tolerance_policy_version="1",
            tolerance_policy_sha256=None,
        ),
        expected=Expected(
            entities=entities,
            relations=relations,
            measurements=measurements,
            capabilities=[],
        ),
        covers=covers,
        excluded=[
            Exclusion(
                exclusion_kind="state",
                local_id=None,
                reason="intermediate states are outside schema_version 1 final-state scope",
            ),
            Exclusion(
                exclusion_kind="node",
                local_id=None,
                reason="profiles, paths, workplanes and selector results are outside schema_version 1 incidence scope",
            ),
            Exclusion(
                exclusion_kind="relation",
                local_id=None,
                reason="uses, derived_from, selected_from and selected_by need 02a and 02b records; added when those stages land",
            ),
            Exclusion(
                exclusion_kind="measurement",
                local_id=None,
                reason="effect measurements need 02b effect capture; added when that stage lands",
            ),
            Exclusion(
                exclusion_kind="node",
                local_id=None,
                reason="point probes are outside schema_version 1 final-state topology scope",
            ),
            Exclusion(
                exclusion_kind="relation",
                local_id=None,
                reason="pair relations and has_point_probe are outside schema_version 1 scope",
            ),
            Exclusion(
                exclusion_kind="measurement",
                local_id=None,
                reason="pair measurements and point-probe measurements are outside schema_version 1 scope",
            ),
        ],
        notes=[
            "Descriptors resolve by equality; a descriptor that matches zero or several entities is a record defect.",
            "local_id is a within-file handle, not a graph identity.",
        ],
    )


def _edge_index(edge: cq.Edge, shape: cq.Shape) -> int:
    key = edge_key(edge)
    for index, candidate in enumerate(shape.Edges()):
        if edge_key(candidate) == key:
            return index
    raise ValueError("edge not found in shape")


def _vertex_index(vertex: cq.Vertex, shape: cq.Shape) -> int:
    target = point3d(vertex.toTuple())
    for index, candidate in enumerate(shape.Vertices()):
        if point3d(candidate.toTuple()) == target:
            return index
    raise ValueError("vertex not found in shape")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    text = args.program.read_text(encoding="utf-8")
    oracle = build_oracle(args.slug, text)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(oracle.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.out}")
    print(
        f"entities={len(oracle.expected.entities)} relations={len(oracle.expected.relations)} measurements={len(oracle.expected.measurements)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
