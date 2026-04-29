# CAD-QA Schema Specification

This file defines the canonical data model for CAD-QA. It is the source of
truth for future Pydantic models, JSON Schema export, JSONL writers, validators,
split audits, and dataset packaging.

CAD-QA uses three record layers:

- **Internal source records** describe normalized CadQuery source programs and
  source provenance.
- **Internal trace records** describe parsed operation graphs, isolated
  execution results, intermediate snapshots, topology, selector results, point
  labels, and provenance diagnostics.
- **Public task rows** are released for training and evaluation. They contain
  prompts, structured answers, code, labels, diagnostics, provenance, split
  metadata, and hashes.

Public rows must be self-contained for training and evaluation. Loading a
released JSONL row must not require CadQuery execution, OpenCascade, STEP/STL
files, render files, or local caches to read the official answer, labels,
diagnostics, provenance, or split assignment.

## 1. Design Principles

- Store raw geometry values and derived task answers separately.
- Compute cheap reusable trace labels once, and compute expensive geometry
  labels only for scheduled candidate descriptors.
- Use stable IDs and hashes.
- Include provenance and split metadata in every public row.
- Keep public rows code-plus-label by default; heavyweight artifacts belong in
  optional bundles.
- Add optional fields under `metadata` or versioned nested objects before
  changing stable top-level keys.

## 2. Common Types

All coordinates and distances are in millimetres. Volumes are in cubic
millimetres. Numeric fields must be finite unless explicitly nullable. JSON
object keys use `snake_case`.

### `BoundingBox`

| Field | Type | Required | Nullable | Meaning |
| --- | --- | --- | --- | --- |
| `min` | array of 3 numbers | yes | no | Minimum `[x, y, z]`. |
| `max` | array of 3 numbers | yes | no | Maximum `[x, y, z]`. |

### `TopologyCounts`

| Field | Type | Required | Nullable | Meaning |
| --- | --- | --- | --- | --- |
| `solid_count` | integer | yes | no | Number of solids. |
| `face_count` | integer | yes | no | Number of faces. |
| `edge_count` | integer | yes | no | Number of edges. |
| `vertex_count` | integer | yes | no | Number of vertices. |
| `wire_count` | integer | no | yes | Number of wires. |
| `planar_face_count` | integer | no | yes | Number of planar faces. |
| `cylindrical_face_count` | integer | no | yes | Number of cylindrical faces. |
| `circular_edge_count` | integer | no | yes | Number of circular edges. |
| `x_parallel_edge_count` | integer | no | yes | Number of X-parallel edges. |
| `y_parallel_edge_count` | integer | no | yes | Number of Y-parallel edges. |
| `z_parallel_edge_count` | integer | no | yes | Number of Z-parallel edges. |

### `LabelPolicy`

| Field | Type | Required | Default |
| --- | --- | --- | --- |
| `linear_tolerance_mm` | number | yes | `1e-6` |
| `angular_tolerance_rad` | number | yes | `1e-6` |
| `volume_tolerance_abs_mm3` | number | yes | `1e-6` |
| `volume_tolerance_ratio` | number | yes | `1e-8` |
| `bbox_tolerance_mm` | number | yes | `1e-6` |
| `point_boundary_tolerance_mm` | number | yes | `1e-5` |
| `selector_dedup_tolerance_mm` | number | yes | `1e-7` |

### `Hashes`

Hashes use lowercase SHA-256 strings with the prefix `sha256:`.

| Field | Meaning |
| --- | --- |
| `raw_source_code_hash` | Hash of source text as read. |
| `normalized_source_code_hash` | Hash of normalized source code. |
| `operation_graph_hash` | Hash of canonical operation graph. |
| `trace_hash` | Hash of operation graph, execution environment, and trace outputs. |
| `geometry_hash` | Hash of geometry snapshots and label policy. |
| `config_hash` | Hash of generation configuration. |
| `prompt_hash` | Hash of prompt template and prompt inputs. |

### Common Enums

`task_type`:

