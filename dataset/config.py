"""Configuration constants for graph-first CAD-QA."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GraphConfig:
    min_high_hop_clue_candidates: int = 3
    profile_polyline_max_points: int = 256
    numeric_tolerance: float = 1e-6


DEFAULT_CONFIG = GraphConfig()
