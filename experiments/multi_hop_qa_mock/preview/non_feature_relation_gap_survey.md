# Non-Feature Relation Gap Survey

- Seed: `20260429`
- Sources sampled: `10`
- Entities per source: `5`

## Summary

### Sampled Entity Types

| Entity Type | Count |
|---|---:|
| `face` | 3 |
| `material_region` | 7 |
| `measurement` | 1 |
| `operation` | 1 |
| `parameter` | 1 |
| `path` | 5 |
| `profile` | 9 |
| `selector` | 4 |
| `solid` | 10 |
| `workplane` | 9 |

### Relation Opportunities By Support

| Support | Count |
|---|---:|
| `current` | 96 |
| `missing_needed` | 24 |
| `spec_only` | 46 |

### Observed Relation Types

| Relation | Count |
|---|---:|
| `adds_material_to` | 5 |
| `after` | 23 |
| `before` | 24 |
| `combines` | 5 |
| `created_by` | 5 |
| `has_centroid` | 10 |
| `has_material_region_geometry` | 5 |
| `has_measurement` | 10 |
| `has_normal` | 5 |
| `has_path_tangent` | 5 |
| `has_profile_geometry` | 9 |
| `has_workplane_frame` | 5 |
| `input_to` | 30 |
| `located_on` | 11 |
| `parameter_of` | 1 |
| `selected_by` | 3 |
| `used_by` | 9 |
| `uses_profile` | 1 |

### Missing But Necessary Families

| Family | Count |
|---|---:|
| `has_material_region_geometry` | 10 |
| `has_profile_geometry` | 9 |
| `has_sketch_center` | 9 |
| `has_workplane_frame` | 6 |
| `has_path_tangent` | 5 |
| `nearest_point_on_path` | 5 |
| `has_stable_face_id` | 5 |
| `same_selected_face_as` | 5 |
| `has_profile_application_effect` | 3 |
| `has_void_region_geometry` | 3 |

## Recommendations

| Relation Family | Observed Need | Recommendation |
|---|---:|---|
| `has_profile_geometry` | 9 | Implement AST/CadQuery profile extraction for circle, rect, polyline, and bounded helper point lists. |
| `has_profile_application_effect` | 3 | Link profiles to operation deltas so profile clues can refer to the effect of the cut/extrude. |
| `has_workplane_frame` | 6 | Persist workplane origin, axes, normal, and frame transforms for every profile. |
| `has_stable_face_id` | 5 | Persist selector-result face IDs and conservative adjacent-snapshot face matching. |
| `has_material_region_geometry` | 10 | Represent added material regions from extrude/sweep/union with centroid, bbox, volume, and adjacency hooks. |
| `has_void_region_geometry` | 3 | Represent removed void regions from cutBlind/cutThruAll/hole with volume, bbox, intersections, and selected face. |
| `has_path_tangent` | 5 | Extract source-defined or fitted path tangents for sweep/helix questions. |
| `same_selected_face_as` | 5 | Add equality joins over selector-result entities across operations. |

## Per-Source Samples

### `src_34c0838fa7a13794`

- Path: `CADEvolve-C/CADEvolve-C-core/ArrayBossHelixWire__01_25_emitted_centered_scaled_binarized/source_cadquery.py`
- Lines: `40`
- Visible ops: `Plane, Vector, Workplane, circle, extrude, moveTo, splineApprox, sweep, union`

| Sampled Entity | Type | Line |
|---|---|---:|
| `wp20 = circle(...)` | `profile` | 21 |
| `wp15 = Workplane(...)` | `workplane` | 16 |
| `wp10 = union(...)` | `solid` | 11 |
| `wp4 = moveTo(...)` | `path` | 5 |
| `added material` | `material_region` | 7 |