```text
operation_count
selector_count
bbox_after_step
signed_volume_delta
topology_count_after_step
point_membership
feature_provenance_choice
workplane_state
coordinate_frame
counterfactual_parameter
graph_query
spatial_distance
bbox_region_query
validity_failure_prediction
ambiguous_question_detection
```

`answer_type`:

```text
integer
number
bbox
choice
enum
coordinate
json
invalid_or_ambiguous
```

`spatial_predicate`:

```text
inside
intersects
contains_centroid
added_material_in_region
removed_material_in_region
```

`validity_status`:

```text
valid
invalid
ambiguous_or_unstable
```

`failure_type`:

```text
none
source_error
kernel_error
timeout
radius_too_large
self_intersection
empty_shape
non_solid_result
non_manifold
ambiguous_or_unstable
```

`point_classification`:

```text
inside
outside
on_boundary
```

`provenance_relation`:

```text
created_by
modified_by
deleted_by
inherited_from
bounded_by
ambiguous_or_merged
```

`split`:

```text
train
validation
test_random
test_generator_heldout
test_source_subtree_heldout
test_operation_heldout
test_topology_heldout
test_near_boundary
```

## 3. Source Record

Required fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `source_id` | string | Stable source ID. |
| `source` | string | `cadevolve` or `synthetic`. |
| `archive_member_path` | string or null | Original CADEvolve path. |
| `normalized_archive_member_path` | string or null | Normalized path. |
| `source_subtree` | string or null | CADEvolve subtree. |
| `generator_id` | string or null | Generator/family ID when derivable. |
| `license` | string or null | Source license metadata. |
| `raw_code` | string | Source code text. |
| `normalized_code` | string | Normalized code used in prompts. |
| `hashes` | object | Hashes object. |

## 4. Operation Node

Required fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `feature_id` | string | Stable operation ID, such as `wp13`. |
| `step_index` | integer | Zero-based operation order. |
| `source_line` | integer or null | Source line number. |
| `target` | string or null | Assigned variable. |
| `base` | string or null | Receiver/base variable. |
| `operation` | string | Normalized operation name. |
| `args_repr` | array | Normalized argument representation. |
| `input_features` | array | Feature IDs this operation depends on. |
| `status` | string | `ok`, `unsupported`, or `failed`. |

## 5. Trace Record

Required fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `trace_id` | string | Stable trace ID. |
| `source_id` | string | Source record ID. |
| `operation_graph_status` | string | Parse/extract status. |
| `execution_status` | string | Isolated execution status. |
| `result_variable` | string or null | Usually `result`. |
| `operation_nodes` | array | Operation nodes. |
| `snapshots` | array | Intermediate geometry snapshots. |
| `label_policy` | object | Label policy used. |
| `environment` | object | Python/CadQuery/OCP versions. |
| `hashes` | object | Hashes object. |
| `failure_reason` | string or null | Failure reason. |

Optional fields for later complex task families:

| Field | Type | Meaning |
| --- | --- | --- |
| `operation_graph` | object or null | Typed graph view derived from operation nodes, entities, parameters, and measured attributes. |
| `spatial_index` | object or null | Queryable indexes over points, axes, centerlines, topology entity bounds, and region evidence. |
| `validity_probes` | array | Operation or candidate-edit validity results from isolated execution probes. |
| `candidate_descriptors` | object or null | Private lightweight candidate descriptors by task type and stratum before scheduled labeling. |
| `sampling_manifest` | object or null | Private descriptor, scheduled-label, label-failure, and exported-row counts plus sampler configuration for this source. |

## 6. Snapshot Record

Required fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `snapshot_id` | string | Stable snapshot ID. |
| `feature_id` | string | Feature that produced this snapshot. |
| `step_index` | integer | Operation index. |
| `shape_status` | string | `ok`, `empty`, `non_solid`, `compound`, or `failed`. |
| `volume` | number or null | Solid volume. |
| `bbox` | object or null | Bounding box. |
| `topology` | object or null | TopologyCounts. |
| `entity_ids` | object or null | Stable IDs for faces/edges/vertices. |
| `workplane_state` | object or null | Active workplane origin, axes, normal, plane ID, and recovery status when available. |
| `coordinate_frame` | object or null | Transform from local workplane coordinates to world coordinates when available. |
| `deltas_from_previous` | object or null | Volume, bbox, topology, selector, workplane, and point-label deltas from the previous snapshot. |
| `diagnostics` | object | Kernel and validation details. |

