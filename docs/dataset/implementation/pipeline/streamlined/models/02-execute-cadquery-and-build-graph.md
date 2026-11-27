# 02a/02b execute CadQuery — typed models

> Owning pipeline stages: `02a`, `02b` (Python).
> Contracts: [`../../02-execute-cadquery-and-build-graph.md`](../../02-execute-cadquery-and-build-graph.md).
> Schemas: [`../../extraction/ast-schema.md`](../../extraction/ast-schema.md),
> [`../../extraction/runtime-schema.md`](../../extraction/runtime-schema.md).
> Graph typed models: [`02c-build-cad-graph.md`](02c-build-cad-graph.md).

## Shared primitives and enums (Python)

```python
from enum import StrEnum

from pydantic import BaseModel, Field


class SourceSpan(BaseModel):
    start_line: int = Field(ge=1)
    start_column: int = Field(ge=0)
    end_line: int = Field(ge=1)
    end_column: int = Field(ge=0)


class Point2D(BaseModel):
    x: float
    y: float


class Point3D(BaseModel):
    x: float
    y: float
    z: float


class Vector3D(BaseModel):
    x: float
    y: float
    z: float


class OperationKind(StrEnum):
    WORKPLANE = "workplane"
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


class ProfileKind(StrEnum):
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    ELLIPSE = "ellipse"
    POLYGON = "polygon"
    SLOT = "slot"
    OTHER = "other"


class PathKind(StrEnum):
    LINE = "line"
    POLYLINE = "polyline"
    SPLINE = "spline"
    ARC = "arc"
    HELIX = "helix"
    OTHER = "other"


class PathSegmentKind(StrEnum):
    LINE = "line"
    ARC = "arc"
    SPLINE = "spline"
    OTHER = "other"


class SelectorKind(StrEnum):
    STRING = "string"
    CALL = "call"
    FILTER = "filter"
    IMPLICIT = "implicit"


class NamedPlane(StrEnum):
    XY = "xy"
    YZ = "yz"
    XZ = "xz"


class WorkplaneKind(StrEnum):
    NAMED = "named"
    CUSTOM = "custom"
    FACE = "face"


class FrameStatus(StrEnum):
    EXPLICIT = "explicit"
    DERIVED = "derived"
    UNKNOWN = "unknown"


class EntityCategory(StrEnum):
    FACE = "face"
    EDGE = "edge"
    VERTEX = "vertex"


class ResultKind(StrEnum):
    WORKPLANE = "workplane"
    WORKPLANE_LIST = "workplane_list"
    SHAPE = "shape"
    SHAPE_LIST = "shape_list"
    LIST = "list"
    SCALAR = "scalar"
    PLANE = "plane"
    VECTOR = "vector"
    EDGE = "edge"
    WIRE = "wire"
    NONE = "none"


class ErrorKind(StrEnum):
    TIMEOUT = "timeout"
    MEMORY = "memory"
    CADQUERY_EXCEPTION = "cadquery_exception"
    RECORDER = "recorder"
    RESULT_KIND = "result_kind"
    NON_SOLID_RESULT = "non_solid_result"
    MISSING_STATE = "missing_state"
    MISSING_SHAPE = "missing_shape"
    UNMAPPED_ENTITY = "unmapped_entity"
    FINGERPRINT_COLLISION = "fingerprint_collision"
    NO_STATE = "no_state"
    GEOMETRY_CAPTURE = "geometry_capture"
    INTERNAL = "internal"


class ProbeClassifier(StrEnum):
    IS_INSIDE = "is_inside"


class AstStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
```

## 02a — AST extraction result (Python, Parquet)