| Relation | Support | Evidence |
|---|---|---|
| `has_path_tangent` | `missing_needed` | needed for sweep path tangent questions |
| `input_to` | `current` | wp4 = moveTo(...) -> wp5 = circle(...) |
| `input_to` | `current` | wp4 = moveTo(...) -> wp6 = sweep(...) |
| `after` | `current` | wp10 = union(...) -> wp9 = extrude(...) |
| `combines` | `spec_only` | wp10 = union(...) -> wp10 = union(...) |
| `adds_material_to` | `spec_only` | wp10 = union(...) -> wp10 = union(...) |
| `has_measurement` | `current` | wp10 = union(...) -> volume bbox topology delta |
| `has_centroid` | `spec_only` | wp10 = union(...) -> feature centroid |
| `before` | `current` | wp10 = union(...) -> wp11 = Workplane(...) |
| `before` | `current` | wp10 = union(...) -> wp12 = circle(...) |

Missing/necessary relation families: `has_material_region_geometry`, `has_path_tangent`, `has_profile_geometry`, `has_sketch_center`, `has_workplane_frame`, `nearest_point_on_path`

### `src_1eb8170a79e73e2a`

- Path: `CADEvolve-P/ShapeNet-P/02924116+dca406daf4b48e6760a4e5b4a0135038+models+model_normalized+r09+s85+t170+p95+k00/source_cadquery.py`
- Lines: `27`
- Visible ops: `Workplane, append, box, center, close, cos, cutBlind, cutThruAll, faces, polyline, rect, sin, workplane`

| Sampled Entity | Type | Line |
|---|---|---:|
| `base = rect(...)` | `profile` | 25 |
| `base = workplane(...)` | `workplane` | 19 |
| `base = faces(...)` | `selector` | 26 |
| `face face` | `face` | 19 |
| `base = box(...)` | `solid` | 9 |

| Relation | Support | Evidence |
|---|---|---|
| `created_by` | `current` | base = box(...) -> base = box(...) |
| `has_material_region_geometry` | `missing_needed` | added-material geometry |
| `has_measurement` | `current` | base = box(...) -> volume bbox topology delta |
| `has_centroid` | `spec_only` | base = box(...) -> feature centroid |
| `selected_by` | `current` | face face -> base = faces(...) |
| `after` | `current` | base = workplane(...) -> base = box(...) |
| `before` | `current` | base = box(...) -> base = workplane(...) |
| `before` | `current` | base = box(...) -> base = polyline(...) |
| `before` | `current` | base = box(...) -> base = cutThruAll(...) |
| `located_on` | `spec_only` | base = workplane(...) -> face >Y |

Missing/necessary relation families: `has_material_region_geometry`, `has_profile_application_effect`, `has_profile_geometry`, `has_sketch_center`, `has_stable_face_id`, `has_void_region_geometry`, `same_selected_face_as`

### `src_faadee5616191d2f`

- Path: `CADEvolve-C/CADEvolve-C-core/ArrayBossHelixWire__05_25_emitted_centered_scaled_binarized/source_cadquery.py`
- Lines: `24`
- Visible ops: `Plane, Vector, Workplane, circle, extrude, moveTo, splineApprox, sweep, union`

| Sampled Entity | Type | Line |
|---|---|---:|
| `wp20 = circle(...)` | `profile` | 21 |
| `wp19 = Workplane(...)` | `workplane` | 20 |
| `wp10 = union(...)` | `solid` | 11 |
| `wp2 = splineApprox(...)` | `path` | 3 |
| `added material` | `material_region` | 18 |

| Relation | Support | Evidence |
|---|---|---|
| `has_path_tangent` | `missing_needed` | needed for sweep path tangent questions |
| `input_to` | `current` | wp2 = splineApprox(...) -> wp6 = sweep(...) |
| `after` | `current` | wp10 = union(...) -> wp9 = extrude(...) |
| `combines` | `spec_only` | wp10 = union(...) -> wp10 = union(...) |
| `adds_material_to` | `spec_only` | wp10 = union(...) -> wp10 = union(...) |
| `has_measurement` | `current` | wp10 = union(...) -> volume bbox topology delta |
| `has_centroid` | `spec_only` | wp10 = union(...) -> feature centroid |
| `before` | `current` | wp10 = union(...) -> wp11 = Workplane(...) |
| `before` | `current` | wp10 = union(...) -> wp12 = circle(...) |
| `before` | `current` | wp10 = union(...) -> wp13 = extrude(...) |