## 7. Later Query Records

These records are optional until the corresponding complex task family is
implemented. They must live under internal trace metadata or public row
`labels`, never inside prompts unless a non-code-only evaluation mode declares
that symbolic metadata is visible.

### `CandidateDescriptorSummary`

Required fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `task_type` | string | Task type represented by the descriptor set. |
| `descriptor_count` | integer | Number of lightweight descriptors available before scheduled labeling. |
| `scheduled_count` | integer | Number of descriptors selected for labeling. |
| `label_success_count` | integer | Number of scheduled descriptors with valid labels. |
| `label_failure_count` | integer | Number of scheduled descriptors rejected by labeling, stability, ambiguity, or budget checks. |
| `exported_count` | integer | Number of scheduled labels rendered into public rows. |
| `strata_counts` | object | Counts by task-specific stratum, such as selector family or point sampling mode. |
| `sampler_config_hash` | string | Hash of the sampler configuration used for this pool. |
| `rng_seed` | integer or string | Seed used for deterministic descriptor scheduling. |

### `GraphQuery`

Required fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `query_id` | string | Stable query ID. |
| `query_type` | string | Query operation such as `argmax`, `compare`, `count`, `lookup`, or `aggregate`. |
| `entity_type` | string | Primary entity type, such as `feature`, `edge`, `face`, `axis`, or `material_region`. |
| `filters` | array | Deterministic graph filters with relation, target, and optional ordinal. |
| `metric` | string or null | Measured attribute such as `net_added_volume`, `bbox_volume_delta`, `axis_length`, or `distance_mm`. |
| `return_type` | string | Expected return shape: `feature_id`, `entity_id`, `number`, `choice`, `coordinate`, or `json`. |
| `resolved_inputs` | object | IDs and measured values used after query resolution. |
| `resolution_status` | string | `ok`, `empty`, `ambiguous`, or `unsupported`. |

### `SpatialReference`

Required fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `reference_id` | string | Stable reference ID. |
| `reference_type` | string | `point`, `axis`, `centerline`, `centroid`, `bbox`, or `entity`. |
| `feature_id` | string or null | Source feature that defines the reference. |
| `entity_id` | string or null | Topology entity that defines the reference. |
| `frame` | string | `world` or a named local workplane frame. |
| `point` | array or null | Point coordinate for point-like references. |
| `direction` | array or null | Unit direction for axis or centerline references. |
| `bbox` | object or null | BoundingBox for region references. |
| `fit_method` | string or null | Method used to derive an axis or centerline. |
| `confidence` | number or null | Derivation confidence when heuristic extraction is used. |

### `BBoxRegionQuery`

Required fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `region_id` | string | Stable region query ID. |
| `bbox` | object | World-coordinate spatial window. |
| `predicate` | string | Spatial predicate enum. |
| `target_entity_type` | string | `feature`, `face`, `edge`, `vertex`, `material_region`, or `point`. |
| `candidate_ids` | array | Deterministically ordered candidate feature/entity IDs. |
| `matched_ids` | array | Deterministically ordered answer IDs. |
| `count` | integer | Number of matched IDs. |
| `resolution_status` | string | `ok`, `ambiguous`, or `unsupported`. |

### `ValidityProbe`

Required fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `probe_id` | string | Stable probe ID. |
| `target_feature_id` | string or null | Operation or feature being probed. |
| `candidate_edit_id` | string or null | Candidate edit when the probe mutates source. |
| `valid_before` | boolean or null | Whether the prior state was valid. |
| `valid_after` | boolean | Whether the probed result is valid. |
| `validity_status` | string | Validity status enum. |
| `failure_stage` | string or null | Parse, trace, operation, cleanup, or export stage. |
| `failure_type` | string | Failure type enum. |
| `searched_parameter` | string or null | Parameter name for threshold-search probes. |
| `searched_range` | array or null | Numeric range searched for validity threshold. |
| `threshold_value` | number or null | Boundary value when a stable threshold exists. |
| `kernel_status` | string | Raw kernel/verifier status. |