```python
class DictEntry(BaseModel):
    key: "AstExpression"
    value: "AstExpression"


class AstExpression(BaseModel):
    expression_kind: str
    source_span: SourceSpan
    literal_value: str | None = None
    name: str | None = None
    value_expression: "AstExpression | None" = None
    attribute: str | None = None
    subscript: "AstExpression | None" = None
    callee: "AstExpression | None" = None
    args: list["AstExpression"] = []
    kwargs: dict[str, "AstExpression"] = {}
    elements: list["AstExpression"] = []
    entries: list[DictEntry] = []
    operator: str | None = None
    operand: "AstExpression | None" = None
    lambda_parameter: str | None = None
    lambda_body: "AstExpression | None" = None


class FilterPredicate(BaseModel):
    attribute: str
    comparator: str
    threshold: float


class PathSegment(BaseModel):
    segment_kind: PathSegmentKind
    start: Point2D | Point3D | None = None
    end: Point2D | Point3D | None = None
    control_points: list[Point2D | Point3D] = []
    center: Point2D | Point3D | None = None
    radius: float | None = None
    start_angle: float | None = None
    end_angle: float | None = None
    normal: Vector3D | None = None
    is_closed: bool


class AstOperation(BaseModel):
    operation_id: str = Field(pattern=r"^op:\d{6}$")
    order: int = Field(ge=0)
    source_line: int = Field(ge=1)
    source_span: SourceSpan
    result_var: str = Field(min_length=1)
    method: str = Field(min_length=1)
    operation_kind: OperationKind
    receiver: AstExpression | None = None
    receiver_var: str | None = None
    args: list[AstExpression] = []
    kwargs: dict[str, AstExpression] = {}
    input_vars: list[str] = []
    is_state_producing: bool
    feature_kind: FeatureKind | None = None
    solid_kind: SolidKind | None = None


class AstAlias(BaseModel):
    alias_id: str = Field(pattern=r"^alias:\d{6}$")
    alias_kind: str  # "name" | "subscript"
    order: int = Field(ge=0)
    source_line: int = Field(ge=1)
    result_var: str = Field(min_length=1)
    target_var: str | None = None
    target_expression: AstExpression | None = None
    source_span: SourceSpan


class AstWorkplane(BaseModel):
    workplane_id: str
    operation_id: str
    workplane_kind: WorkplaneKind
    named_plane: NamedPlane | None = None
    origin: Point3D | None = None
    x_direction: Vector3D | None = None
    normal: Vector3D | None = None
    frame_status: FrameStatus
    derived_from_workplane_id: str | None = None
    source_selector_id: str | None = None
    offset: float | None = None
    tag: str | None = None
    args: list[AstExpression] = []
    source_span: SourceSpan


class AstProfile(BaseModel):
    profile_id: str
    operation_id: str
    profile_kind: ProfileKind
    dimensions: dict[str, AstExpression] = {}
    points: list[Point2D] | None = None
    is_closed: bool
    workplane_id: str | None = None
    source_span: SourceSpan


class AstPath(BaseModel):
    path_id: str
    operation_id: str
    path_kind: PathKind
    points: list[Point3D] | None = None
    segments: list[PathSegment] = []
    is_closed: bool
    workplane_id: str | None = None
    source_span: SourceSpan


class AstSelector(BaseModel):
    selector_id: str = Field(pattern=r"^sel:")
    operation_id: str
    selector_kind: SelectorKind
    selected_entity_category: EntityCategory
    selector_expression: str | None = None
    receiver_var: str
    filter_predicate: FilterPredicate | None = None
    source_span: SourceSpan


class CadQueryImport(BaseModel):
    alias: str = "cq"


class AstFailure(BaseModel):
    failure_kind: str
    message: str
    source_line: int | None = None


class CadQueryAstExtractionResult(BaseModel):
    """One program. A rejection has status=failure and no downstream records."""

    program_id: str
    program_sha256: str
    normalization_version: str
    extractor_version: str
    ast_schema_version: str
    canonicalization_version: str
    ast_status: AstStatus
    imports: list[CadQueryImport] = []
    operations: list[AstOperation] = []
    aliases: list[AstAlias] = []
    workplanes: list[AstWorkplane] = []
    profiles: list[AstProfile] = []
    paths: list[AstPath] = []
    selectors: list[AstSelector] = []
    ast_extraction_result_sha256: str | None = None
    failure: AstFailure | None = None
```

The AST rejection reason set is closed: `syntax`, `import`, `module_shape`,
`assignment_shape`, `unsupported_expression`, `unsupported_call`, `chained_call`,
`unknown_method`, `unresolved_name`, `duplicate_target`, `missing_result`,
`invalid_id`, `invalid_reference`, `internal`.

## 02b — Runtime extraction result (Python, Parquet)

