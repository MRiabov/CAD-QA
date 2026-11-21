"""Typed models for the CadQuery-query scratch experiment.

Terminology follows docs/dataset/requirements/terminology.md. Enum values are spelled as in the
specs where a spec term exists.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

Point3 = tuple[float, float, float]

SEED = "cadqa-cq-scratch-20261022"
EXPERIMENT_VERSION = "cq-query-scratch-v1"
PARALLEL_TOLERANCE_DEG = 0.1
COMPARISON_REL_TOL = 1e-3
FACE_MATCH_CENTER_TOL = 1e-5
FACE_MATCH_AREA_REL_TOL = 1e-6
ANSWER_REL_TOL = 1e-3
ANSWER_ABS_TOL = 1e-6


class EntityCategory(StrEnum):
    FACE = "face"
    EDGE = "edge"
    VERTEX = "vertex"


class ClueType(StrEnum):
    PROPERTY = "property"
    RELATION = "relation"
    COMPARISON = "comparison"
    AGGREGATION = "aggregation"
    PROVENANCE = "provenance"


class TargetCategory(StrEnum):
    OPERATION = "operation"
    SOLID_STATE = "solid_state"
    FACE = "face"
    EDGE = "edge"
    VERTEX = "vertex"
    SCALAR_VALUE = "scalar_value"


class AnswerMeaning(StrEnum):
    VOLUME = "volume"
    AREA = "area"
    LENGTH = "length"
    DISTANCE = "distance"
    COUNT = "count"
    POSITION = "position"
    MATERIAL_CHANGE = "material_change"
    TOPOLOGY_CHANGE = "topology_change"


class AnswerFormat(StrEnum):
    NUMBER = "number"
    INTEGER = "integer"
    COORDINATE = "3d_coordinate"


class CheckKind(StrEnum):
    """One typed task clue check. The clue type is derived from the kind."""

    GEOM_KIND = "geom_kind"
    AXIS_PARALLEL = "axis_parallel"
    AXIS_PERPENDICULAR = "axis_perpendicular"
    AXIS_FACING = "axis_facing"
    THRESHOLD = "threshold"
    EXTREME = "extreme"
    CREATED_BY = "created_by"
    ADJACENT_TO_ANCHOR = "adjacent_to_anchor"
    PARALLEL_TO_ANCHOR = "parallel_to_anchor"
    PERPENDICULAR_TO_ANCHOR = "perpendicular_to_anchor"
    EDGE_OF_ANCHOR_FACE = "edge_of_anchor_face"
    FACE_HAS_ANCHOR_EDGE = "face_has_anchor_edge"
    SHARES_VERTEX_WITH_ANCHOR = "shares_vertex_with_anchor"
    ENDPOINT_OF_ANCHOR_EDGE = "endpoint_of_anchor_edge"
    EDGE_HAS_ANCHOR_VERTEX = "edge_has_anchor_vertex"
    FACE_HAS_ANCHOR_VERTEX = "face_has_anchor_vertex"
    VERTEX_OF_ANCHOR_FACE = "vertex_of_anchor_face"
    COMPARE_TO_ANCHOR = "compare_to_anchor"


CLUE_TYPE_BY_CHECK: dict[CheckKind, ClueType] = {
    CheckKind.GEOM_KIND: ClueType.PROPERTY,
    CheckKind.AXIS_PARALLEL: ClueType.PROPERTY,
    CheckKind.AXIS_PERPENDICULAR: ClueType.PROPERTY,
    CheckKind.AXIS_FACING: ClueType.PROPERTY,
    CheckKind.THRESHOLD: ClueType.PROPERTY,
    CheckKind.EXTREME: ClueType.AGGREGATION,
    CheckKind.CREATED_BY: ClueType.PROVENANCE,
    CheckKind.COMPARE_TO_ANCHOR: ClueType.COMPARISON,
}


def clue_type_of(kind: CheckKind) -> ClueType:
    return CLUE_TYPE_BY_CHECK.get(kind, ClueType.RELATION)


class Axis(StrEnum):
    X = "x"
    Y = "y"
    Z = "z"


class Measure(StrEnum):
    AREA = "area"
    LENGTH = "length"
    RADIUS = "radius"
    CENTER_X = "center_x"
    CENTER_Y = "center_y"
    CENTER_Z = "center_z"


class Comparator(StrEnum):
    GREATER = "greater"
    LESS = "less"


class Extreme(StrEnum):
    MAX = "max"
    MIN = "min"


class AnswerStepKind(StrEnum):
    # Step count 1: the target is named directly.
    FINAL_VOLUME = "final_volume"
    FINAL_SURFACE_AREA = "final_surface_area"
    FINAL_CENTER = "final_center"
    FINAL_FACE_COUNT = "final_face_count"
    FINAL_EDGE_COUNT = "final_edge_count"
    STATE_VOLUME = "state_volume"
    OPERATION_VOLUME_CHANGE = "operation_volume_change"
    OPERATION_FACE_COUNT_CHANGE = "operation_face_count_change"
    # After clue steps.
    ENTITY_AREA = "entity_area"
    ENTITY_LENGTH = "entity_length"
    ENTITY_RADIUS = "entity_radius"
    ENTITY_CENTER = "entity_center"
    DISTANCE_TO_ANCHOR = "distance_to_anchor"
    SET_COUNT = "set_count"


# ---------------------------------------------------------------- extraction facts


class FaceFact(BaseModel):
    entity_id: str = Field(min_length=68, max_length=68)
    kind: str = Field(min_length=1, max_length=16, description="CadQuery geomType(), e.g. PLANE.")
    area: float = Field(ge=0.0)
    center: Point3
    normal: Point3
    bbox_min: Point3
    bbox_max: Point3
    edge_ids: list[str] = Field(default_factory=list)
    vertex_ids: list[str] = Field(default_factory=list)


class EdgeFact(BaseModel):
    entity_id: str = Field(min_length=68, max_length=68)
    kind: str = Field(min_length=1, max_length=16, description="CadQuery geomType(), e.g. LINE.")
    length: float = Field(ge=0.0)
    center: Point3
    start: Point3
    end: Point3
    direction: Point3 | None = Field(default=None, description="Unit direction for LINE edges.")
    radius: float | None = Field(default=None, gt=0.0, description="Radius for CIRCLE edges.")
    vertex_ids: list[str] = Field(default_factory=list)


class VertexFact(BaseModel):
    entity_id: str = Field(min_length=68, max_length=68)
    point: Point3

    @property
    def center(self) -> Point3:
        return self.point


Entity = FaceFact | EdgeFact | VertexFact


class FaceFingerprint(BaseModel):
    center: Point3
    area: float = Field(ge=0.0)


class SolidStateFact(BaseModel):
    """A solid state produced by one top-level assignment (02b ShapeSnapshot subset)."""

    state_id: str = Field(min_length=1, max_length=64)
    operation_id: str = Field(min_length=1, max_length=64)
    result_var: str = Field(min_length=1, max_length=64)
    receiver_var: str | None = Field(default=None, max_length=64)
    method: str = Field(min_length=1, max_length=64)
    source_line: int = Field(ge=1)
    volume: float
    area: float = Field(ge=0.0)
    center: Point3
    face_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    vertex_count: int = Field(ge=0)
    faces: list[FaceFingerprint] = Field(default_factory=list)
    has_before_solid: bool = Field(description="receiver.findSolid() returned a solid before this operation.")
    before_volume: float = Field(default=0.0, description="Volume of the modified solid; 0 if none.")
    before_face_count: int = Field(default=0, ge=0)
    before_faces: list[FaceFingerprint] = Field(default_factory=list)


class ProgramFacts(BaseModel):
    program_id: str = Field(min_length=10, max_length=80)
    program_sha256: str = Field(min_length=64, max_length=64)
    source_id: str = Field(min_length=1, max_length=64)
    collection: str = Field(min_length=1, max_length=64)
    family_id: str = Field(min_length=1, max_length=200)
    program_text: str = Field(min_length=1)
    final_var: str = Field(min_length=1, max_length=64)
    final_state_id: str = Field(min_length=1, max_length=64)
    states: list[SolidStateFact]
    faces: list[FaceFact]
    edges: list[EdgeFact]
    vertices: list[VertexFact]
    adjacent_face_pairs: list[tuple[str, str]] = Field(default_factory=list)


class PoolEntry(BaseModel):
    source_id: str = Field(min_length=1, max_length=64)
    collection: str = Field(min_length=1, max_length=64)
    family_id: str = Field(min_length=1, max_length=200)
    program_id: str = Field(min_length=10, max_length=80)
    program_sha256: str = Field(min_length=64, max_length=64)
    order_key: str = Field(min_length=64, max_length=64)
    final_face_count: int = Field(ge=0)


class Rejection(BaseModel):
    stage: str = Field(min_length=1, max_length=40)
    subject: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=80)
    detail: str = Field(default="", max_length=2000)


# ---------------------------------------------------------------- task definitions


class ClueCheck(BaseModel):
    kind: CheckKind
    geom_kind: str | None = Field(default=None, max_length=16)
    axis: Axis | None = None
    positive: bool | None = Field(default=None, description="AXIS_FACING: +axis when true.")
    measure: Measure | None = None
    comparator: Comparator | None = None
    threshold: float | None = None
    extreme: Extreme | None = None
    operation_var: str | None = Field(default=None, max_length=64)
    receiver_var: str | None = Field(default=None, max_length=64)
    method: str | None = Field(default=None, max_length=64)
    source_line: int | None = Field(default=None, ge=1)


class ClueResult(BaseModel):
    before_count: int = Field(ge=1)
    after_count: int = Field(ge=1)


class TaskClue(BaseModel):
    clue_id: str = Field(min_length=1, max_length=16)
    order: int = Field(ge=1)
    clue_type: ClueType
    subject_category: EntityCategory
    anchor_label: str | None = Field(default=None, max_length=1)
    check: ClueCheck
    result: ClueResult


class Segment(BaseModel):
    """Clues that narrow one entity category; non-final segments bind a labeled anchor."""

    label: str = Field(min_length=1, max_length=1)
    category: EntityCategory
    clues: list[TaskClue]
    bound_entity_ids: list[str] = Field(min_length=1)


class AnswerStep(BaseModel):
    kind: AnswerStepKind
    operation_var: str | None = Field(default=None, max_length=64)
    receiver_var: str | None = Field(default=None, max_length=64)
    method: str | None = Field(default=None, max_length=64)
    source_line: int | None = Field(default=None, ge=1)
    anchor_label: str | None = Field(default=None, max_length=1)


class TaskValidity(BaseModel):
    every_clue_narrows: bool
    every_clue_necessary: bool
    unique_answer: bool
    geometry_required: bool
    gold_query_reproduces_answer: bool = False


class TaskDefinition(BaseModel):
    task_id: str = Field(min_length=10, max_length=40)
    definition_sha256: str = Field(min_length=64, max_length=64)
    program_id: str = Field(min_length=10, max_length=80)
    program_sha256: str = Field(min_length=64, max_length=64)
    source_id: str = Field(min_length=1, max_length=64)
    cadevolve_program_family_id: str = Field(min_length=1, max_length=200)
    target_category: TargetCategory
    segments: list[Segment] = Field(default_factory=list)
    answer_meaning: AnswerMeaning
    answer_step: AnswerStep
    native_answer_format: AnswerFormat
    gold_answer: float | int | Point3
    tolerance_rel: float = Field(default=ANSWER_REL_TOL, gt=0.0)
    tolerance_abs: float = Field(default=ANSWER_ABS_TOL, gt=0.0)
    clue_step_count: int = Field(ge=0)
    task_reasoning_step_count: int = Field(ge=1)
    validity: TaskValidity
    gold_query: str = Field(min_length=1)
    prompt: str = Field(default="", description="Rendered model-facing task text (04).")
    provenance: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------- evaluation


class Harness(StrEnum):
    SINGLE_SHOT = "single_shot"
    AGENTIC = "agentic"


class TurnRecord(BaseModel):
    """One assistant turn in the agentic harness, plus the tool results it received."""

    reasoning: str = ""
    content: str = ""
    tool_calls: list[dict] = Field(default_factory=list)
    tool_results: list[str] = Field(default_factory=list)
    finish_reason: str | None = Field(default=None, max_length=40)
    completion_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)


class Outcome(StrEnum):
    NO_TOOL_CALL = "no_tool_call"
    EXEC_ERROR = "exec_error"
    TIMEOUT = "timeout"
    LITERAL_ANSWER = "literal_answer"
    WRONG = "wrong"
    CORRECT = "correct"
    API_ERROR = "api_error"


class ModelCall(BaseModel):
    task_id: str = Field(min_length=10, max_length=40)
    model: str = Field(min_length=1, max_length=120)
    provider: str = Field(default="", max_length=200)
    harness: Harness = Harness.SINGLE_SHOT
    turns: list[TurnRecord] = Field(default_factory=list)
    run_query_calls: int = Field(default=0, ge=0)
    blocked_run_queries: int = Field(default=0, ge=0, description="run_query calls refused by the escape guard.")
    reasoning_effort: str | None = Field(default=None, max_length=16)
    vendor: str = Field(default="", max_length=64, description="Serving vendor (x-merge-vendor header).")
    system_prompt_sha256: str = Field(min_length=64, max_length=64)
    user_prompt_sha256: str = Field(min_length=64, max_length=64)
    reasoning: str = ""
    content: str = ""
    tool_calls: list[dict] = Field(default_factory=list)
    submitted_code: str | None = None
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)
    finish_reason: str | None = Field(default=None, max_length=40)
    cost_usd: float = Field(default=0.0, ge=0.0)
    latency_s: float = Field(default=0.0, ge=0.0)
    error: str | None = None


class QueryExecution(BaseModel):
    ok: bool
    answer: float | int | bool | list[float] | None = None
    error_type: str | None = Field(default=None, max_length=120)
    message: str | None = Field(default=None, max_length=4000)
    timed_out: bool = False
    repr_text: str | None = Field(default=None, max_length=4000, description="Explore mode: repr(answer).")
    stdout: str = Field(default="", max_length=4000)


class GradeResult(BaseModel):
    task_id: str = Field(min_length=10, max_length=40)
    task_reasoning_step_count: int = Field(ge=1)
    outcome: Outcome
    model_answer: float | int | bool | list[float] | None = None
    gold_answer: float | int | Point3
    error_type: str | None = None
    message: str | None = None