Missing/necessary relation families: `has_material_region_geometry`, `has_path_tangent`, `has_profile_geometry`, `has_sketch_center`, `has_workplane_frame`, `nearest_point_on_path`

### `src_4381883289a33860`

- Path: `CADEvolve-C/CADEvolve-C-core/ArrayBossHelixWire__02_25_emitted_centered_scaled_binarized/source_cadquery.py`
- Lines: `56`
- Visible ops: `Plane, Vector, Workplane, circle, extrude, moveTo, splineApprox, sweep, union`

| Sampled Entity | Type | Line |
|---|---|---:|
| `wp16 = circle(...)` | `profile` | 17 |
| `wp19 = Workplane(...)` | `workplane` | 20 |
| `wp18 = union(...)` | `solid` | 19 |
| `wp2 = splineApprox(...)` | `path` | 3 |
| `added material` | `material_region` | 10 |

| Relation | Support | Evidence |
|---|---|---|
| `has_path_tangent` | `missing_needed` | needed for sweep path tangent questions |
| `input_to` | `current` | wp2 = splineApprox(...) -> wp6 = sweep(...) |
| `after` | `current` | wp16 = circle(...) -> wp14 = union(...) |
| `located_on` | `spec_only` | wp16 = circle(...) -> wp15 = Workplane(...) |
| `has_profile_geometry` | `missing_needed` | area/perimeter/centroid/bbox/edge-count extraction |
| `input_to` | `current` | wp16 = circle(...) -> wp17 = extrude(...) |
| `used_by` | `spec_only` | wp16 = circle(...) -> wp17 = extrude(...) |
| `after` | `current` | wp18 = union(...) -> wp17 = extrude(...) |
| `combines` | `spec_only` | wp18 = union(...) -> wp18 = union(...) |
| `adds_material_to` | `spec_only` | wp18 = union(...) -> wp18 = union(...) |

Missing/necessary relation families: `has_material_region_geometry`, `has_path_tangent`, `has_profile_geometry`, `has_sketch_center`, `has_workplane_frame`, `nearest_point_on_path`

### `src_ba38136d03fe7cbc`

- Path: `CADEvolve-P/ShapeNet-P/02924116+dd21b1599951d4bcb84877c61813ddb3+models+model_normalized+r09+s95+t170+p95+k00/source_cadquery.py`
- Lines: `28`
- Visible ops: `Workplane, append, box, center, close, cos, cutBlind, cutThruAll, faces, polyline, rect, sin, workplane`

| Sampled Entity | Type | Line |
|---|---|---:|
| `body = rect(...)` | `profile` | 27 |
| `body = workplane(...)` | `workplane` | 27 |
| `body = faces(...)` | `selector` | 20 |
| `face >X` | `face` | 27 |
| `body = box(...)` | `solid` | 9 |

| Relation | Support | Evidence |
|---|---|---|
| `created_by` | `current` | body = box(...) -> body = box(...) |
| `has_material_region_geometry` | `missing_needed` | added-material geometry |
| `has_measurement` | `current` | body = box(...) -> volume bbox topology delta |
| `has_centroid` | `spec_only` | body = box(...) -> feature centroid |
| `before` | `current` | body = box(...) -> body = workplane(...) |
| `before` | `current` | body = box(...) -> body = polyline(...) |
| `before` | `current` | body = box(...) -> body = cutThruAll(...) |
| `input_to` | `current` | body = faces(...) -> body = cutThruAll(...) |
| `selected_by` | `current` | face >X -> body = faces(...) |
| `after` | `current` | body = workplane(...) -> body = cutBlind(...) |

Missing/necessary relation families: `has_material_region_geometry`, `has_profile_application_effect`, `has_profile_geometry`, `has_sketch_center`, `has_stable_face_id`, `has_void_region_geometry`, `same_selected_face_as`

### `src_f795fa559cb38da1`

- Path: `CADEvolve-C/CADEvolve-C-core/ArrayBossHelixWire__03_25_emitted_centered_scaled_binarized/source_cadquery.py`
- Lines: `44`
- Visible ops: `Plane, Vector, Workplane, circle, extrude, moveTo, splineApprox, sweep, union`

