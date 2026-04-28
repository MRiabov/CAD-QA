# CAD-QA Label Rules

This file defines official label semantics and threshold policy for CAD-QA.
Public task answers must be derived from precomputed trace, topology, and
geometry fields using these rules, not from prompt text, heuristics, or
task-specific recomputation.

Raw values must always be stored alongside derived labels. This allows
validation, threshold audits, future relabeling, and task materialization from
one trace record.

## 1. Default Threshold Policy

Provisional defaults:

```text
linear_tolerance_mm = 1e-6
angular_tolerance_rad = 1e-6
volume_tolerance_abs_mm3 = 1e-6
volume_tolerance_ratio = 1e-8
bbox_tolerance_mm = 1e-6
point_boundary_tolerance_mm = 1e-5
selector_dedup_tolerance_mm = 1e-7
near_boundary_sampling_band_mm = 1e-3
```

Thresholds are part of the label policy. Each dataset version must store them
in metadata and include them in the config hash. Changing any threshold
requires a new dataset version or an explicit relabeling audit.

## 2. Raw Trace Inputs

Each trace-backed label record should contain these fields when applicable:

| Field | Meaning |
| --- | --- |
| `operation_graph_status` | `ok`, `partial`, or `failed`. |
| `execution_status` | `ok`, `timeout`, `source_error`, `kernel_error`, or `failed`. |
| `snapshot_status` | `ok`, `missing`, `non_solid`, `compound_only`, or `failed`. |
| `feature_id` | Stable operation ID targeted by the row. |
| `operation` | Normalized CadQuery operation name. |
| `volume_before` | Kernel volume before a feature. |
| `volume_after` | Kernel volume after a feature. |
| `bbox_before` | Axis-aligned bounding box before a feature. |
| `bbox_after` | Axis-aligned bounding box after a feature. |
| `topology_before` | Entity counts before a feature. |
| `topology_after` | Entity counts after a feature. |
| `selector_result` | Selector target entity IDs and counts. |
| `point_query` | Coordinate, target state, and classifier details. |
| `provenance` | Entity or point provenance relation details. |
| `answer_status` | `ok` when all task-required fields are valid; otherwise `invalid`. |
| `failure_reason` | Machine-readable invalid reason. |

## 3. Operation Count Rules

- Count parsed operation graph nodes, not textual substrings.
- Normalize common CadQuery spelling and fluent-call variants.
- Do not count imports, comments, function definitions, or helper calls unless
  the helper call itself is a CadQuery operation node in the normalized graph.
- Repeated operations inside static Python loops are counted according to the
  executed trace when loop expansion is available; otherwise the row must be
  excluded from trace-count tasks or labeled with an explicit static-count task
  type.

## 4. Volume Delta Rules

The official signed volume delta is:

```text
signed_volume_delta = volume_after - volume_before
```

Classification:

- `adds_material` if `signed_volume_delta > volume_epsilon`.
- `removes_material` if `signed_volume_delta < -volume_epsilon`.
- `no_measurable_change` otherwise.

Where:

```text
volume_epsilon = max(volume_tolerance_abs_mm3,
                    volume_tolerance_ratio * max(abs(volume_before), abs(volume_after), 1.0))
```

Fillet, chamfer, shell, clean, and boolean operations must use kernel-computed
pre/post volumes. Do not substitute analytic formulas unless the row is an
explicit symbolic-arithmetic task.

## 5. Bounding Box Rules

Bounding boxes are stored as:

```json
{"min": [x, y, z], "max": [x, y, z]}
```

All values are in world coordinates after the target state has been evaluated.
For local workplane tasks, the field name must say `local_bbox`.

Numeric answers are correct when every coordinate is within
`bbox_tolerance_mm`, unless a task row defines a looser tolerance for rounded
labels.

## 6. Topology Count Rules

Counts are derived from the target snapshot after shape cleanup policy has been
applied. The cleanup policy must be stored in metadata.

Default entity count keys:

```text
solid_count
shell_count
face_count
edge_count
vertex_count
wire_count
planar_face_count
cylindrical_face_count
circular_edge_count
x_parallel_edge_count
y_parallel_edge_count
z_parallel_edge_count
```

Axis-parallel classification uses the absolute angle between the entity tangent
or normal and the global axis. An entity is parallel when the angle is within
`angular_tolerance_rad` of 0 or pi.

## 7. Selector Rules

Selector labels must record:

- selector expression;
- entity type requested;
- target feature or state before selector evaluation;
- raw selected entity IDs;
- deduplicated entity IDs;
- selected count;
- CadQuery version and OCP version.

CadQuery selector semantics are authoritative. A natural-language phrase such
as "X-axis edge" is not equivalent to a selector unless the task defines it.

## 8. Point Membership Rules

Allowed labels:

```text
inside
outside
on_boundary
ambiguous
```

Use the kernel point classifier when available. A point within
`point_boundary_tolerance_mm` of a face, edge, or vertex is `on_boundary` for
boundary tasks and `ambiguous` for ordinary inside/outside tasks unless the
generation policy explicitly sampled it as a boundary case.

Near-boundary samples must store the nearest entity ID, nearest distance, and
classification status.

## 9. Provenance Rules

Allowed provenance relations:

```text
created_by
modified_by
deleted_by
inherited_from
bounded_by
ambiguous_or_merged
```

Feature provenance is many-to-many. A row may store multiple contributing
features, but a single-choice task may be emitted only when the primary answer
is stable under the label policy.

Default interpretation:

- `created_by`: the feature generated a final entity or material region.
- `modified_by`: the feature changed an existing entity into the final entity.
- `deleted_by`: the feature removed material or an earlier entity.
- `inherited_from`: the entity survived from a prior state under topology
  matching.
- `bounded_by`: the final entity exists at the boundary between multiple
  contributing features.
- `ambiguous_or_merged`: cleanup, unification, kernel history loss, or
  topology merging prevents a defensible single-source attribution.

OpenCascade builder history, when captured, wins over topology matching
heuristics. When builder history is unavailable, provenance rows must store the
matching method and confidence.

## 10. Invalid and Failure Handling

Common failure reasons:

```text
source_parse_error
source_exec_error
execution_timeout
missing_result_object
invalid_cadquery_type
non_solid_result
empty_shape
compound_without_solid
operation_graph_unsupported
trace_snapshot_missing
selector_eval_failed
point_classifier_failed
topology_matching_failed
provenance_low_confidence
kernel_error
non_finite_geometry_value
ambiguous_question
```

Rows with `answer_status != "ok"` must not be included in ordinary task
metrics. Invalid/ambiguous detection tasks may include them only when the
allowed answer set and scoring rule explicitly support invalid labels.

## 11. Golden Test Cases

The golden fixture suite should include:

- box volume and topology;
- extruded rectangle volume and bounding box;
- through-hole cut volume sign and selector counts;
- vertical-edge fillet signed volume delta;
- shell operation topology and volume change;
- translated workplane coordinate tracking;
- `faces(">Z")` and `edges("|Z")` selector cases;
- point inside, outside, boundary, and near-boundary cases;
- provenance of a cylindrical hole wall, circular edge, inherited side face,
  and fillet-modified edge.
