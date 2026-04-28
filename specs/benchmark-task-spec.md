# Benchmark Task Specification: CAD-QA

This document freezes the first CAD-QA task definitions. It is
implementation-facing: prompt generation, answer parsing, metrics, and schema
fields should be derivable from this file without guessing.

Threshold constants, topology tolerance, and numeric epsilon values belong in
`specs/label_rules.md`. This file defines task semantics, required fields, and
answer contracts.

## 1. Purpose

CAD-QA is a benchmark for reasoning over executable CadQuery scripts. The
benchmark asks whether a model can infer what the program does: which operations
exist, which selectors bind which entities, what intermediate geometry states
look like, how topology changes, whether points are inside the final solid, and
which feature last created, removed, or bounded a region of material.

Official labels come from precomputed trace and geometry metadata produced
offline. Labels must not come from model execution during evaluation. Public
closed-book prompts expose only code, task instructions, and allowed answer
formats; labels, diagnostics, kernel tolerances, and verifier outputs are
stored separately.

## 2. Common Assumptions

- Units are millimetres.
- Source programs are CadQuery Python scripts.
- Public prompts expose normalized code and task-specific references such as
  feature IDs, source lines, selector expressions, entity IDs, or coordinates.
- Official answers, raw labels, diagnostics, and failure reasons are stored
  outside prompt text.
- Closed-book models must not execute code or call CAD/verifier tools.
- Prompt generation must be a pure transformation of precomputed trace
  metadata. It must not recompute CadQuery labels.
- `feature_id` means a normalized operation step in the source operation graph,
  not necessarily human design intent.
- `step_index` is zero-based unless a prompt explicitly uses source line
  numbers.
- Topology labels are kernel-versioned and tolerance-versioned.

## 3. Shared Label Fields

All CAD-QA tasks may use these raw fields. Public task rows should include the
fields needed for evaluation and slicing, but prompts must not reveal answer
labels or diagnostics.

| Field | Type | Meaning |
| --- | --- | --- |
| `source_id` | string | Stable ID for the normalized CadQuery source file. |
| `trace_id` | string | Stable ID for the executed statement trace. |
| `feature_id` | string or null | Operation step targeted by the question, if any. |
| `step_index` | integer or null | Zero-based operation index targeted by the question, if any. |
| `operation` | string or null | CadQuery method or constructor name for the target step. |
| `volume_before` | number or null | Solid volume before the target step, in cubic millimetres. |
| `volume_after` | number or null | Solid volume after the target step, in cubic millimetres. |
| `signed_volume_delta` | number or null | `volume_after - volume_before`. |
| `bbox_before` | object or null | Axis-aligned bounding box before the step. |
| `bbox_after` | object or null | Axis-aligned bounding box after the step. |
| `topology_before` | object or null | Counts by entity type before the step. |
| `topology_after` | object or null | Counts by entity type after the step. |
| `selector_result` | object or null | Entity IDs and counts selected by a selector expression. |
| `point_classification` | string or null | `inside`, `outside`, `on_boundary`, or `ambiguous`. |
| `provenance_relation` | string or null | `created_by`, `modified_by`, `deleted_by`, `inherited_from`, `bounded_by`, or `ambiguous_or_merged`. |
| `answer_status` | string | `ok` or `invalid`. |
| `failure_reason` | string or null | Machine-readable failure reason. Null when labels are valid. |

Rows with unavailable required labels must either be excluded from the task
family or assigned the task-specific invalid answer where explicitly defined.

## 4. MVP Task Families

The MVP implementation targets exactly these task families:

- `operation_count`
- `selector_count`
- `bbox_after_step`
- `signed_volume_delta`
- `topology_count_after_step`
- `point_membership`
- `feature_provenance_choice`

CADEvolve-derived scripts are the primary source for released benchmark rows.
Synthetic primitives are allowed for golden tests, smoke tests, debugging, and
label edge cases; they should not dominate public benchmark counts.

### 4.1 `operation_count`

**Task purpose**

Count normalized CadQuery operations of a specified type in the script.

**Input shown to model**

- Normalized source code.
- Operation type to count, for example `extrude`, `cut`, `fillet`, `workplane`,
  `hole`, `box`, `loft`, or `sweep`.
- Exact answer format.

**Allowed answer**

A non-negative integer.

**Label derivation**

Count operation nodes in the parsed source operation graph whose normalized
`operation` equals the requested operation. Aliases must be normalized before
counting. Comments and dead text do not count.

**Primary metric**

Exact integer accuracy.

### 4.2 `selector_count`

**Task purpose**

Given a selector expression at a particular step, predict how many entities it
selects.

**Input shown to model**

- Normalized source code.
- Target source line or feature ID containing a selector expression.
- Entity type: `face`, `edge`, `vertex`, `wire`, or `solid`.
- Answer format.

**Allowed answer**

A non-negative integer, or `invalid` only for rows explicitly labeled
unanswerable.

**Label derivation**

