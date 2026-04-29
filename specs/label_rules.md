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
spatial_distance_tolerance_mm = 1e-5
axis_parallel_tolerance_rad = 1e-6
bbox_region_overlap_tolerance_mm = 1e-6
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
| `graph_query` | Typed graph-query IR, resolved inputs, and resolution status. |
| `spatial_query` | Point, axis, centerline, or region query details. |
| `validity_result` | Operation or candidate validity probe result. |
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

## 10. Graph Query Rules

Graph-like QA labels must be derived from a stored query IR, not ad hoc prompt
text parsing. Query resolution must record:

- graph version;
- query type;
- target entity type;
- filters and ordinals;
- metric or attribute used;
- candidate IDs;
- resolved IDs;
- measured values used to choose the answer;
- resolution status.

Allowed graph metrics include scalar trace values such as signed volume delta,
gross swept/tool volume when available, net added or removed material, bounding
box deltas, topology deltas, axis length, centerline distance, and material mass
derived from an explicit density. A public row may use one of these metrics only
when every referenced feature/entity resolves uniquely and every metric source
has an `ok` label status.

Rows that rely on ordinal references such as `box #2` must store the numeric
ordinal in query IR and the exact resolved feature ID. If the ordinal, relation,
or target is ambiguous, the row must be excluded or labeled with an explicit
invalid/ambiguous answer.

## 11. Spatial Distance Rules

All spatial-distance labels are in millimetres and world coordinates unless the
task explicitly names a local workplane frame.

Point references must store their coordinate, source feature/entity, and frame.
Axis and centerline references must store origin, unit direction, source
feature/entity, extraction method, and confidence. Distances between skew or
parallel centerlines use the standard shortest line-to-line distance; component
distance questions must name the component axis.

Rows are invalid when a referenced point, axis, or centerline cannot be derived
stably, when multiple entities satisfy the reference without a deterministic
tie-break, or when the distance is below tolerance and the intended distinction
is ambiguous.

## 12. Bounding-Box Region Query Rules

Bounding-box-as-selector labels use an explicit world-coordinate region and one
of these predicates:

```text
inside
intersects
contains_centroid
added_material_in_region
removed_material_in_region
```

Entity queries may use exact geometry tests, entity centroids, or entity
bounding boxes, but the method must be stored. Feature material-region queries
must use conservative evidence from pre/post snapshots, provenance, boolean
intersections, or sampled material deltas. Bounding-box false positives must not
be emitted as exact public labels.

Answer lists must be sorted by stable feature/entity ID unless the prompt
explicitly requests another deterministic order.

## 13. Validity and Failure-Mode Rules

Validity labels must come from isolated execution probes under the recorded
environment. Store:

- target feature or candidate edit;
- prior state validity;
- post-probe validity;
- execution or kernel status;
- failure stage;
- failure type;
- searched parameter and range for threshold tasks;
- threshold value and search tolerance when applicable.

Allowed validity answers are `valid`, `invalid`, or
`ambiguous_or_unstable`. Failure-type answers must use a versioned enum.
Numeric threshold tasks, such as maximum valid fillet radius, require a bounded
search policy and either monotonic behavior over the search range or an
explicit statement that the row is diagnostic-only.

Kernel-unstable failures, timeout-sensitive failures, and failures that depend
on local machine resources must be quarantined from public metrics.

## 14. Invalid and Failure Handling

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
graph_query_ambiguous
spatial_reference_ambiguous
bbox_region_query_ambiguous
validity_probe_unstable
failure_threshold_unstable
kernel_error
non_finite_geometry_value
ambiguous_question
```

Rows with `answer_status != "ok"` must not be included in ordinary task
metrics. Invalid/ambiguous detection tasks may include them only when the
allowed answer set and scoring rule explicitly support invalid labels.

## 15. Golden Test Cases

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
- one deterministic graph query using an ordinal feature reference;
- one point-to-point distance and one centerline-to-centerline distance;
- one bounding-box region query with `inside` and one with `intersects`;
- one validity/failure-mode probe with a stable failure type.