| Sampled Entity | Type | Line |
|---|---|---:|
| `wp16 = circle(...)` | `profile` | 17 |
| `wp23 = Workplane(...)` | `workplane` | 24 |
| `wp6 = sweep(...)` | `solid` | 7 |
| `wp4 = moveTo(...)` | `path` | 5 |
| `added material` | `material_region` | 18 |

| Relation | Support | Evidence |
|---|---|---|
| `has_path_tangent` | `missing_needed` | needed for sweep path tangent questions |
| `input_to` | `current` | wp4 = moveTo(...) -> wp5 = circle(...) |
| `uses_profile` | `spec_only` | wp6 = sweep(...) -> wp5 = circle(...) |
| `created_by` | `current` | wp6 = sweep(...) -> wp6 = sweep(...) |
| `has_material_region_geometry` | `missing_needed` | added-material geometry |
| `has_measurement` | `current` | wp6 = sweep(...) -> volume bbox topology delta |
| `has_centroid` | `spec_only` | wp6 = sweep(...) -> feature centroid |
| `input_to` | `current` | wp4 = moveTo(...) -> wp6 = sweep(...) |
| `before` | `current` | wp6 = sweep(...) -> wp7 = Workplane(...) |
| `before` | `current` | wp6 = sweep(...) -> wp8 = circle(...) |

Missing/necessary relation families: `has_material_region_geometry`, `has_path_tangent`, `has_profile_geometry`, `has_sketch_center`, `has_workplane_frame`, `nearest_point_on_path`

### `src_bb1d614881c83f67`

- Path: `CADEvolve-P/ShapeNet-P/02924116+dc9c640221f58021c08550bf6ec9e732+models+model_normalized+r09+s75+t170+p95+k00/source_cadquery.py`
- Lines: `38`
- Visible ops: `Workplane, append, box, center, close, cos, cutBlind, cutThruAll, faces, polyline, rect, sin, workplane`

| Sampled Entity | Type | Line |
|---|---|---:|
| `base = polyline(...)` | `profile` | 25 |
| `base = workplane(...)` | `workplane` | 25 |
| `base = faces(...)` | `selector` | 27 |
| `face >X` | `face` | 36 |
| `base = box(...)` | `solid` | 10 |

| Relation | Support | Evidence |
|---|---|---|
| `created_by` | `current` | base = box(...) -> base = box(...) |
| `has_material_region_geometry` | `missing_needed` | added-material geometry |
| `has_measurement` | `current` | base = box(...) -> volume bbox topology delta |
| `has_centroid` | `spec_only` | base = box(...) -> feature centroid |
| `after` | `current` | base = workplane(...) -> base = box(...) |
| `before` | `current` | base = box(...) -> base = workplane(...) |
| `after` | `current` | base = polyline(...) -> base = box(...) |
| `before` | `current` | base = box(...) -> base = polyline(...) |
| `located_on` | `spec_only` | base = polyline(...) -> base = workplane(...) |
| `has_profile_geometry` | `missing_needed` | area/perimeter/centroid/bbox/edge-count extraction |

Missing/necessary relation families: `has_material_region_geometry`, `has_profile_application_effect`, `has_profile_geometry`, `has_sketch_center`, `has_stable_face_id`, `has_void_region_geometry`, `same_selected_face_as`

### `src_50f6c097f59d60cb`

- Path: `CADEvolve-P/ShapeNet-P/02924116+e299444f1a4c7457fa9ee9b3a7eba069+models+model_normalized+r12+s90+t170+p95+k00/source_cadquery.py`
- Lines: `18`
- Visible ops: `Plane, Workplane, box, chamfer, edges, extrude, rect, union`

| Sampled Entity | Type | Line |
|---|---|---:|
| `tab = rect(...)` | `profile` | 16 |
| `tab = Workplane(...)` | `workplane` | 16 |
| `body = edges(...)` | `selector` | 10 |
| `body = union(...)` | `solid` | 17 |
| `added material` | `material_region` | 10 |