Execute the script trace offline. Evaluate the selector against the target
intermediate workplane or shape under the recorded CadQuery/OCP environment.
The official label is the selected entity count after deduplication by the
dataset topology policy.

**Edge cases**

- Selectors after topology-changing operations may select different entities
  than visually similar selectors earlier in the script.
- `edges("|X")` means edges parallel to the selected axis under CadQuery
  selector semantics, not edges lying on the global X axis.

### 4.3 `bbox_after_step`

**Task purpose**

Predict an intermediate or final axis-aligned bounding box.

**Allowed answer**

Six finite numbers in millimetres:

```json
{"min": [x, y, z], "max": [x, y, z]}
```

**Label derivation**

Use the precomputed trace snapshot after the target step. Round only at export
time according to the numeric policy. Evaluation uses tolerance from
`label_rules.md`.

### 4.4 `signed_volume_delta`

**Task purpose**

Predict how much material a feature added or removed.

**Allowed answer**

A finite number in cubic millimetres. Positive means material was added,
negative means material was removed, and zero means no measurable volume change.

**Label derivation**

`volume_after - volume_before` using kernel-computed volumes for the target
step. Labels must store both raw volumes and the signed delta.

### 4.5 `topology_count_after_step`

**Task purpose**

Predict a topology count after a specified step: faces, edges, vertices, wires,
solids, planar faces, cylindrical faces, circular edges, or axis-parallel edges.

**Allowed answer**

A non-negative integer.

**Label derivation**

Use the topology snapshot after the target step. Geometry-type classifications
use the tolerance policy in `label_rules.md`.

### 4.6 `point_membership`

**Task purpose**

Classify whether a point is inside material, outside material, or on the
boundary at a target state.

**Allowed answers**

```text
inside
outside
on_boundary
ambiguous
```

**Label derivation**

Use the kernel point classifier with the dataset tolerance policy. Near-boundary
points inside the ambiguity band are labeled `ambiguous` unless the row is part
of an explicit boundary task.

### 4.7 `feature_provenance_choice`

**Task purpose**

Given a point or final entity, choose which feature most recently created,
removed, modified, inherited, or bounded the relevant material or topology.

**Allowed answer**

One `feature_id` from the provided choices, or `ambiguous_or_merged`.

**Label derivation**

Use trace-backed topology matching and operation histories where available.
When exact OpenCascade builder history is unavailable, use the documented
provenance approximation and store `provenance_confidence`. Low-confidence
many-to-many cases must not be forced into a single feature label.

## 5. Later Task Families

Reserved compatible task types:

- `workplane_state`
- `coordinate_frame`
- `intermediate_point_membership`
- `feature_first_added_point`
- `feature_last_removed_point`
- `selector_stability`
- `counterfactual_parameter`
- `counterfactual_operation_removal`
- `ambiguous_question_detection`
- `natural_language_explanation`

These should not be promoted into public v0.1 until their labels are stable,
their prompt formats are frozen, and their leakage behavior is audited.

## 6. Answer Formats

Every task row must define:

- `answer_type`
- `answer`
- optional `choices`
- optional `numeric_tolerance`
- optional `unit`
- `parse_policy`

Free-form prose is not a primary answer format for v0.1. Explanations may be
stored as optional auxiliary supervision, but official metrics grade structured
answers.

### Parse policies

`parse_policy` is a versioned grading contract. The MVP uses:

| Policy | Applies to | Rule |
| --- | --- | --- |
| `strict_integer_v1` | integer count tasks | Answer candidate must be exactly one non-negative base-10 integer. |
| `strict_enum_v1` | enum and choice tasks | Answer candidate must exactly match one allowed token after surrounding whitespace is stripped. |
| `strict_json_bbox_v1` | bounding boxes | Answer candidate must be JSON with `min` and `max` arrays of three finite numbers. |
| `numeric_4_sigfig_v1` | scalar numeric answers | Answer candidate must contain exactly one finite number and pass four-significant-figure tolerance. |

For `numeric_4_sigfig_v1`, compare against:

```text
effective_tolerance = max(row.numeric_tolerance or 0,
                          half_unit_of_fourth_significant_digit(answer))
```

For a nonzero canonical answer `x`:

```text
half_unit = 0.5 * 10 ** (floor(log10(abs(x))) - 3)
```

For canonical zero, use `row.numeric_tolerance` when present, otherwise the
task's absolute zero tolerance from `specs/label_rules.md`.

For `strict_json_bbox_v1`, apply the same four-significant-figure numeric rule
independently to each coordinate unless the row declares a stricter coordinate
tolerance. The exported answer may contain more precision; the parse policy
defines accepted model output precision.

## 7. Metrics

Report:

- exact-match accuracy for categorical and integer tasks;
- numeric accuracy under absolute and relative tolerances;
- invalid output rate;
- per-task accuracy;
- per-capability accuracy by `requires`;
- per-difficulty accuracy;
- split-specific generalization;
- near-boundary performance;
- provenance ambiguity performance.

Rows with `answer_status != "ok"` are excluded from normal metrics unless the
task explicitly includes invalid/ambiguous detection.
