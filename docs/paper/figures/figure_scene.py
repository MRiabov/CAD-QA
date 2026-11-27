"""Geometry and typed scene document for the paper's example task figure.

This module owns the CAD-specific half of the figure: it reads a gold oracle,
executes its program, binds the answer's target and the entity each clue names,
and returns the typed scene and panel the renderer consumes. It draws nothing;
``task_figure.py`` drives Blender and Pillow.
"""

from __future__ import annotations

import itertools
import sys
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
DEVTOOLS = REPO_ROOT / "tools/manual-verification"
sys.path.insert(0, str(DEVTOOLS))

from task_oracle_runner import PRELUDE
from task_oracle_schema import (
    Answer,
    Clue,
    EntityCategory,
    EntityDescriptor,
    TaskOracle,
    Unit,
    render_answer_value,
)

#: The answer's entity. Orange reads as "this is what is asked about".
TARGET_COLOR: tuple[float, float, float] = (0.91, 0.35, 0.05)
CLUE_COLORS: tuple[tuple[float, float, float], ...] = (
    (0.26, 0.39, 0.92),
    (0.18, 0.62, 0.27),
    (0.66, 0.25, 0.72),
)
BODY_COLOR: tuple[float, float, float] = (0.80, 0.82, 0.86)
WIRE_COLOR: tuple[float, float, float] = (0.33, 0.36, 0.41)
FACE_TOLERANCE = 0.02
WIRE_RADIUS = 0.045
TARGET_RADIUS = 0.12

RENDER_WIDTH = 1400
RENDER_HEIGHT = 1024
RENDER_SAMPLES = 64
CAMERA_DIRECTION = (1.0, -1.2, 1.6)
ORTHO_MARGIN = 1.08

FIGURE_WIDTH = 2100
FIGURE_HEIGHT = 1260
PANEL_WIDTH = 880
LEGEND_HEIGHT = 160
DPI = 300

FONT_DIR = Path("/usr/share/fonts/truetype")
SANS_REGULAR = FONT_DIR / "noto/NotoSans-Regular.ttf"
SANS_BOLD = FONT_DIR / "noto/NotoSans-Bold.ttf"
MONO_REGULAR = FONT_DIR / "dejavu/DejaVuSansMono.ttf"


class FigureError(RuntimeError):
    """The record names geometry this figure cannot bind."""


class LabelKind(StrEnum):
    TARGET = "target"
    CLUE = "clue"


class MeshPart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    color: tuple[float, float, float]
    smooth: bool
    vertices: list[tuple[float, float, float]]
    triangles: list[tuple[int, int, int]]


class EdgeGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    color: tuple[float, float, float]
    radius: float = Field(gt=0.0)
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]]


class SceneLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=8)
    position: tuple[float, float, float]
    color: tuple[float, float, float]
    kind: LabelKind


class LegendItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    color: tuple[float, float, float]


class CameraSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    direction: tuple[float, float, float]
    ortho_margin: float = Field(gt=1.0, le=2.0)


class RenderSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int = Field(ge=256, le=4096)
    height: int = Field(ge=256, le=4096)
    samples: int = Field(ge=1, le=1024)


class SceneSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(min_length=1)
    bounds_min: tuple[float, float, float]
    bounds_max: tuple[float, float, float]
    camera: CameraSpec
    render: RenderSpec
    parts: list[MeshPart]
    edge_groups: list[EdgeGroup]
    labels: list[SceneLabel]
    legend: list[LegendItem]


class PanelClue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: int = Field(ge=1)
    statement: str = Field(min_length=1)
    color: tuple[float, float, float]


class PanelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eyebrow: str = Field(min_length=1)
    question: str = Field(min_length=1)
    clues: list[PanelClue]
    narrows: list[int]
    answer: str = Field(min_length=1)
    answer_label: str = Field(min_length=1)
    program: str = Field(min_length=1)


class FigureSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    panel: PanelSpec
    scene: SceneSpec


class BoundEntity(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    descriptor: EntityDescriptor
    shape: Any
    color: tuple[float, float, float]
    role: str = Field(min_length=1)


def load_oracle(directory: Path, slug: str) -> TaskOracle:
    path = directory / f"{slug}.json"
    if not path.is_file():
        raise FigureError(f"oracle record does not exist: {path}")
    return TaskOracle.model_validate_json(path.read_text(encoding="utf-8"))


def execute_program(program: str) -> Any:
    namespace: dict[str, Any] = {"__name__": "__figure__"}
    exec(PRELUDE + program, namespace)  # noqa: S102 - checked-in gold record
    result = namespace.get("result")
    if result is None:
        raise FigureError("program did not bind `result`")
    return result.val() if hasattr(result, "val") else result


def _entities(shape: Any, category: EntityCategory) -> list[Any]:
    match category:
        case EntityCategory.FACE:
            return list(shape.Faces())
        case EntityCategory.EDGE:
            return list(shape.Edges())
        case EntityCategory.VERTEX:
            return list(shape.Vertices())
        case _:
            raise FigureError(f"cannot bind category {category.value!r} to the solid")


def _apply_filter(
    entities: list[Any], key: str, value: str, category: EntityCategory
) -> list[Any]:
    match key:
        case "position":
            axis, extreme = _parse_position(value)
            centre = lambda entity: getattr(entity.Center(), axis)
            values = [centre(entity) for entity in entities]
            if not values:
                return []
            target = max(values) if extreme == "max" else min(values)
            return [
                entity for entity in entities if abs(centre(entity) - target) < 1e-6
            ]
        case "surface_kind" | "curve_kind":
            wanted = value.upper()
            return [
                entity for entity in entities if entity.geomType().upper() == wanted
            ]
        case "centroid_x" | "centroid_y" | "centroid_z":
            axis = key[-1]
            wanted = float(value)
            return [
                entity
                for entity in entities
                if abs(getattr(entity.Center(), axis) - wanted) < 1e-6
            ]
        case _:
            raise FigureError(
                f"unsupported filter {key!r} for category {category.value!r}"
            )


def _parse_position(value: str) -> tuple[str, str]:
    match value:
        case "max_x" | "min_x":
            return "x", value[:3]
        case "max_y" | "min_y":
            return "y", value[:3]
        case "max_z" | "min_z":
            return "z", value[:3]
        case _:
            raise FigureError(f"unsupported bounding-box position {value!r}")


def select_entity(shape: Any, descriptor: EntityDescriptor) -> Any:
    entities = _entities(shape, descriptor.category)
    for key, value in descriptor.filters.items():
        entities = _apply_filter(entities, key, value, descriptor.category)
    if len(entities) != 1:
        raise FigureError(
            f"{descriptor.category.value} filters {descriptor.filters} matched "
            f"{len(entities)} entities, not one"
        )
    return entities[0]


def _fingerprint(entity: Any) -> tuple[float, ...]:
    centre = entity.Center()
    match entity.geomType().upper():
        case "PLANE" | "CYLINDER":
            return (
                round(centre.x, 6),
                round(centre.y, 6),
                round(centre.z, 6),
                round(entity.Area(), 6),
            )
        case _:
            return (
                round(centre.x, 6),
                round(centre.y, 6),
                round(centre.z, 6),
                round(entity.Length(), 6),
            )


def _clue_entity(clue: Clue) -> EntityDescriptor | None:
    match clue.check.predicate_kind:
        case "relation":
            return clue.check.object
        case "comparison":
            return clue.check.reference
        case _:
            # A property clue describes the target itself; there is no second
            # entity to colour.
            return None


def bound_entities(oracle: TaskOracle, shape: Any) -> list[BoundEntity]:
    measurement = [
        ref
        for ref in oracle.answer.evidence_refs
        if ref.reference_kind == "measurement" and ref.subject is not None
    ]
    if not measurement:
        raise FigureError("answer has no measurement reference to bind the target")
    target = measurement[0].subject
    assert target is not None
    bound = [
        BoundEntity(
            descriptor=target,
            shape=select_entity(shape, target),
            color=TARGET_COLOR,
            role="target",
        )
    ]
    seen = {_fingerprint(bound[0].shape)}
    for index, clue in enumerate(oracle.clues):
        descriptor = _clue_entity(clue)
        if descriptor is None:
            continue
        entity = select_entity(shape, descriptor)
        fingerprint = _fingerprint(entity)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        bound.append(
            BoundEntity(
                descriptor=descriptor,
                shape=entity,
                color=CLUE_COLORS[index % len(CLUE_COLORS)],
                role=f"clue {clue.order}",
            )
        )
    return bound


def _tessellate_faces(
    faces: list[Any],
) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    vertices: list[tuple[float, float, float]] = []
    triangles: list[tuple[int, int, int]] = []
    for face in faces:
        points, indices = face.tessellate(FACE_TOLERANCE)
        offset = len(vertices)
        vertices.extend(
            (
                round(float(point.x), 6),
                round(float(point.y), 6),
                round(float(point.z), 6),
            )
            for point in points
        )
        triangles.extend(
            (offset + int(index[0]), offset + int(index[1]), offset + int(index[2]))
            for index in indices
        )
    return vertices, triangles


def _edge_segments(
    edge: Any, samples: int
) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    count = 2 if edge.geomType().upper() == "LINE" else samples
    points = [edge.positionAt(index / count) for index in range(count + 1)]
    return [
        (
            (
                round(float(start.x), 6),
                round(float(start.y), 6),
                round(float(start.z), 6),
            ),
            (round(float(end.x), 6), round(float(end.y), 6), round(float(end.z), 6)),
        )
        for start, end in itertools.pairwise(points)
    ]


def _label_position(
    entity: Any, descriptor: EntityDescriptor
) -> tuple[float, float, float]:
    match descriptor.category:
        case EntityCategory.EDGE:
            point = entity.positionAt(0.5)
            return (point.x - 0.12, point.y, point.z + 0.05)
        case EntityCategory.FACE:
            if entity.geomType().upper() == "CYLINDER":
                centre = entity.Center()
                box = entity.BoundingBox()
                radius = (box.xmax - box.xmin) / 2
                return (centre.x + 0.65 * radius, centre.y + 0.65 * radius, centre.z)
            box = entity.BoundingBox()
            return (
                box.xmin + 0.18 * (box.xmax - box.xmin),
                box.ymin + 0.22 * (box.ymax - box.ymin),
                box.zmax + 0.03,
            )
        case _:
            raise FigureError(
                f"no label anchor for category {descriptor.category.value!r}"
            )


def _answer_text(answer: Answer) -> str:
    value = render_answer_value(answer.value_kind, answer.value)
    match answer.unit:
        case Unit.MILLIMETRE:
            return f"{value} mm"
        case Unit.SQUARE_MILLIMETRE:
            return f"{value} mm²"
        case Unit.CUBIC_MILLIMETRE:
            return f"{value} mm³"
        case Unit.DEGREE:
            return f"{value}°"
        case _:
            return value


_POSITION_LABEL = {
    "min_x": "left",
    "max_x": "right",
    "min_y": "front",
    "max_y": "back",
    "min_z": "bottom",
    "max_z": "top",
}


def _descriptor_detail(descriptor: EntityDescriptor) -> str:
    """A short phrase naming the entity, for the render legend."""

    filters = descriptor.filters
    match descriptor.category:
        case EntityCategory.FACE:
            if "position" in filters:
                return f"{_POSITION_LABEL[filters['position']]} face"
            if "surface_kind" in filters:
                return f"{filters['surface_kind']} face"
        case EntityCategory.EDGE:
            if "curve_kind" in filters:
                return f"{filters['curve_kind']} edge"
        case _:
            pass
    return descriptor.category.value.replace("_", " ")


def _legend(bound: list[BoundEntity]) -> list[LegendItem]:
    return [
        LegendItem(
            label="target" if entity.role == "target" else entity.role,
            detail=_descriptor_detail(entity.descriptor),
            color=entity.color,
        )
        for entity in bound
    ]


def build_figure(oracle: TaskOracle) -> FigureSpec:
    shape = execute_program(oracle.program.text)
    bound = bound_entities(oracle, shape)
    bound_fingerprints = {_fingerprint(entity.shape) for entity in bound}

    body_faces = [
        face for face in shape.Faces() if _fingerprint(face) not in bound_fingerprints
    ]
    target_edge = next(
        (entity.shape for entity in bound if entity.role == "target"),
        None,
    )
    body_edges = [
        edge
        for edge in shape.Edges()
        if target_edge is None or _fingerprint(edge) != _fingerprint(target_edge)
    ]

    parts: list[MeshPart] = []
    if body_faces:
        vertices, triangles = _tessellate_faces(body_faces)
        parts.append(
            MeshPart(
                name="body",
                color=BODY_COLOR,
                smooth=False,
                vertices=vertices,
                triangles=triangles,
            )
        )
    for entity in bound:
        if entity.descriptor.category != EntityCategory.FACE:
            continue
        vertices, triangles = _tessellate_faces([entity.shape])
        parts.append(
            MeshPart(
                name=entity.role.replace(" ", "-"),
                color=entity.color,
                smooth=entity.shape.geomType().upper() == "CYLINDER",
                vertices=vertices,
                triangles=triangles,
            )
        )

    edge_groups: list[EdgeGroup] = []
    if body_edges:
        edge_groups.append(
            EdgeGroup(
                name="wire",
                color=WIRE_COLOR,
                radius=WIRE_RADIUS,
                segments=[
                    segment
                    for edge in body_edges
                    for segment in _edge_segments(edge, samples=64)
                ],
            )
        )
    if target_edge is not None:
        edge_groups.append(
            EdgeGroup(
                name="target",
                color=TARGET_COLOR,
                radius=TARGET_RADIUS,
                segments=_edge_segments(target_edge, samples=96),
            )
        )

    labels = [
        SceneLabel(
            text="T" if entity.role == "target" else entity.role.split()[1],
            position=_label_position(entity.shape, entity.descriptor),
            color=entity.color,
            kind=LabelKind.TARGET if entity.role == "target" else LabelKind.CLUE,
        )
        for entity in bound
    ]

    box = shape.BoundingBox()
    scene = SceneSpec(
        slug=oracle.slug,
        bounds_min=(box.xmin, box.ymin, box.zmin),
        bounds_max=(box.xmax, box.ymax, box.zmax),
        camera=CameraSpec(
            direction=CAMERA_DIRECTION,
            ortho_margin=ORTHO_MARGIN,
        ),
        render=RenderSpec(
            width=RENDER_WIDTH,
            height=RENDER_HEIGHT,
            samples=RENDER_SAMPLES,
        ),
        parts=parts,
        edge_groups=edge_groups,
        labels=labels,
        legend=_legend(bound),
    )

    panel = PanelSpec(
        eyebrow="CAD-QA · task example",
        question=oracle.task.question,
        clues=[
            PanelClue(
                order=clue.order,
                statement=clue.statement,
                color=CLUE_COLORS[index % len(CLUE_COLORS)],
            )
            for index, clue in enumerate(oracle.clues)
        ],
        narrows=[
            oracle.clues[0].narrows.before,
            *[clue.narrows.after for clue in oracle.clues],
        ],
        answer=_answer_text(oracle.answer),
        answer_label="Answer",
        program=oracle.program.text.rstrip() + "\n",
    )
    return FigureSpec(panel=panel, scene=scene)
