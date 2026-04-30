"""Profile geometry helpers."""

from __future__ import annotations

import math
from typing import Any, Sequence


def circle_profile(radius: float) -> dict[str, Any]:
    return {
        "kind": "circle",
        "radius": radius,
        "area": math.pi * radius * radius,
        "perimeter": 2.0 * math.pi * radius,
        "centroid": [0.0, 0.0],
        "local_bbox": {"min": [-radius, -radius], "max": [radius, radius]},
        "edge_count": 1,
        "vertex_count": 1,
        "primitive_segment_counts": {"arc": 1, "line": 0},
    }


def rect_profile(width: float, height: float) -> dict[str, Any]:
    return {
        "kind": "rect",
        "width": width,
        "height": height,
        "area": width * height,
        "perimeter": 2.0 * (width + height),
        "centroid": [0.0, 0.0],
        "local_bbox": {"min": [-width / 2.0, -height / 2.0], "max": [width / 2.0, height / 2.0]},
        "edge_count": 4,
        "vertex_count": 4,
        "primitive_segment_counts": {"arc": 0, "line": 4},
    }


def polyline_profile(points: Sequence[Sequence[float]], *, closed: bool = True) -> dict[str, Any]:
    pts = [[float(point[0]), float(point[1])] for point in points]
    if len(pts) < 3:
        raise ValueError("closed polyline profile requires at least three points")
    area = _polygon_area(pts) if closed else 0.0
    perimeter = _polyline_perimeter(pts, closed=closed)
    centroid = _polygon_centroid(pts) if closed and abs(area) > 1e-12 else _mean_point(pts)
    xs = [point[0] for point in pts]
    ys = [point[1] for point in pts]
    return {
        "kind": "polyline",
        "points": pts,
        "closed": closed,
        "area": abs(area),
        "perimeter": perimeter,
        "centroid": centroid,
        "local_bbox": {"min": [min(xs), min(ys)], "max": [max(xs), max(ys)]},
        "edge_count": len(pts) if closed else max(0, len(pts) - 1),
        "vertex_count": len(pts),
        "primitive_segment_counts": {"arc": 0, "line": len(pts) if closed else max(0, len(pts) - 1)},
    }


def _polyline_perimeter(points: list[list[float]], *, closed: bool) -> float:
    pairs = list(zip(points, points[1:], strict=False))
    if closed:
        pairs.append((points[-1], points[0]))
    return sum(math.dist(a, b) for a, b in pairs)


def _polygon_area(points: list[list[float]]) -> float:
    total = 0.0
    for a, b in zip(points, points[1:] + points[:1], strict=False):
        total += a[0] * b[1] - b[0] * a[1]
    return total / 2.0


def _polygon_centroid(points: list[list[float]]) -> list[float]:
    area = _polygon_area(points)
    factor = 1.0 / (6.0 * area)
    cx = 0.0
    cy = 0.0
    for a, b in zip(points, points[1:] + points[:1], strict=False):
        cross = a[0] * b[1] - b[0] * a[1]
        cx += (a[0] + b[0]) * cross
        cy += (a[1] + b[1]) * cross
    return [cx * factor, cy * factor]


def _mean_point(points: list[list[float]]) -> list[float]:
    return [
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    ]
