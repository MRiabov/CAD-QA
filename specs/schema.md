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
- Compute expensive geometry once per trace and derive multiple task rows from
  that trace.
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

`point_classification`:

```text
inside
outside
on_boundary
ambiguous
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
| `diagnostics` | object | Kernel and validation details. |

## 7. Public Task Row

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

## 8. Dataset Metadata File

The release metadata file must include:

- dataset version;
- row counts by split and task type;
- source manifest hash;
- generation config hash;
- code commit;
- label policy;
- execution environment;
- CADEvolve source metadata and license;
- known limitations;
- validation command outputs or report paths.

## 9. Split Manifest

The split manifest must record row IDs and group IDs used for leakage audits:

- `source_id`;
- `generator_id`;
- `source_subtree`;
- `normalized_source_code_hash`;
- `operation_signature_hash`;
- `topology_signature_hash`;
- `counterfactual_group_id`;
- `point_sampling_group_id`.

No group may appear in both train and held-out test splits unless the split
explicitly permits that leakage for a sanity check.

## 10. Export Layout

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

## 11. Validation Requirements

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
