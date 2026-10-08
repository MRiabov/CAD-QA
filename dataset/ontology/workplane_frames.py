"""CadQuery workplane frame extraction helpers."""

from __future__ import annotations

import math
from typing import Any


DEFAULT_PLANES: dict[str, dict[str, list[float]]] = {
    "XY": {"normal": [0.0, 0.0, 1.0], "x_axis": [1.0, 0.0, 0.0], "y_axis": [0.0, 1.0, 0.0]},
    "XZ": {"normal": [0.0, -1.0, 0.0], "x_axis": [1.0, 0.0, 0.0], "y_axis": [0.0, 0.0, 1.0]},
    "YZ": {"normal": [1.0, 0.0, 0.0], "x_axis": [0.0, 1.0, 0.0], "y_axis": [0.0, 0.0, 1.0]},
}


def default_workplane_frame(plane: str = "XY", origin: list[float] | None = None) -> dict[str, Any]:
    axes = DEFAULT_PLANES.get(plane.upper(), DEFAULT_PLANES["XY"])
    return {
        "kind": "default",
        "plane": plane,
        "origin": [float(v) for v in (origin or [0.0, 0.0, 0.0])],
        "normal": axes["normal"],
        "x_axis": axes["x_axis"],
        "y_axis": axes["y_axis"],
    }


def explicit_workplane_frame(
    *,
    origin: list[float],
    x_axis: list[float],
    normal: list[float],
) -> dict[str, Any]:
    x_unit = _unit(x_axis)
    normal_unit = _unit(normal)
    y_axis = _unit(_cross(normal_unit, x_unit))
    return {
        "kind": "explicit_plane",
        "plane": "cq.Plane",
        "origin": [float(v) for v in origin],
        "normal": normal_unit,
        "x_axis": x_unit,
        "y_axis": y_axis,
    }


def project_local_point(frame: dict[str, Any], point: list[float]) -> list[float]:
    x, y = float(point[0]), float(point[1])
    origin = frame["origin"]
    x_axis = frame["x_axis"]
    y_axis = frame["y_axis"]
    return [
        origin[i] + x * x_axis[i] + y * y_axis[i]
        for i in range(3)
    ]


def _unit(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(float(v) * float(v) for v in vec))
    if norm == 0:
        raise ValueError("zero-length vector")
    return [float(v) / norm for v in vec]


def _cross(a: list[float], b: list[float]) -> list[float]:
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]
