"""Typed schema for the extraction-graph oracle records.

The JSON files under ``docs/dataset/implementation/pipeline/testing/oracles/
extraction-graph/`` are instances of :class:`Oracle`. The builder and the
validator both import this module so there is one definition of the format.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class _OracleModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OracleKind(StrEnum):
    EXTRACTION_GRAPH = "extraction-graph"


class OracleScope(StrEnum):
    FINAL_STATE = "final_state"


class VerificationStatus(StrEnum):
    PROPOSED = "proposed"
    VERIFIED = "verified"
    STALE = "stale"


class CadGraphEntityKind(StrEnum):
    CADQUERY_PROGRAM = "cadquery_program"
    OPERATION = "operation"
    FEATURE = "feature"
    SOLID_STATE = "solid_state"
    POINT_PROBE = "point_probe"
    FACE = "face"
    EDGE = "edge"
    VERTEX = "vertex"
    EDGE_ENDPOINT = "edge_endpoint"
    CADQUERY_PROFILE = "cadquery_profile"
    CADQUERY_WORKPLANE = "cadquery_workplane"
    CADQUERY_PATH = "cadquery_path"
    CADQUERY_PATH_POINT = "cadquery_path_point"
    CADQUERY_PATH_SEGMENT = "cadquery_path_segment"
    REGION = "region"
    CADQUERY_SELECTOR_RESULT = "cadquery_selector_result"


class RelationKind(StrEnum):
    BEFORE = "before"
    AFTER = "after"
    CREATES = "creates"
    USES = "uses"
    DERIVED_FROM = "derived_from"
    HAS_FACE = "has_face"
    HAS_EDGE = "has_edge"
    HAS_VERTEX = "has_vertex"
    ADJACENT_TO = "adjacent_to"
    ENDPOINT_OF = "endpoint_of"
    HAS_POINT_PROBE = "has_point_probe"
    COPLANAR_WITH = "coplanar_with"
    COAXIAL_WITH = "coaxial_with"
    SELECTED_FROM = "selected_from"
    SELECTED_BY = "selected_by"
    ADDS_MATERIAL = "adds_material"
    REMOVES_MATERIAL = "removes_material"
    PART_OF = "part_of"


class MeasurementKind(StrEnum):
    VOLUME = "volume"
    AREA = "area"
    LENGTH = "length"
    DISTANCE = "distance"
    ANGLE = "angle"
    BOUNDING_BOX = "bounding_box"
    CENTROID = "centroid"
    PROBE_POINT = "probe_point"
    DISTANCE_TO_FACE_SURFACE = "distance_to_face_surface"
    FACE_COUNT = "face_count"
    EDGE_COUNT = "edge_count"
    VERTEX_COUNT = "vertex_count"
    SELECTED_COUNT = "selected_count"
    VALIDITY = "validity"
    VOLUME_CHANGE = "volume_change"
    BOUNDING_BOX_CHANGE = "bounding_box_change"
    TOPOLOGY_CHANGE = "topology_change"
    CADQUERY_WORKPLANE_FRAME = "workplane_frame"


class OperationKind(StrEnum):
    CADQUERY_WORKPLANE = "workplane"
    SKETCH = "sketch"
    PATH = "path"
    SOLID = "solid"
    CADQUERY_SELECTOR = "cadquery_selector"
    BOOLEAN = "boolean"
    ASSEMBLY = "assembly"
    MODIFIER = "modifier"
    TRANSFORM = "transform"
    ACCESSOR = "accessor"


class FeatureKind(StrEnum):
    ADD_MATERIAL = "add_material"
    REMOVE_MATERIAL = "remove_material"
    MODIFY = "modify"
    CONSTRUCTION = "construction"


class SolidKind(StrEnum):
    PRIMITIVE = "primitive"
    EXTRUDE = "extrude"
    LOFT = "loft"
    SWEEP = "sweep"
    REVOLVE = "revolve"
    TWIST = "twist"
    TEXT = "text"
    BOOLEAN = "boolean"
    ASSEMBLY = "assembly"
    MODIFIER = "modifier"
    TRANSFORM = "transform"


class FilterName(StrEnum):
    PROGRAM_SHA256 = "program_sha256"
    ORDER = "order"
    METHOD = "method"
    OPERATION_ORDER = "operation_order"
    FEATURE_KIND = "feature_kind"
    IS_FINAL = "is_final"
    GEOMETRY_SURFACE_KIND = "surface_kind"
    CURVE_KIND = "curve_kind"
    AREA = "area"
    LENGTH = "length"
    CENTROID_X = "centroid_x"
    CENTROID_Y = "centroid_y"
    CENTROID_Z = "centroid_z"
    EDGE_LOCAL_ID = "edge_local_id"
    END = "end"
    FEATURE_OPERATION_ORDER = "feature_operation_order"
    REGION_SIGN = "region_sign"


class AttributeName(StrEnum):
    NORMALIZATION_VERSION = "normalization_version"
    OPERATION_KIND = "operation_kind"
    RESULT_VAR = "result_var"
    FEATURE_KIND = "feature_kind"
    IS_FINAL = "is_final"
    FACE_SURFACE_KIND = "face_surface_kind"
    EDGE_CURVE_KIND = "edge_curve_kind"
    REGION_SIGN = "region_sign"
    END = "end"


class Point3D(_OracleModel):
    x: str
    y: str
    z: str


class BoundingBox(_OracleModel):
    min: Point3D
    max: Point3D


class Verification(_OracleModel):
    status: VerificationStatus = VerificationStatus.PROPOSED
    verified_by: str | None = Field(default=None, min_length=1, max_length=200)
    verified_at: str | None = Field(default=None, min_length=1, max_length=40)
    rationale: str = Field(min_length=1, max_length=2000)


class Program(_OracleModel):
    program_id: str = Field(pattern=r"^cadqaprog:[0-9a-f]{64}$")
    program_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    text: str = Field(min_length=1)


class Environment(_OracleModel):
    cadquery_version: str = Field(min_length=1, max_length=50)
    ocp_version: str = Field(min_length=1, max_length=50)
    tolerance_policy_version: str = Field(min_length=1, max_length=50)
    tolerance_policy_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class Descriptor(_OracleModel):
    category: CadGraphEntityKind
    filters: dict[FilterName, str] = Field(default_factory=dict)


class CadGraphEntity(_OracleModel):
    local_id: str = Field(min_length=1, max_length=200)
    entity_kind: CadGraphEntityKind
    descriptor: Descriptor
    attributes: dict[AttributeName, str] = Field(default_factory=dict)


class Relation(_OracleModel):
    relation_kind: RelationKind
    from_local_id: str = Field(min_length=1, max_length=200)
    to_local_id: str = Field(min_length=1, max_length=200)
    evidence_rule: str = Field(min_length=1, max_length=100)


class Measurement(_OracleModel):
    measurement_kind: MeasurementKind
    subject_local_id: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1)
    unit: str | None = Field(default=None, max_length=30)
    tolerance: str | None = Field(default=None, max_length=50)


class Capability(_OracleModel):
    target_category: str = Field(min_length=1, max_length=50)
    clue_type: str = Field(min_length=1, max_length=50)
    clue_reduction_form: str | None = Field(default=None, max_length=50)
    answer_meaning: str = Field(min_length=1, max_length=50)


class Expected(_OracleModel):
    entities: list[CadGraphEntity]
    relations: list[Relation]
    measurements: list[Measurement]
    capabilities: list[Capability]


class Covers(_OracleModel):
    entity_kinds: list[CadGraphEntityKind]
    relation_kinds: list[RelationKind]
    measurement_kinds: list[MeasurementKind]


class Exclusion(_OracleModel):
    exclusion_kind: str = Field(min_length=1, max_length=30)
    local_id: str | None = Field(default=None, max_length=200)
    reason: str = Field(min_length=1, max_length=500)


class Oracle(_OracleModel):
    schema_version: int = Field(ge=1)
    oracle_kind: OracleKind
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    scope: OracleScope
    verification: Verification
    program: Program
    environment: Environment
    expected: Expected
    covers: Covers
    excluded: list[Exclusion]
    notes: list[str] = Field(default_factory=list)


class MethodSpec(_OracleModel):
    operation_kind: OperationKind
    feature_kind: FeatureKind | None = None
    solid_kind: SolidKind | None = None
    state_producing: bool
