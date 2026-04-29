from cad_qa.trace import (
    _generated_selector_descriptors_for_snapshot,
    _generated_selector_tables_for_snapshot,
    _point_query_descriptors_for_snapshots,
    _point_queries_for_snapshots,
)


class _FakeSelection:
    def __init__(self, count: int):
        self._count = count

    def vals(self):
        return list(range(self._count))


class _FakeWorkplane:
    def faces(self, selector=None):
        return _FakeSelection(6 if selector is None else 1)

    def edges(self, selector=None):
        return _FakeSelection(12 if selector is None else 4)

    def vertices(self, selector=None):
        return _FakeSelection(8 if selector is None else 2)

    def Volume(self):
        return 8.0

    def isInside(self, point, tolerance):
        del tolerance
        return all(-1.0 < coordinate < 1.0 for coordinate in point)


def test_generated_selector_tables_cover_hypothetical_common_selectors():
    snapshot = {"feature_id": "wp1"}
    tables = _generated_selector_tables_for_snapshot(
        snapshot, {"wp1": _FakeWorkplane()}
    )

    expressions = {table["selector_expression"] for table in tables}

    assert "wp1.faces()" in expressions
    assert 'wp1.faces(">Z")' in expressions
    assert 'wp1.edges("|Z")' in expressions
    assert "wp1.vertices()" in expressions
    assert {table["selector_origin"] for table in tables} == {"generated"}


def test_generated_selector_descriptors_are_created_before_evaluation():
    snapshot = {"feature_id": "wp1", "snapshot_id": "snap_wp1_0001", "step_index": 1}

    descriptors = _generated_selector_descriptors_for_snapshot(snapshot)

    assert len(descriptors) > 40
    assert {descriptor["task_type"] for descriptor in descriptors} == {
        "selector_count"
    }
    assert {"generated_face", "generated_edge", "generated_vertex"} <= {
        descriptor["stratum"] for descriptor in descriptors
    }
    assert all("selected_count" not in descriptor["payload"] for descriptor in descriptors)


def test_point_queries_are_generated_for_each_snapshot_aabb():
    snapshots = [
        {
            "snapshot_id": "snap_wp1_0001",
            "feature_id": "wp1",
            "step_index": 1,
            "bbox": {"min": [-1.0, -1.0, -1.0], "max": [1.0, 1.0, 1.0]},
            "diagnostics": {
                "entity_signatures": {
                    "face": [
                        {
                            "entity_id": "face_0000",
                            "entity_type": "face",
                            "geometry_type": "PLANE",
                            "center": [0.0, 0.0, 1.0],
                        }
                    ],
                    "edge": [
                        {
                            "entity_id": "edge_0000",
                            "entity_type": "edge",
                            "geometry_type": "LINE",
                            "center": [1.0, 0.0, 0.0],
                        }
                    ],
                    "vertex": [
                        {
                            "entity_id": "vertex_0000",
                            "entity_type": "vertex",
                            "geometry_type": "VERTEX",
                            "center": [1.0, 1.0, 1.0],
                        }
                    ],
                }
            },
        },
        {
            "snapshot_id": "snap_wp2_0002",
            "feature_id": "wp2",
            "step_index": 2,
            "bbox": {"min": [-2.0, -2.0, -2.0], "max": [2.0, 2.0, 2.0]},
        },
    ]

    rows = _point_queries_for_snapshots(
        {"wp1": _FakeWorkplane(), "wp2": _FakeWorkplane()}, snapshots
    )

    assert {row["target_feature_id"] for row in rows} == {"wp1", "wp2"}
    assert {"deep_inside", "expanded_aabb_outside"} <= {
        row["sampling_stratum"] for row in rows
    }
    assert {"near_boundary_inside", "near_boundary_outside"} <= {
        row["sampling_stratum"] for row in rows
    }
    near_row = next(
        row for row in rows if row["sampling_stratum"] == "near_boundary_inside"
    )
    assert near_row["adaptive_boundary_margin_mm"] == 0.02
    assert near_row["max_aabb_side_length_mm"] == 2.0
    assert near_row["point_export_sigfigs"] == 4
    assert near_row["nearest_entity_diagnostics"]["entity_id"] in {
        "face_0000",
        "edge_0000",
        "vertex_0000",
    }


def test_point_descriptors_exist_for_aabb_and_adaptive_near_boundary_strata():
    snapshots = [
        {
            "snapshot_id": "snap_wp1_0001",
            "feature_id": "wp1",
            "step_index": 1,
            "bbox": {"min": [-1.0, -1.0, -1.0], "max": [1.0, 1.0, 1.0]},
            "diagnostics": {
                "entity_signatures": {
                    "face": [
                        {
                            "entity_id": "face_0000",
                            "entity_type": "face",
                            "geometry_type": "PLANE",
                            "center": [0.0, 0.0, 1.0],
                        }
                    ],
                }
            },
        }
    ]

    descriptors = _point_query_descriptors_for_snapshots(snapshots)

    assert {
        "aabb_uniform_inside",
        "expanded_aabb_outside",
        "near_boundary_inside",
        "near_boundary_outside",
    } <= {descriptor["stratum"] for descriptor in descriptors}
    assert {descriptor["task_type"] for descriptor in descriptors} == {
        "point_membership"
    }
    assert all("point_classification" not in descriptor["payload"] for descriptor in descriptors)
    near_payload = next(
        descriptor["payload"]
        for descriptor in descriptors
        if descriptor["stratum"] == "near_boundary_inside"
    )
    assert near_payload["adaptive_boundary_margin_mm"] == 0.02
    assert near_payload["point_export_sigfigs"] == 4
