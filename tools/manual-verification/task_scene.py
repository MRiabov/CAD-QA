"""Tessellated scene payload for the dataset browser.

The browser asks the backend for one scene per program. This module turns a
CadQuery shape into flat triangle and line-segment positions and a typed
:class:`ScenePayload` the frontend can draw with three.js. It imports no CAD
kernel at module import time, so the payload models and the HTTP API load
without CadQuery.

This is a manual-verification devtool. The generator never imports it.
"""

from __future__ import annotations

from enum import StrEnum
from itertools import pairwise
from typing import Annotated, Any, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

UnitChannel = Annotated[float, Field(ge=0.0, le=1.0)]
Color: TypeAlias = tuple[UnitChannel, UnitChannel, UnitChannel]
Point: TypeAlias = tuple[float, float, float]

FACE_COLOR: Color = (0.68, 0.73, 0.80)
EDGE_COLOR: Color = (0.12, 0.14, 0.18)

#: Bump when the tessellation or payload shape changes, so a stale cache is not
#: reused.
SCENE_VERSION = 1
#: Chord tolerance, in the program frame's length unit, for face tessellation.
FACE_TOLERANCE = 0.1
#: Samples per edge. A straight edge ignores the extra samples; a curved one
#: needs them.
EDGE_SAMPLES = 32


class PrimitiveKind(StrEnum):
    """How three.js draws one part."""

    TRIANGLES = "triangles"
    LINES = "lines"


class MeshPart(BaseModel):
    """One draw call; ``positions`` is a flat ``x, y, z`` sequence."""

    model_config = ConfigDict(extra="forbid")

    primitive_kind: PrimitiveKind
    color: Color
    positions: list[float] = Field(min_length=0)


class LegendEntry(BaseModel):
    """One colour row of the viewer legend."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=16)
    label: str = Field(min_length=1, max_length=120)
    detail: str = Field(default="", max_length=240)
    color: Color


class ScenePayload(BaseModel):
    """Everything the frontend needs to draw one final solid state."""

    model_config = ConfigDict(extra="forbid")

    scene_version: int = Field(default=SCENE_VERSION, ge=1)
    parts: list[MeshPart] = Field(default_factory=list)
    legend: list[LegendEntry] = Field(default_factory=list)
    bounds_min: Point = (0.0, 0.0, 0.0)
    bounds_max: Point = (0.0, 0.0, 0.0)
    triangle_count: int = Field(default=0, ge=0)
    segment_count: int = Field(default=0, ge=0)


def _round(value: float) -> float:
    """Trim tessellation noise so the payload stays small."""

    return round(float(value), 4)


def _point(vector: Any) -> Point:
    """A CadQuery or OCP point as a plain coordinate triple."""

    return (float(vector.x), float(vector.y), float(vector.z))


def _bounds(positions: list[float]) -> tuple[Point, Point]:
    if not positions:
        return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    xs = positions[0::3]
    ys = positions[1::3]
    zs = positions[2::3]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def face_positions(shape: Any) -> list[float]:
    """Tessellate every face into flat triangle positions.

    ``Shape.tessellate`` returns one vertex list and one index list per face.
    The index list is expanded into standalone triangles because the frontend
    draws one attribute buffer per part and has no index buffer.
    """

    positions: list[float] = []
    for face in shape.Faces():
        vertices, triangles = face.tessellate(FACE_TOLERANCE)
        points = [_point(vertex) for vertex in vertices]
        for triangle in triangles:
            for index in triangle:
                positions.extend(_round(value) for value in points[int(index)])
    return positions


def edge_positions(shape: Any) -> list[float]:
    """Discretise every edge into flat line-segment positions."""

    positions: list[float] = []
    for edge in shape.Edges():
        points = [
            _point(edge.positionAt(index / EDGE_SAMPLES))
            for index in range(EDGE_SAMPLES + 1)
        ]
        for start, end in pairwise(points):
            positions.extend(_round(value) for value in start)
            positions.extend(_round(value) for value in end)
    return positions


def scene_from_shape(shape: Any) -> ScenePayload:
    """Tessellate one shape and assemble the scene payload."""

    faces = face_positions(shape)
    edges = edge_positions(shape)
    parts: list[MeshPart] = []
    if faces:
        parts.append(
            MeshPart(
                primitive_kind=PrimitiveKind.TRIANGLES,
                color=FACE_COLOR,
                positions=faces,
            )
        )
    if edges:
        parts.append(
            MeshPart(
                primitive_kind=PrimitiveKind.LINES,
                color=EDGE_COLOR,
                positions=edges,
            )
        )
    bounds_min, bounds_max = _bounds(faces + edges)
    legend = [
        LegendEntry(
            key="body",
            label="final solid state",
            detail="the shape the program returns",
            color=FACE_COLOR,
        ),
        LegendEntry(
            key="edge",
            label="CAD edge",
            detail="every edge of the final solid state",
            color=EDGE_COLOR,
        ),
    ]
    return ScenePayload(
        parts=parts,
        legend=legend,
        bounds_min=bounds_min,
        bounds_max=bounds_max,
        triangle_count=len(faces) // 9,
        segment_count=len(edges) // 6,
    )