## 8. Public Task Row

Required fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Stable row ID. |
| `dataset_version` | string | Dataset version. |
| `task_type` | string | Task enum. |
| `source_id` | string | Source record ID. |
| `trace_id` | string | Trace record ID. |
| `target_feature_id` | string or null | Target feature. |
| `split` | string | Split enum. |
| `prompt` | string | Public prompt. |
| `answer_type` | string | Answer type enum. |
| `answer` | any | Official structured answer. |
| `choices` | array or null | Allowed choices, when applicable. |
| `unit` | string or null | Unit. |
| `numeric_tolerance` | number or null | Tolerance for numeric grading. |
| `requires` | array | Capability tags. |
| `difficulty_tags` | array | Difficulty tags. |
| `labels` | object | Task-relevant labels. |
| `diagnostics` | object | Non-prompt diagnostics. |
| `provenance` | object | Source and grouping metadata. |
| `hashes` | object | Hashes object. |

Example:

```json
{
  "id": "cadqa_volume_delta_000001",
  "dataset_version": "cadqa-v0.1",
  "task_type": "signed_volume_delta",
  "source_id": "cadevolve_c_000001",
  "trace_id": "trace_000001",
  "target_feature_id": "wp13",
  "split": "train",
  "prompt": "Given the CadQuery script... What is the signed volume delta caused by feature wp13?",
  "answer_type": "number",
  "answer": -78.539816,
  "unit": "mm^3",
  "numeric_tolerance": 0.001,
  "requires": ["cadquery_syntax", "boolean_reasoning", "volume_delta"],
  "difficulty_tags": ["boolean_cut"],
  "labels": {
    "volume_before": 1000.0,
    "volume_after": 921.460184,
    "signed_volume_delta": -78.539816
  },
  "diagnostics": {
    "answer_status": "ok",
    "failure_reason": null
  },
  "provenance": {
    "source": "cadevolve",
    "generator_id": "abc_family_001",
    "operation_group_id": "opgrp_sha256_...",
    "counterfactual_group_id": null
  },
  "hashes": {
    "prompt_hash": "sha256:6666666666666666666666666666666666666666666666666666666666666666"
  }
}
```

## 9. Dataset Metadata File

The release metadata file must include:

- dataset version;
- row counts by split and task type;
- source manifest hash;
- generation config hash;
- sampler config hash;
- code commit;
- label policy;
- execution environment;
- CADEvolve source metadata and license;
- descriptor counts, scheduled-label counts, label-failure counts, and
  exported-row counts by task type and stratum;
- known limitations;
- validation command outputs or report paths.

## 10. Split Manifest

The split manifest must record row IDs and group IDs used for leakage audits:

- `source_id`;
- `generator_id`;
- `source_subtree`;
- `normalized_source_code_hash`;
- `operation_signature_hash`;
- `topology_signature_hash`;
- `counterfactual_group_id`;
- `point_sampling_group_id`.
- `graph_query_group_id`;
- `spatial_reference_group_id`;
- `validity_probe_group_id`.

No group may appear in both train and held-out test splits unless the split
explicitly permits that leakage for a sanity check.

## 11. Export Layout

Recommended layout:

```text
dataset/
  metadata.json
  split_manifest.json
  failure_manifest.jsonl
  jsonl/
    train.jsonl
    validation.jsonl
    test_random.jsonl
    test_generator_heldout.jsonl
    test_operation_heldout.jsonl
    test_topology_heldout.jsonl
    test_near_boundary.jsonl
  parquet/
    ...
  artifacts/
    manifest.json
```

## 12. Validation Requirements

Validation must check:

- every public row has a valid prompt, answer, split, and task type;
- answer type matches task type;
- numeric answers are finite;
- label status is valid for the task;
- prompt text does not contain hidden labels or diagnostics;
- hashes are well-formed;
- split groups do not leak across protected splits;
- row IDs are unique;
- public rows do not reference local cache paths.