| Relation | Support | Evidence |
|---|---|---|
| `input_to` | `current` | body = edges(...) -> body = chamfer(...) |
| `after` | `current` | tab = Workplane(...) -> body = chamfer(...) |
| `after` | `current` | tab = rect(...) -> body = chamfer(...) |
| `located_on` | `spec_only` | tab = rect(...) -> tab = Workplane(...) |
| `has_profile_geometry` | `missing_needed` | area/perimeter/centroid/bbox/edge-count extraction |
| `used_by` | `spec_only` | tab = rect(...) -> tab = extrude(...) |
| `input_to` | `current` | body = edges(...) -> tab = extrude(...) |
| `after` | `current` | body = union(...) -> tab = extrude(...) |
| `input_to` | `current` | body = edges(...) -> body = union(...) |
| `combines` | `spec_only` | body = union(...) -> body = union(...) |

Missing/necessary relation families: `has_material_region_geometry`, `has_profile_geometry`, `has_sketch_center`, `has_stable_face_id`, `has_workplane_frame`, `same_selected_face_as`

### `src_07b5ee0b6d93a6cb`

- Path: `CADEvolve-C/CADEvolve-C-core/ArrayBossHelixWire__01_50_emitted_centered_scaled_binarized/source_cadquery.py`
- Lines: `40`
- Visible ops: `Plane, Vector, Workplane, circle, extrude, moveTo, splineApprox, sweep, union`

| Sampled Entity | Type | Line |
|---|---|---:|
| `wp20 = circle(...)` | `profile` | 21 |
| `wp7 = Workplane(...)` | `workplane` | 8 |
| `wp22 = union(...)` | `solid` | 23 |
| `wp4 = moveTo(...)` | `path` | 5 |
| `added material` | `material_region` | 22 |

| Relation | Support | Evidence |
|---|---|---|
| `has_path_tangent` | `missing_needed` | needed for sweep path tangent questions |
| `input_to` | `current` | wp4 = moveTo(...) -> wp5 = circle(...) |
| `input_to` | `current` | wp4 = moveTo(...) -> wp6 = sweep(...) |
| `after` | `current` | wp7 = Workplane(...) -> wp6 = sweep(...) |
| `has_normal` | `spec_only` | explicit cq.Plane normal |
| `has_workplane_frame` | `missing_needed` | frame extraction needed for profile/world geometry |
| `input_to` | `current` | wp7 = Workplane(...) -> wp8 = circle(...) |
| `after` | `current` | wp20 = circle(...) -> wp18 = union(...) |
| `located_on` | `spec_only` | wp20 = circle(...) -> wp19 = Workplane(...) |
| `has_profile_geometry` | `missing_needed` | area/perimeter/centroid/bbox/edge-count extraction |

Missing/necessary relation families: `has_material_region_geometry`, `has_path_tangent`, `has_profile_geometry`, `has_sketch_center`, `has_workplane_frame`, `nearest_point_on_path`

### `src_76925f7c6dc8a7c0`

- Path: `CADEvolve-P/ShapeNet-P/02924116+e0275ff6dfb3de5ae550942ea36e5443+models+model_normalized+r20+s80+t170+p95+k00/source_cadquery.py`
- Lines: `11`
- Visible ops: `Workplane, box, center, edges, extrude, faces, fillet, rect, union, workplane`

| Sampled Entity | Type | Line |
|---|---|---:|
| `body = box(...)` | `solid` | 6 |
| `added material` | `material_region` | 6 |
| `volume bbox topology delta` | `measurement` | 6 |
| `parameter `a` used by result` | `parameter` | 11 |
| `result = reduce(...)` | `operation` | 11 |

| Relation | Support | Evidence |
|---|---|---|
| `created_by` | `current` | body = box(...) -> body = box(...) |
| `has_material_region_geometry` | `missing_needed` | added-material geometry |
| `has_measurement` | `current` | body = box(...) -> volume bbox topology delta |
| `has_centroid` | `spec_only` | body = box(...) -> feature centroid |
| `input_to` | `current` | body = box(...) -> result = reduce(...) |
| `parameter_of` | `current` | parameter `a` used by result -> result = reduce(...) |

Missing/necessary relation families: `has_material_region_geometry`, `has_stable_face_id`, `same_selected_face_as`
