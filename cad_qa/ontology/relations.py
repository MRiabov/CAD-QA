"""Relation and measurement registries."""

RELATION_FAMILIES = {
    "before",
    "after",
    "input_to",
    "combines",
    "created_by",
    "modified_by",
    "deleted_by",
    "bounded_by",
    "selected_by",
    "located_on",
    "uses_profile",
    "used_by",
    "parameter_of",
    "has_measurement",
    "has_normal",
    "has_centroid",
    "has_coordinate",
    "has_endpoint",
    "endpoint_of",
    "distance_to",
    "nearest_tangent_to",
    "parallel_to",
    "not_parallel_to",
    "perpendicular_to",
    "orthogonal_to",
    "coaxial_with",
    "same_length_as",
    "longer_than",
    "shorter_than",
    "adjacent_to",
    "opposite_to",
    "contained_in",
    "intersects",
    "adds_material_to",
    "removes_material_from",
    "same_selected_face_as",
    "same_selected_entity_as",
    "has_path_tangent",
    "nearest_point_on_path",
    "point_on_path",
    "segment_on_path",
    "has_stable_face_id",
    "has_kernel_stable_face_id",
    "has_kernel_stable_edge_id",
    "has_kernel_stable_vertex_id",
    "has_sketch_center",
    "has_material_region_geometry",
    "has_void_region_geometry",
    "has_kernel_material_region_geometry",
    "has_kernel_void_region_geometry",
}

MEASUREMENT_SCOPES = {
    "profile_intrinsic",
    "feature_application_effect",
    "entity_geometry",
    "snapshot_state",
    "relation_metric",
}


def assert_relation_type(relation_type: str) -> None:
    if relation_type not in RELATION_FAMILIES:
        raise ValueError(f"unknown relation family: {relation_type}")


def assert_measurement_scope(scope: str) -> None:
    if scope not in MEASUREMENT_SCOPES:
        raise ValueError(f"unknown measurement scope: {scope}")
