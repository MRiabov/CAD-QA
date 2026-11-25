"""Typed schema for the task-construction oracle records.

The JSON files under ``docs/dataset/implementation/pipeline/testing/oracles/
task-construction/`` are instances of :class:`TaskOracle`. The runner and the
validator both import this module so there is one definition of the format.
"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TOOL_VERSION = "1"

DECIMAL_TEXT = r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$"
SLUG = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
SHA256 = r"^[0-9a-f]{64}$"


class _OracleModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OracleKind(StrEnum):
    TASK_CONSTRUCTION = "task-construction"


class VerificationStatus(StrEnum):
    PROPOSED = "proposed"
    VERIFIED = "verified"
    STALE = "stale"


class GoldQueryStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_RUN = "not_run"


class TargetCategory(StrEnum):
    CADQUERY_PROGRAM = "cadquery_program"
    OPERATION = "operation"
    FEATURE = "feature"
    SOLID_STATE = "solid_state"
    FACE = "face"
    EDGE = "edge"
    VERTEX = "vertex"
    EDGE_ENDPOINT = "edge_endpoint"
    CADQUERY_PROFILE = "cadquery_profile"
    CADQUERY_WORKPLANE = "cadquery_workplane"
    PATH = "path"
    PATH_POINT = "path_point"
    PATH_SEGMENT = "path_segment"
    REGION = "region"
    CADQUERY_SELECTOR_RESULT = "cadquery_selector_result"
    SCALAR_VALUE = "scalar_value"


class EntityCategory(StrEnum):
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


class ClueType(StrEnum):
    PROPERTY = "property"
    RELATION = "relation"
    COMPARISON = "comparison"
    AGGREGATION = "aggregation"
    PROVENANCE = "provenance"


class ClueReductionForm(StrEnum):
    FILTERED = "filtered"
    SELECTED_IN_EARLIER_CLUE = "selected_in_earlier_clue"
    AGGREGATED = "aggregated"
    CROSS_STATE = "cross_state"


class CategoricalFeature(StrEnum):
    FACE_SURFACE_KIND = "face_surface_kind"
    POSITION = "position"


class FaceSurfaceKind(StrEnum):
    PLANE = "plane"
    CYLINDER = "cylinder"
    CONE = "cone"
    SPHERE = "sphere"
    TORUS = "torus"
    BSPLINE = "bspline"
    OTHER = "other"


class BoundingBoxPosition(StrEnum):
    MIN_X = "min_x"
    MAX_X = "max_x"
    MIN_Y = "min_y"
    MAX_Y = "max_y"
    MIN_Z = "min_z"
    MAX_Z = "max_z"


class ProgramAxis(StrEnum):
    PLUS_X = "+x"
    MINUS_X = "-x"
    PLUS_Y = "+y"
    MINUS_Y = "-y"
    PLUS_Z = "+z"
    MINUS_Z = "-z"


class AnswerMeaning(StrEnum):
    IDENTITY = "identity"
    VOLUME = "volume"
    AREA = "area"
    LENGTH = "length"
    DISTANCE = "distance"
    ANGLE = "angle"
    COUNT = "count"
    RANK = "rank"
    MEMBERSHIP = "membership"
    VALIDITY = "validity"
    POSITION = "position"
    EXTENT = "extent"
    CADQUERY_WORKPLANE_STATE = "cadquery_workplane_state"
    MATERIAL_CHANGE = "material_change"
    TOPOLOGY_CHANGE = "topology_change"


class AnswerFormat(StrEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    COORDINATE = "coordinate"
    BOUNDING_BOX = "bounding_box"
    STRUCTURED = "structured"


class ValueKind(StrEnum):
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    POINT = "point"
    BOUNDING_BOX = "bounding_box"
    LABEL = "label"
    STRUCTURED = "structured"


class Unit(StrEnum):
    MILLIMETRE = "millimetre"
    SQUARE_MILLIMETRE = "square_millimetre"
    CUBIC_MILLIMETRE = "cubic_millimetre"
    DEGREE = "degree"
    UNITLESS = "unitless"


class ToleranceKind(StrEnum):
    ABSOLUTE = "absolute"
    RELATIVE = "relative"


class ScoringRule(StrEnum):
    EXACT = "exact"
    NUMERIC_TOLERANCE = "numeric_tolerance"
    STRUCTURED_EXACT = "structured_exact"


class EvidenceKind(StrEnum):
    MEASURED = "measured"
    DERIVED = "derived"


class Comparator(StrEnum):
    EQ = "eq"
    GT = "gt"
    GE = "ge"
    LT = "lt"
    LE = "le"
    BETWEEN = "between"


class RelationType(StrEnum):
    HAS_FACE = "has_face"
    HAS_EDGE = "has_edge"
    HAS_VERTEX = "has_vertex"
    ADJACENT_TO = "adjacent_to"
    COPLANAR_WITH = "coplanar_with"
    COAXIAL_WITH = "coaxial_with"
    ENDPOINT_OF = "endpoint_of"
    USES = "uses"
    DERIVED_FROM = "derived_from"
    BEFORE = "before"
    AFTER = "after"
    CREATES = "creates"
    PART_OF = "part_of"
    ADDS_MATERIAL = "adds_material"
    REMOVES_MATERIAL = "removes_material"
    SELECTED_FROM = "selected_from"
    SELECTED_BY = "selected_by"
    HAS_POINT_PROBE = "has_point_probe"


class Direction(StrEnum):
    SUBJECT_TO_OBJECT = "subject_to_object"
    OBJECT_TO_SUBJECT = "object_to_subject"


class PositionPointKind(StrEnum):
    FACE_CENTROID = "face_centroid"
    EDGE_MIDPOINT = "edge_midpoint"
    VERTEX_POINT = "vertex_point"
    REGION_CENTROID = "region_centroid"
    SOLID_STATE_CENTROID = "solid_state_centroid"


class TopologyCategory(StrEnum):
    FACE = "face"
    EDGE = "edge"
    VERTEX = "vertex"


class Point3D(_OracleModel):
    x: str = Field(pattern=DECIMAL_TEXT)
    y: str = Field(pattern=DECIMAL_TEXT)
    z: str = Field(pattern=DECIMAL_TEXT)


class BoundingBox(_OracleModel):
    min: Point3D
    max: Point3D


class EntityDescriptor(_OracleModel):
    category: EntityCategory
    filters: dict[str, str] = Field(default_factory=dict)


class GoldQueryCheck(_OracleModel):
    status: GoldQueryStatus
    stdout: str | None = Field(default=None, min_length=1)
    checked_at: str | None = Field(default=None, min_length=1, max_length=40)


class Verification(_OracleModel):
    status: VerificationStatus = VerificationStatus.PROPOSED
    verified_by: str | None = Field(default=None, min_length=1, max_length=200)
    verified_at: str | None = Field(default=None, min_length=1, max_length=40)
    rationale: str = Field(min_length=1, max_length=2000)
    gold_query: GoldQueryCheck


class Environment(_OracleModel):
    cadquery_version: str = Field(min_length=1, max_length=50)
    ocp_version: str = Field(min_length=1, max_length=50)
    python_version: str = Field(min_length=1, max_length=50)
    oracle_tool_version: str = Field(min_length=1, max_length=50)


class Program(_OracleModel):
    program_id: str = Field(pattern=r"^cadqaprog:[0-9a-f]{64}$")
    program_sha256: str = Field(pattern=SHA256)
    text: str = Field(min_length=1)


class TaskDescription(_OracleModel):
    target_category: TargetCategory
    question: str = Field(min_length=1, max_length=300)
    state_scope: Literal["final"] = "final"
    possible_answer_count: int = Field(ge=1)
    task_reasoning_step_count: int = Field(ge=1)
    answer_meaning: AnswerMeaning
    native_answer_format: AnswerFormat
    answer_format: AnswerFormat
    geometry_required: bool
    uniqueness: str = Field(min_length=1, max_length=1000)


class PropertyMeasurementCheck(_OracleModel):
    predicate_kind: Literal["property"] = "property"
    property_shape: Literal["measurement"] = "measurement"
    measurement: str = Field(min_length=1, max_length=100)
    comparator: Comparator
    axis: ProgramAxis | None = None
    threshold: str | None = Field(default=None, pattern=DECIMAL_TEXT)
    range_min: str | None = Field(default=None, pattern=DECIMAL_TEXT)
    range_max: str | None = Field(default=None, pattern=DECIMAL_TEXT)

    @model_validator(mode="after")
    def _measurement_shape(self) -> PropertyMeasurementCheck:
        if self.comparator == Comparator.BETWEEN:
            if (
                self.threshold is not None
                or self.range_min is None
                or self.range_max is None
            ):
                raise ValueError("a between check needs range_min and range_max only")
        elif self.range_min is not None or self.range_max is not None:
            raise ValueError("only a between check carries a range")
        elif self.threshold is None:
            raise ValueError("a comparator check needs a threshold")
        if self.measurement == "angle":
            if self.axis is None:
                raise ValueError("a direction clue names the program axis")
        elif self.axis is not None:
            raise ValueError("only the angle measurement names a program axis")
        return self


class PropertyFeatureCheck(_OracleModel):
    predicate_kind: Literal["property"] = "property"
    property_shape: Literal["categorical_feature"] = "categorical_feature"
    feature: CategoricalFeature
    value: str = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def _value_matches_feature(self) -> PropertyFeatureCheck:
        match self.feature:
            case CategoricalFeature.FACE_SURFACE_KIND:
                FaceSurfaceKind(self.value)
            case CategoricalFeature.POSITION:
                BoundingBoxPosition(self.value)
        return self


PropertyCheck = Annotated[
    PropertyMeasurementCheck | PropertyFeatureCheck,
    Field(discriminator="property_shape"),
]


class NamedRelationCheck(_OracleModel):
    predicate_kind: Literal["relation"] = "relation"
    relation_shape: Literal["named"] = "named"
    relation_type: RelationType
    direction: Direction
    object: EntityDescriptor


class AngleRelationCheck(_OracleModel):
    predicate_kind: Literal["relation"] = "relation"
    relation_shape: Literal["angle"] = "angle"
    measurement: Literal["angle"] = "angle"
    comparator: Comparator
    threshold: str = Field(pattern=DECIMAL_TEXT)
    object: EntityDescriptor


RelationCheck = Annotated[
    NamedRelationCheck | AngleRelationCheck,
    Field(discriminator="relation_shape"),
]


class ComparisonCheck(_OracleModel):
    predicate_kind: Literal["comparison"] = "comparison"
    measurement: str = Field(min_length=1, max_length=100)
    comparator: Comparator
    reference: EntityDescriptor


class AggregationCheck(_OracleModel):
    predicate_kind: Literal["aggregation"] = "aggregation"
    scope: str = Field(min_length=1, max_length=100)
    aggregation_kind: Literal["extreme", "rank", "count"]
    measurement: str = Field(min_length=1, max_length=100)
    extreme: Literal["min", "max"] | None = None
    rank: int | None = Field(default=None, ge=1)


class ProvenanceCheck(_OracleModel):
    predicate_kind: Literal["provenance"] = "provenance"
    operation: EntityDescriptor | None = None
    cadquery_profile: EntityDescriptor | None = None

    @model_validator(mode="after")
    def _one_provenance(self) -> ProvenanceCheck:
        named = [
            item for item in (self.operation, self.cadquery_profile) if item is not None
        ]
        if len(named) != 1:
            raise ValueError(
                "a provenance clue names exactly one operation or CadQuery profile"
            )
        return self


ClueCheck = Annotated[
    PropertyCheck
    | RelationCheck
    | ComparisonCheck
    | AggregationCheck
    | ProvenanceCheck,
    Field(discriminator="predicate_kind"),
]


class Narrows(_OracleModel):
    before: int = Field(ge=1)
    after: int = Field(ge=1)


class Clue(_OracleModel):
    order: int = Field(ge=1)
    clue_type: ClueType
    clue_reduction_form: ClueReductionForm | None = None
    statement: str = Field(min_length=1, max_length=500)
    check: ClueCheck
    narrows: Narrows

    @model_validator(mode="after")
    def _predicate_kind_and_form(self) -> Clue:
        if self.clue_type.value != self.check.predicate_kind:
            raise ValueError(
                f"clue_type {self.clue_type.value!r} does not match "
                f"predicate_kind {self.check.predicate_kind!r}"
            )
        if self.clue_type == ClueType.PROPERTY and self.clue_reduction_form is not None:
            raise ValueError("a property clue has no clue reduction form")
        if self.clue_type != ClueType.PROPERTY and self.clue_reduction_form is None:
            raise ValueError(
                f"a {self.clue_type.value} clue needs a clue reduction form"
            )
        return self


class Tolerance(_OracleModel):
    tolerance_kind: ToleranceKind
    value_text: str = Field(pattern=DECIMAL_TEXT)

    @field_validator("value_text")
    @classmethod
    def _positive(cls, value: str) -> str:
        if float(value) <= 0:
            raise ValueError("tolerance must be positive")
        return value


class PointProbe(_OracleModel):
    point: Point3D
    location: Literal["inside", "outside"]
    distance_to_face_surface: str = Field(pattern=DECIMAL_TEXT)
    classifier: str = Field(min_length=1, max_length=100)
    margin: str = Field(pattern=DECIMAL_TEXT)


class EvidenceRef(_OracleModel):
    reference_kind: Literal["node", "relation", "measurement"]
    subject: EntityDescriptor | None = None
    object: EntityDescriptor | None = None
    measurement: str | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def _ref_shape(self) -> EvidenceRef:
        if self.reference_kind == "measurement":
            if self.subject is None or self.measurement is None:
                raise ValueError("a measurement ref needs a subject and a measurement")
        elif self.reference_kind == "node":
            if self.subject is None:
                raise ValueError("a node ref needs a subject")
        else:
            if self.subject is None or self.object is None:
                raise ValueError("a relation ref needs a subject and an object")
        return self


class EquivalentEntry(_OracleModel):
    subject: EntityDescriptor
    value: Any


class MembershipPointParameter(_OracleModel):
    parameter_kind: Literal["membership_point"] = "membership_point"
    point: Point3D


class DistanceReferenceParameter(_OracleModel):
    parameter_kind: Literal["distance_reference"] = "distance_reference"
    subject: EntityDescriptor


class AngleReferenceParameter(_OracleModel):
    parameter_kind: Literal["angle_reference"] = "angle_reference"
    subject: EntityDescriptor


class PositionPointParameter(_OracleModel):
    parameter_kind: Literal["position_point"] = "position_point"
    point_kind: PositionPointKind


class TopologyCategoryParameter(_OracleModel):
    parameter_kind: Literal["topology_category"] = "topology_category"
    category: TopologyCategory


AnswerParameter = Annotated[
    MembershipPointParameter
    | DistanceReferenceParameter
    | AngleReferenceParameter
    | PositionPointParameter
    | TopologyCategoryParameter,
    Field(discriminator="parameter_kind"),
]


class Answer(_OracleModel):
    value_kind: ValueKind
    value: Any
    unit: Unit | None = None
    tolerance: Tolerance | None = None
    scoring_rule: ScoringRule
    parameter: AnswerParameter | None = None
    point_probe: PointProbe | None = None
    evidence_kind: EvidenceKind
    evidence_rule: str = Field(min_length=1, max_length=100)
    evidence_refs: list[EvidenceRef] = Field(min_length=1)
    answer_equivalent_set: list[EquivalentEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def _value_shape(self) -> Answer:
        match self.value_kind:
            case ValueKind.NUMBER | ValueKind.LABEL:
                if not isinstance(self.value, str) or not self.value:
                    raise TypeError(f"{self.value_kind.value} value must be a string")
                if self.value_kind == ValueKind.NUMBER:
                    float(self.value)
            case ValueKind.INTEGER:
                if not isinstance(self.value, int) or isinstance(self.value, bool):
                    raise TypeError("integer value must be an integer")
            case ValueKind.BOOLEAN:
                if not isinstance(self.value, bool):
                    raise TypeError("boolean value must be a boolean")
            case ValueKind.POINT:
                Point3D.model_validate(self.value)
            case ValueKind.BOUNDING_BOX:
                BoundingBox.model_validate(self.value)
            case ValueKind.STRUCTURED:
                if not isinstance(self.value, dict):
                    raise TypeError("structured value must be an object")
        if self.value_kind in {
            ValueKind.NUMBER,
            ValueKind.POINT,
            ValueKind.BOUNDING_BOX,
        }:
            if self.scoring_rule != ScoringRule.NUMERIC_TOLERANCE:
                raise ValueError("a numeric answer uses numeric_tolerance")
            if self.tolerance is None:
                raise ValueError("a numeric answer needs a tolerance")
        elif self.value_kind == ValueKind.STRUCTURED:
            if self.scoring_rule != ScoringRule.STRUCTURED_EXACT:
                raise ValueError("a structured answer uses structured_exact")
            if self.tolerance is not None:
                raise ValueError("a structured answer has no tolerance")
        else:
            if self.scoring_rule != ScoringRule.EXACT:
                raise ValueError(f"a {self.value_kind.value} answer uses exact scoring")
            if self.tolerance is not None:
                raise ValueError(f"a {self.value_kind.value} answer has no tolerance")
        return self


class GoldQuery(_OracleModel):
    language: Literal["python"] = "python"
    code: str = Field(min_length=1)
    expected_stdout: str = Field(min_length=1)
    sha256: str = Field(pattern=SHA256)


class Covers(_OracleModel):
    target_category: TargetCategory
    clue_types: list[ClueType]
    clue_reduction_forms: list[ClueReductionForm]
    answer_meaning: AnswerMeaning
    answer_format: AnswerFormat
    task_reasoning_step_count: int = Field(ge=1)


class Exclusion(_OracleModel):
    exclusion_kind: str = Field(min_length=1, max_length=50)
    reason: str = Field(min_length=1, max_length=500)


NATIVE_FORMAT: dict[AnswerMeaning, set[AnswerFormat]] = {
    AnswerMeaning.IDENTITY: {AnswerFormat.MULTIPLE_CHOICE},
    AnswerMeaning.VOLUME: {AnswerFormat.NUMBER},
    AnswerMeaning.AREA: {AnswerFormat.NUMBER},
    AnswerMeaning.LENGTH: {AnswerFormat.NUMBER},
    AnswerMeaning.DISTANCE: {AnswerFormat.NUMBER},
    AnswerMeaning.ANGLE: {AnswerFormat.NUMBER},
    AnswerMeaning.COUNT: {AnswerFormat.INTEGER},
    AnswerMeaning.RANK: {AnswerFormat.INTEGER},
    AnswerMeaning.MEMBERSHIP: {AnswerFormat.BOOLEAN},
    AnswerMeaning.VALIDITY: {AnswerFormat.BOOLEAN},
    AnswerMeaning.POSITION: {AnswerFormat.COORDINATE},
    AnswerMeaning.EXTENT: {AnswerFormat.BOUNDING_BOX},
    AnswerMeaning.CADQUERY_WORKPLANE_STATE: {AnswerFormat.STRUCTURED},
    AnswerMeaning.MATERIAL_CHANGE: {AnswerFormat.NUMBER, AnswerFormat.INTEGER},
    AnswerMeaning.TOPOLOGY_CHANGE: {AnswerFormat.INTEGER},
}

FORMAT_TO_VALUE_KIND: dict[AnswerFormat, ValueKind] = {
    AnswerFormat.MULTIPLE_CHOICE: ValueKind.LABEL,
    AnswerFormat.NUMBER: ValueKind.NUMBER,
    AnswerFormat.INTEGER: ValueKind.INTEGER,
    AnswerFormat.BOOLEAN: ValueKind.BOOLEAN,
    AnswerFormat.COORDINATE: ValueKind.POINT,
    AnswerFormat.BOUNDING_BOX: ValueKind.BOUNDING_BOX,
    AnswerFormat.STRUCTURED: ValueKind.STRUCTURED,
}


class TaskOracle(_OracleModel):
    schema_version: int = Field(ge=1)
    oracle_kind: OracleKind
    slug: str = Field(pattern=SLUG)
    verification: Verification
    environment: Environment
    program: Program
    task: TaskDescription
    clues: list[Clue]
    answer: Answer
    gold_query: GoldQuery
    covers: Covers
    excluded: list[Exclusion]
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistent(self) -> TaskOracle:
        if self.oracle_kind != OracleKind.TASK_CONSTRUCTION:
            raise ValueError("oracle_kind must be task-construction")
        if self.environment.oracle_tool_version != TOOL_VERSION:
            raise ValueError(
                f"oracle_tool_version must be {TOOL_VERSION!r}; rerun the verifier"
            )

        native = NATIVE_FORMAT[self.task.answer_meaning]
        if self.task.native_answer_format not in native:
            raise ValueError(
                f"{self.task.answer_meaning.value} has no native format "
                f"{self.task.native_answer_format.value}"
            )
        if (
            self.task.answer_format != self.task.native_answer_format
            and self.task.answer_format != AnswerFormat.MULTIPLE_CHOICE
        ):
            raise ValueError(
                "answer_format may differ from native_answer_format only for "
                "multiple choice"
            )
        if self.answer.value_kind != FORMAT_TO_VALUE_KIND[self.task.answer_format]:
            raise ValueError(
                f"answer.value_kind {self.answer.value_kind.value} does not match "
                f"answer_format {self.task.answer_format.value}"
            )

        answer_step = 0 if self.task.answer_meaning == AnswerMeaning.IDENTITY else 1
        expected_steps = len(self.clues) + answer_step
        if self.task.task_reasoning_step_count != expected_steps:
            raise ValueError(
                f"task_reasoning_step_count is "
                f"{self.task.task_reasoning_step_count}, expected {expected_steps}"
            )

        if self.clues:
            orders = [clue.order for clue in self.clues]
            if orders != list(range(1, len(self.clues) + 1)):
                raise ValueError(f"clue orders {orders} are not 1..{len(self.clues)}")
            if self.clues[0].narrows.before != self.task.possible_answer_count:
                raise ValueError(
                    "the first clue does not start from possible_answer_count"
                )
            for earlier, later in zip(self.clues, self.clues[1:]):
                if earlier.narrows.after != later.narrows.before:
                    raise ValueError(
                        f"clue {earlier.order} does not end where clue "
                        f"{later.order} starts"
                    )
            for clue in self.clues:
                if clue.narrows.after >= clue.narrows.before:
                    raise ValueError(f"clue {clue.order} does not narrow")
        elif self.task.possible_answer_count != 1:
            raise ValueError(
                "a task with no clue identifies its target directly, so "
                "possible_answer_count must be 1"
            )

        if self.clues and self.clues[-1].narrows.after != len(
            self.answer.answer_equivalent_set
        ):
            raise ValueError(
                "the last clue's after count does not match the "
                "answer-equivalent set size"
            )

        for entry in self.answer.answer_equivalent_set:
            if entry.value != self.answer.value:
                raise ValueError(
                    "every answer-equivalent entry must give the answer value"
                )

        if self.answer.point_probe is not None:
            if self.task.answer_meaning != AnswerMeaning.MEMBERSHIP:
                raise ValueError("a point probe is only for a membership answer")
        elif self.task.answer_meaning == AnswerMeaning.MEMBERSHIP:
            raise ValueError("a membership answer needs a point probe")

        if self.task.answer_meaning == AnswerMeaning.MEMBERSHIP and not isinstance(
            self.answer.parameter, MembershipPointParameter
        ):
            raise ValueError("a membership answer needs a membership point")
        if self.task.answer_meaning == AnswerMeaning.POSITION and not isinstance(
            self.answer.parameter, PositionPointParameter
        ):
            raise ValueError("a position answer needs a position point kind")
        if self.task.answer_meaning == AnswerMeaning.DISTANCE and not isinstance(
            self.answer.parameter, DistanceReferenceParameter
        ):
            raise ValueError("a distance answer needs a reference subject")
        if self.task.answer_meaning == AnswerMeaning.ANGLE and not isinstance(
            self.answer.parameter, AngleReferenceParameter
        ):
            raise ValueError("an angle answer needs a reference subject")
        if self.task.answer_meaning == AnswerMeaning.TOPOLOGY_CHANGE and not isinstance(
            self.answer.parameter, TopologyCategoryParameter
        ):
            raise ValueError("a topology change answer needs a category")

        expected_covers = Covers(
            target_category=self.task.target_category,
            clue_types=[clue.clue_type for clue in self.clues],
            clue_reduction_forms=[
                clue.clue_reduction_form
                for clue in self.clues
                if clue.clue_reduction_form is not None
            ],
            answer_meaning=self.task.answer_meaning,
            answer_format=self.task.answer_format,
            task_reasoning_step_count=self.task.task_reasoning_step_count,
        )
        if self.covers != expected_covers:
            raise ValueError("covers does not match the task description and clues")

        if self.verification.status == VerificationStatus.VERIFIED and (
            not self.verification.verified_by or not self.verification.verified_at
        ):
            raise ValueError("a verified oracle needs verified_by and verified_at")

        return self


def render_answer_value(value_kind: ValueKind, value: Any) -> str:
    """Render the answer value the way a gold query must print it."""
    match value_kind:
        case ValueKind.NUMBER | ValueKind.LABEL:
            return str(value)
        case ValueKind.INTEGER:
            return str(int(value))
        case ValueKind.BOOLEAN:
            return "true" if value else "false"
        case ValueKind.POINT | ValueKind.BOUNDING_BOX | ValueKind.STRUCTURED:
            return json.dumps(value, sort_keys=True, separators=(",", ":"))
        case _:
            raise ValueError(f"unsupported value kind {value_kind!r}")
