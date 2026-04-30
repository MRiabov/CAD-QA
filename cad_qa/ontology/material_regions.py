"""Conservative material-region helpers."""

from __future__ import annotations


def feature_effect_from_profile(profile: dict[str, object], operation: str, distance: float | None) -> dict[str, object]:
    signed_distance = float(distance or 0.0)
    area = float(profile.get("area") or 0.0)
    sign = -1.0 if operation.startswith("cut") else 1.0
    return {
        "operation": operation,
        "signed_volume_delta": sign * area * abs(signed_distance),
        "edge_count_delta": int(profile.get("edge_count") or 0),
        "circular_edge_delta": 2 if profile.get("kind") == "circle" and operation in {"extrude", "cutBlind", "cutThruAll"} else 0,
        "evidence": "profile_area_times_distance",
    }