```python
class ExecutionEnvironment(BaseModel):
    """The environment class, not a machine. Recorded in the run manifest."""

    os_arch: str
    timeout_seconds: int = Field(gt=0)
    memory_limit_bytes: int = Field(gt=0)
    worker_preload: bool
    worker_request_limit: int = Field(gt=0)
    environment_id: str


class RecordedAssignment(BaseModel):
    """Instrumentation ABI record; persisted as runtime_recordings."""

    operation_id: str
    result_var: str
    result_kind: ResultKind
    state_id: str | None = None
    selector_result_id: str | None = None
    source_span: SourceSpan


class EntityFingerprint(BaseModel):
    point: Point3D | None = None
    start: Point3D | None = None
    end: Point3D | None = None
    length: float | None = None
    centroid: Point3D | None = None
    area: float | None = None
    normal: Vector3D | None = None
    bbox: "BoundingBox | None" = None


class BoundingBox(BaseModel):
    min: Point3D
    max: Point3D


class BoundingBoxChange(BaseModel):
    before: BoundingBox
    after: BoundingBox


class TopologyDelta(BaseModel):
    face_delta: int
    edge_delta: int
    vertex_delta: int


class RuntimeEntity(BaseModel):
    state_id: str
    entity_id: str = Field(pattern=r"^ent:[0-9a-f]{64}$")
    entity_category: EntityCategory
    fingerprint: EntityFingerprint
    fingerprint_sha256: str
    face_surface_kind: str | None = None
    edge_curve_kind: str | None = None
    is_closed: bool | None = None


class ShapeSnapshot(BaseModel):
    state_id: str = Field(pattern=r"^state:op:")
    operation_id: str
    shape_hash: str
    is_solid: bool
    is_valid: bool
    volume: float
    bbox_min: Point3D
    bbox_max: Point3D
    centroid: Point3D
    face_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    vertex_count: int = Field(ge=0)
    entity_table_ref: str
    entities: list[RuntimeEntity] = []
    source_span: SourceSpan


class RuntimeBinding(BaseModel):
    """Recorder binding for one variable name; replaced only by its own assignment."""

    result_kind: ResultKind
    state_id: str | None = None
    workplane_id: str | None = None
    selected_category: EntityCategory | None = None


class WorkplaneFrameCapture(BaseModel):
    workplane_id: str
    operation_id: str
    origin: Point3D
    x_direction: Vector3D
    normal: Vector3D
    workplane_kind: WorkplaneKind
    named_plane: NamedPlane | None = None
    source_span: SourceSpan


class CadQuerySelectorResult(BaseModel):
    selector_result_id: str = Field(pattern=r"^sres:")
    selector_id: str
    selected_entity_category: EntityCategory
    state_id: str
    selected_entity_ids: list[str]
    count: int = Field(ge=0)
    source_span: SourceSpan


class PointProbe(BaseModel):
    probe_id: str = Field(pattern=r"^probe:")
    state_id: str
    probe_index: int = Field(ge=0, le=1)
    point: Point3D
    is_inside: bool
    distance_to_face_surface: float = Field(ge=0)
    classifier: ProbeClassifier
    margin: float = Field(ge=0)
    source_span: SourceSpan | None = None


class PairDistance(BaseModel):
    pair_id: str = Field(pattern=r"^pair:")
    state_id: str
    subject_entity_id: str
    object_entity_id: str
    subject_category: EntityCategory
    object_category: EntityCategory
    distance: float = Field(ge=0)
    kernel_call: str


class EffectEvidence(BaseModel):
    before_state_id: str | None = None
    after_state_id: str
    rule: str
    refs: list["RuntimeEvidenceRef"] = []


class CadFeatureSolidStateEffectDelta(BaseModel):
    effect_id: str = Field(pattern=r"^effect:")
    operation_id: str
    before_state_id: str | None = None
    after_state_id: str
    volume_change: float | None = None
    bbox_change: BoundingBoxChange | None = None
    topology_change: TopologyDelta | None = None
    evidence: EffectEvidence


class TopologyRelationKind(StrEnum):
    FACE_HAS_EDGE = "face_has_edge"
    EDGE_HAS_VERTEX = "edge_has_vertex"
    FACE_ADJACENT_TO_FACE = "face_adjacent_to_face"
    SOLID_HAS_FACE = "solid_has_face"
    SOLID_HAS_EDGE = "solid_has_edge"
    SOLID_HAS_VERTEX = "solid_has_vertex"


class TopologyEvidence(BaseModel):
    relation_kind: TopologyRelationKind
    from_entity_id: str
    to_entity_id: str
    call: str
    refs: list["RuntimeEvidenceRef"] = []


class RuntimeTopology(BaseModel):
    topology_id: str = Field(pattern=r"^topo:")
    state_id: str
    relation_kind: TopologyRelationKind
    from_entity_id: str
    to_entity_id: str
    evidence: TopologyEvidence


class RuntimeEvidenceRef(BaseModel):
    kind: str
    state_id: str | None = None
    entity_id: str | None = None
    operation_id: str | None = None
    span: SourceSpan | None = None
    call: str | None = None
    selector_result_id: str | None = None
    artifact_uri: str | None = None
    artifact_field: str | None = None


class CadQueryRuntimeExtractionSuccess(BaseModel):
    program_id: str
    program_sha256: str
    ast_extraction_result_sha256: str
    environment: ExecutionEnvironment
    operation_recordings: list[RecordedAssignment]
    shape_snapshots: list[ShapeSnapshot]
    workplane_frames: list[WorkplaneFrameCapture]
    selector_results: list[CadQuerySelectorResult]
    effect_deltas: list[CadFeatureSolidStateEffectDelta]
    point_probes: list[PointProbe]
    pair_distances: list[PairDistance]
    runtime_topology: list[RuntimeTopology]
    final_state_id: str
    runtime_extraction_result_sha256: str


class FailureTombstone(BaseModel):
    program_id: str
    program_sha256: str
    operation_id: str | None = None
    error_kind: ErrorKind
    message: str
    source_line: int | None = None
    source_span: SourceSpan | None = None
    environment: ExecutionEnvironment
    cache_key: str


CadQueryRuntimeExtractionResult = CadQueryRuntimeExtractionSuccess | FailureTombstone
```

A failure tombstone hashes only the program row and the failure row. A state has
at most two point probes; a state with none supports no membership task.
