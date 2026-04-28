# Dataset spec for CAD QA

Initial human suggestion:

"""
I have this idea for a dataset:
A dataset of QA pairs for CAD. Given a CadQuery script, answer questions like:
"In this point in space, which feature has last contributed to adding volume to it?"
"How much volume does a subtractive filet over all Z axes would have?"
"How much edges are there in a script?"
"How much many X-axis edges does the script have?"
"How big is the distance between point A and point B"?
"How much volume would this extrude add?"
"How points and edges would this extrude add?"

Are there any improvement to the dataset you may suggest?

Why I care: LLMs are stlll bad at understanding CAD. Perhaps QA dataset training would allow improvements on it.
"""

---
---
---

# LLM-expanded idea.

Yes. The core idea is good, but I would sharpen it into a benchmark for “mental execution of CAD programs,” not just generic CAD QA.

The main improvement: make the questions diagnostic. Each question should isolate a specific CAD reasoning capability, so model failures tell you what the model cannot do.

## Primary source: CADEvolve

CAD-QA should start from CADEvolve rather than a new synthetic corpus. The reason is practical: CADEvolve is already a large, normalized CadQuery source with executable programs, broad CadQuery operator coverage, and source-family structure that can be used for leakage-resistant evaluation.

Use the CADEvolve tiers this way:

```text
CADEvolve-P: executable CadQuery programs sampled from generators
CADEvolve-C: canonicalized executable scripts, preferred for normalized training/evaluation rows
CADEvolve-G: generator metadata and family context for grouping, not the default executable source
```

The paper describes CADEvolve as roughly 8k parametric generators expanded into roughly 1.3M scripts. That makes it a better first substrate than hand-written primitives: scripts are diverse enough for topology, boolean, transform, fillet/chamfer/shell, sweep, and loft questions, while still being regular enough to parse into source-step graphs.

Implementation policy:

```text
primary released rows: CADEvolve-derived
synthetic rows: golden tests, smoke tests, and label edge cases only
source execution: isolated workers with timeouts, because CADEvolve files are Python
source identity: preserve archive member path, normalized code hash, source subtree, generator/family ID when available
```

See also [docs/cad_qa_feature_provenance.md](../docs/cad_qa_feature_provenance.md) for the CADEvolve feature-provenance notes.

## 1. Split the dataset into reasoning tiers

Instead of one mixed QA dataset, define task families.

### Tier A — static code comprehension

These do not require executing geometry, only parsing the CadQuery script.

Examples:

```text
How many `.extrude()` operations are in the script?
Which operation creates the first solid body?
Which workplane is active before the final cut?
How many named parameters affect the hole diameter?
Which selector is used before the fillet operation?
```

Useful because this tests whether the model understands CadQuery syntax and operation ordering.

### Tier B — symbolic geometric reasoning

These require arithmetic and geometric inference, but not full B-Rep evaluation.

Examples:

```text
What is the volume added by this box/extrude/cylinder?
What is the distance between point A and point B?
What is the bounding box after this translation?
What is the center of mass of this primitive before subtraction?
Which faces are parallel to the XY plane?
```

This is probably the best early training signal. It teaches exactness.

### Tier C — topology reasoning

These require reasoning about faces, edges, vertices, loops, holes, and adjacency.

Examples:

```text
How many planar faces are present after this through-hole cut?
How many circular edges does the part contain?
Which faces share an edge with the top face?
How many vertical edges are created by this extrusion?
Does the fillet reduce, preserve, or increase the number of edges?
```

This is where LLMs are usually especially weak.

### Tier D — feature provenance / history

Your question:

```text
At point P, which feature last contributed volume?
```

This is very interesting, but also harder to generate labels for.

You could phrase it as:

```text
At coordinate (x, y, z), which operation most recently made this point part of the final solid?
At coordinate (x, y, z), which operation most recently removed material from this region?
Is point P inside material added by feature F?
Was point P ever inside the model before being removed?
```

This becomes a “CAD execution trace QA” dataset.

### Tier E — counterfactual CAD reasoning

This is likely the most valuable category.

Examples:

```text
If the hole radius changes from 2 mm to 3 mm, how does the final volume change?
If the extrusion height doubles, which bounding-box dimension changes?
If this fillet is removed, how many sharp edges remain?
If the cut is made blind instead of through-all, does it intersect the bottom face?
If object B is translated by +5 mm in X, do the two parts intersect?
```

This directly trains models to reason about edits, not only read existing scripts.

## 2. Add answer types beyond plain text

I would avoid only natural-language answers. Use typed answers.

For example:

```json
{
  "answer_type": "integer",
  "answer": 12
}
```

```json
{
  "answer_type": "float_mm3",
  "answer": 157.08,
  "tolerance": 0.01
}
```

```json
{
  "answer_type": "choice",
  "choices": ["extrude_1", "cut_1", "fillet_1", "none"],
  "answer": "cut_1"
}
```

```json
{
  "answer_type": "coordinate",
  "answer": [10.0, 5.0, 2.5],
  "tolerance": 0.001
}
```

This matters because CAD questions often need exact grading. Free-form answers will make evaluation noisy.

## 3. Represent every CadQuery operation as a named feature

Instead of giving anonymous scripts, instrument them:

```python
# feature_id: base_box
part = cq.Workplane("XY").box(20, 10, 5)

# feature_id: top_hole
part = part.faces(">Z").workplane().hole(3)

# feature_id: edge_fillet
part = part.edges("|Z").fillet(1)
```

Then ask questions over these feature IDs.

Examples:

```text
Which feature first created material at point (4, 2, 1)?
Which feature last modified the neighborhood of edge E_12?
Which feature removed the most volume?
Which feature changes the final bounding box?
```

This gives you provenance-style supervision.

## 4. Include “invalid assumption” questions

A strong CAD model should know when a question is impossible or underspecified.

Examples:

```text
How many X-axis edges does the script have?
```

This may be ambiguous unless you define whether you mean:

```text
edges parallel to X
edges lying on the X axis
edges whose local direction vector has positive X component
edges selected by CadQuery selector "|X"
```

So include answer classes like:

```json
{
  "answer_type": "invalid_or_ambiguous",
  "reason": "The phrase 'X-axis edge' is ambiguous; the script contains edges parallel to X, but none lying on the global X axis."
}
```

This is valuable because LLMs often hallucinate precise CAD answers from imprecise questions.

## 5. Add selector reasoning tasks

CadQuery uses selectors heavily, and models are poor at them.

Examples:

```text
Which faces are selected by faces(">Z")?
How many edges are selected by edges("|Z")?
Does faces("<X") select one face or multiple faces?
After this fillet, does edges("|Z") still select the same edges?
Which operation changes the result of the selector faces(">Z")?
```

This is important because selector semantics are central to CadQuery.

## 6. Add coordinate-frame and workplane reasoning

Many CAD errors come from misunderstanding local vs global frames.

Examples:

```text
What is the origin of the active workplane before the hole operation?
Is this point expressed in local workplane coordinates or global coordinates?
After `.transformed(offset=(10,0,0))`, where is the center of the next circle?
Which global axis is normal to the active workplane?
```

This is especially useful for LLM-to-CAD generation because most failures are frame mistakes.

## 7. Add “operation delta” questions

These are better than asking only about the final model.

Examples:

```text
How much volume did feature F add?
How much volume did feature F remove?
How many faces existed before and after feature F?
Which feature first introduced a curved surface?
Which feature caused the largest topology change?
Which feature changed the bounding box?
```

This trains causal understanding of operations.

A good schema:

```json
{
  "script_id": "part_000421",
  "feature_id": "cut_slot_2",
  "question": "How much volume did this feature remove?",
  "answer": 240.0,
  "unit": "mm^3",
  "tolerance": 0.01,
  "requires": ["boolean_reasoning", "volume_delta", "feature_trace"]
}
```

## 8. Include near-boundary geometric cases

These are important if the goal is genuine spatial reasoning.

Examples:

```text
Is point P inside the final solid?
```

Generate points in categories:

```text
deep_inside
deep_outside
near_face
near_edge
near_vertex
on_boundary
inside_removed_cut
inside_added_feature
inside_fillet_region
```

This prevents the model from only learning easy bounding-box heuristics.

## 9. Include intermediate-state questions

CadQuery scripts are procedural. Ask about the model after step N, not only at the end.

Examples:

```text
After feature 3, what is the bounding box?
After the first cut, is point P still inside the solid?
Before the fillet, how many sharp vertical edges exist?
After the shell operation, is the top face still present?
```

This teaches execution order.

## 10. Include multiple-choice and contrastive pairs

For training, open-ended QA is okay. For evaluation, contrastive QA is stronger.

Example:

```text
Which feature contributed material at point P?

A. base_box
B. mounting_boss
C. through_hole
D. edge_fillet
```

Better still, create counterfactual variants:

```text
Script A: hole radius = 2
Script B: hole radius = 3

Question: Which script has lower final volume?
```

Or:

```text
Only one parameter differs between these two scripts. Which geometric property changes?
```

This directly tests whether the model pays attention to the relevant line.

## 11. Add task labels for capability analysis

Every example should have metadata:

```json
{
  "requires": [
    "cadquery_syntax",
    "workplane_tracking",
    "boolean_subtraction",
    "volume_arithmetic",
    "selector_semantics"
  ],
  "difficulty": "medium",
  "numeric_tolerance": 0.01,
  "uses_approximation": false,
  "operation_count": 7,
  "has_fillet": true,
  "has_boolean_cut": true,
  "has_transform": false
}
```

Then you can report not just total accuracy, but:

```text
Volume arithmetic: 91%
Selector reasoning: 63%
Fillet topology: 38%
Coordinate-frame reasoning: 52%
Feature provenance: 29%
```

This is much more publishable.

## 12. Be careful with fillet questions

Your example:

```text
How much volume does a subtractive fillet over all Z axes have?
```

This is a good direction, but fillets are hard. Exact fillet volume can be nontrivial, especially with intersections, neighboring edges, tangent propagation, and kernel-specific behavior.

A better progression:

```text
Does this fillet add or remove volume?
Which edges are selected for the fillet?
What is the approximate volume removed by the fillet?
What is the exact volume difference before and after the fillet, as computed by the CAD kernel?
```

For labels, compute:

```python
volume_before = shape_before.val().Volume()
volume_after = shape_after.val().Volume()
delta = volume_after - volume_before
```

Then the answer does not require your own analytic formula.

## 13. Suggested dataset task families

A strong version of this dataset could include:

| Family              | Example                                          | Main skill          |
| ------------------- | ------------------------------------------------ | ------------------- |
| Syntax count        | How many extrudes?                               | CadQuery parsing    |
| Selector result     | How many faces does `faces(">Z")` select?        | Selector semantics  |
| Workplane state     | Where is the next sketch placed?                 | Coordinate tracking |
| Primitive volume    | How much volume does this extrusion add?         | Geometry arithmetic |
| Boolean delta       | How much volume does this cut remove?            | Solid reasoning     |
| Topology count      | How many edges/faces/vertices after operation N? | B-Rep topology      |
| Point membership    | Is point P inside the final solid?               | Spatial reasoning   |
| Feature provenance  | Which feature last affected point P?             | Execution tracing   |
| Counterfactual edit | What changes if radius becomes 3?                | Causal reasoning    |
| Ambiguity detection | Is the question answerable?                      | Robustness          |
| Assembly reasoning  | Do object A and B intersect?                     | Transform reasoning |
| Repair/edit QA      | What translation fixes the collision?            | CAD editing         |

## 14. Stronger example questions

Some refined versions of your examples:

```text
Given the CadQuery script, how many final edges are parallel to the global X axis?
```

```text
After feature `slot_cut`, how many faces does the solid have?
```

```text
What is the signed volume delta caused by feature `center_hole`?
```

```text
At point (12, 4, 2), is there material in the final solid?
```

```text
At point (12, 4, 2), which feature first added material there?
```

```text
At point (12, 4, 2), which feature last removed or added material there?
```

```text
Which operation changes the maximum Z value of the bounding box?
```

```text
If the extrusion height changes from 5 mm to 8 mm, what is the new bounding box?
```

```text
Which faces are affected by increasing the fillet radius from 1 mm to 2 mm?
```

```text
Does this script contain a workplane-frame error that causes the hole to be placed off-center?
```

## 15. The highest-value addition: generate execution traces

For every script, save intermediate CAD states:

```json
{
  "feature_id": "base_box",
  "operation": "box",
  "volume_before": 0.0,
  "volume_after": 1000.0,
  "faces_before": 0,
  "faces_after": 6,
  "bbox_after": [0, 0, 0, 20, 10, 5]
}
```

Then derive QA pairs from traces.

This gives you many question types automatically:

```text
Which feature added the most volume?
Which feature removed the most volume?
Which feature first introduced circular edges?
Which feature changed the bounding box?
Which feature increased face count the most?
```

The dataset becomes scalable and auditable.

## 16. Pin down the execution environment

The ground truth should not depend on an implicit local CAD stack. B-Rep topology, fillet behavior, boolean cleanup, and tolerance-sensitive classifications can change across CadQuery/OpenCascade versions.

Every generated artifact should record:

```json
{
  "python_version": "3.11.8",
  "cadquery_version": "2.5.2",
  "ocp_version": "7.8.1",
  "unit": "mm",
  "linear_tolerance": 1e-6,
  "angular_tolerance_rad": 1e-6,
  "kernel_tolerance_policy": "dataset_default_v1"
}
```

This makes reported results reproducible and makes topology-count labels defensible.

## 17. Store stable trace artifacts

Do not store only scalar labels. Save enough intermediate artifacts to audit or regenerate every answer.

For each operation, include:

```json
{
  "script_id": "part_000421",
  "feature_id": "slot_cut_2",
  "operation_index": 7,
  "operation_type": "cutBlind",
  "shape_brep_path_before": "shapes/part_000421/op_006.brep",
  "shape_brep_path_after": "shapes/part_000421/op_007.brep",
  "shape_hash_before": "sha256:...",
  "shape_hash_after": "sha256:...",
  "valid_before": true,
  "valid_after": true,
  "failure_reason": null,
  "volume_before": 1320.0,
  "volume_after": 1184.0,
  "net_volume_delta": -136.0
}
```

The `shape_hash` should be computed from a normalized export, not from object identity or file metadata.

For CADEvolve-derived rows, also store source provenance:

```json
{
  "source": "cadevolve",
  "source_tier": "CADEvolve-C",
  "source_subtree": "CADEvolve-C/CADEvolve-C-core",
  "archive_member_path": "CADEvolve-C/CADEvolve-C-core/...",
  "raw_source_hash": "sha256:...",
  "normalized_code_hash": "sha256:...",
  "generator_family_id": "..."
}
```

Public QA rows should not require local B-Rep files or CadQuery execution to read official labels. Heavy trace artifacts can live in an audit bundle referenced by stable IDs.

## 18. Define topological naming rules

Feature IDs should come from the normalized source-step graph, not from CAD-kernel topology ordering. This is a good fit for CADEvolve because many scripts are machine-generated, mostly single-assignment CadQuery programs where variables such as `wp13` can be parsed into an operation DAG with source lines, input variables, output variables, method names, and arguments.

Raw face IDs and edge IDs from the CAD kernel are not necessarily stable after booleans, fillets, chamfers, splits, or export/import cycles.

If questions refer to `face_12` or `edge_7`, define how those labels are created:

```text
derive final topology from the pinned CadQuery/OCP execution environment
sort faces by rounded centroid, normal, area, and surface type
sort edges by rounded midpoint, tangent direction, length, and curve type
break ties with a deterministic geometry hash
```

These `face_*` and `edge_*` labels are dataset artifact labels for asking questions about final topology. They are not provenance labels. Provenance should be attached by comparing pre/post states and, where possible, capturing OCC operation histories such as `Generated`, `Modified`, and `IsDeleted` before CadQuery discards builder objects.

Also mark when a topological entity is:

```text
created
deleted
split_from:<old_entity_id>
merged_from:[<old_entity_id>, ...]
modified_from:<old_entity_id>
unmatched
```

This prevents provenance QA from relying on unstable kernel-internal ordering.

## 19. Separate gross and net operation semantics

Questions like:

```text
How much volume did this extrude add?
```

need explicit semantics. For every material-changing operation, store separate quantities:

```json
{
  "gross_swept_volume": 500.0,
  "overlap_volume_with_previous_solid": 100.0,
  "net_added_volume": 400.0,
  "net_removed_volume": 0.0,
  "signed_final_volume_delta": 400.0
}
```

For subtractive operations:

```json
{
  "gross_tool_volume": 300.0,
  "intersection_volume_with_previous_solid": 240.0,
  "net_removed_volume": 240.0,
  "signed_final_volume_delta": -240.0
}
```

Then generate both question variants:

```text
What is the gross swept volume of feature F?
What is the signed final volume delta caused by feature F?
```

This avoids mixing analytic primitive volume with actual boolean effect.

## 20. Add invalidity and failure-mode QA

Real CAD agents need to predict when operations fail, not only answer questions about successful scripts.

Examples:

```text
Will this fillet operation succeed?
What is the largest valid fillet radius for the selected edges?
Will this shell thickness produce a valid solid?
Does this cut remove the entire object?
Does this loft self-intersect?
Does this boolean union produce one solid or multiple solids?
Is this sketch closed?
Is the resulting solid manifold?
```

Useful labels:

```json
{
  "valid_before": true,
  "valid_after": false,
  "failure_stage": "fillet",
  "failure_type": "radius_too_large",
  "max_valid_parameter": {"fillet_radius": 1.42},
  "recovery_hint": "reduce_radius"
}
```

This is especially important for edit and repair tasks.

## 21. Use leakage-resistant dataset splits

Random train/test split is too weak for generated CAD data. If train and test share the same generator template with only parameter changes, the benchmark may mostly measure template memorization.

Recommended splits:

```text
train
validation
test_random
test_generator_family_heldout
test_source_subtree_heldout
test_operation_sequence_heldout
test_topology_heldout
test_transform_heldout
test_parameter_range_heldout
test_near_boundary
test_invalid_operations
test_real_cadquery_scripts
```

Also store generator metadata:

```json
{
  "source": "cadevolve",
  "source_tier": "CADEvolve-C",
  "source_subtree": "CADEvolve-C/CADEvolve-C-core",
  "generator_family": "box_hole_fillet",
  "source_path_prefix": "CADEvolve-C/CADEvolve-C-core/...",
  "operation_sequence_signature": ["box", "hole", "hole", "fillet"],
  "topology_signature": {
    "num_solids": 1,
    "has_through_hole": true,
    "has_fillet": true
  },
  "parameter_bucket": "large_radius_small_clearance"
}
```

CADEvolve `G` metadata should be used for generator-family grouping when available. If it is not available for a row, fall back to conservative grouping by source subtree, source path prefix, normalized code hash, operation-sequence signature, object ID, and counterfactual group ID.

This lets evaluation report generalization across source families, operation order, topology, transforms, and parameter regimes.

## 22. Formalize graph-like QA

The graph-like questions in the human notes should become a first-class generation mode, not just hand-written examples.

Represent each script as a typed graph:

```text
nodes: features, sketches, profiles, faces, edges, vertices, solids, workplanes, parameters, materials
edges: created_by, consumed_by, modifies, before, after, selected_by, adjacent_to, parallel_to, coaxial_with, contained_in
attributes: volume_delta, bbox_delta, axis, radius, length, centroid, normal, material, density
```

Then represent a QA item with a query IR:

```json
{
  "query_type": "argmax",
  "entity": "feature",
  "metric": "net_added_volume",
  "filters": [
    {"relation": "after", "target": "second_feature_of_type:box"}
  ],
  "return": "feature_id"
}
```

Example natural-language questions derived from graph queries:

```text
Which feature after the second box added the most net volume?
How much volume did the cylinder selected by the third cut remove from box B?
What is the X distance between the first hole and the third hole?
Which of box(1,2,3) and box(4,5,6) changed the bounding box more along Y?
What feature has the largest positive volume delta, and what is its length?
```

This supports multi-hop questions where the model must identify the referenced entity before computing the answer.

## 23. Separate evaluation modes

Do not mix tasks that provide different information sources.

Suggested modes:

```text
code_only
code_plus_symbolic_trace
code_plus_brep_metadata
tool_allowed_execution
```

The same underlying question can appear in several modes, but scores should be reported separately. A model that mentally executes code is demonstrating a different capability from a model that reads the answer from a trace or runs CadQuery as a tool.

## 24. My recommended dataset name/framing

Possible names:

```text
CADTraceQA
FeatureTraceQA
CADExecQA
BRepQA
ParametricCAD-QA
CADReasonBench
```

The strongest framing:

> A benchmark for evaluating whether language models can mentally execute parametric CAD programs, track intermediate geometric state, and answer exact questions about topology, volume, feature provenance, and spatial relations.

That is cleaner than “QA pairs for CAD.”

## Bottom line

The idea is worth pursuing, but I would not make it a loose collection of CAD questions. I would structure it around execution trace reasoning:

```text
script → ordered features → intermediate solids → derived QA
```

The best additions are:

1. feature-level provenance questions;
2. before/after delta questions;
3. selector and workplane reasoning;
4. topology-count questions;
5. counterfactual parameter edits;
6. point-membership and near-boundary cases;
7. ambiguity/invalid-question detection;
8. code-only vs trace/tool-assisted evaluation modes;
9. pinned execution environment and stable trace artifacts;
10. leakage-resistant train/test splits;
11. invalidity and failure-mode questions;
12. graph-query representations for multi-hop CAD reasoning.

This would make the dataset much more useful for training and also more defensible as a research contribution.

# Additional human notes

Additional notes are graph-like reasoning:

* "How much volume does the feature that comes after the second box contribute to the volume?"
* "What is the length of the axis for the feature that has 8 parallel edges?"
* "Of boxes with parameters (1,2,3) and (4,5,6), which changed the bounding-box volume more?"
* "Of boxes with parameters (1,2,3) and (4,5,6), which has changed the bounding box more on the Y axis?"
* "How much volume did the cylinder A subtract from box B?"
* "How much X distance is between the first hole and the third hole in the script?"
* "What is the length of the feature that added the most volume?"


## A bit of diversity

* "Given this script we intend to add feature box(1,2,3)."
* "What is the weight added by feature A, provided the material has density 8.27 g/cm^3?"
* "What is the shortest distance between the centerlines of the first hole and the second cylinder in the script?"

### Bounding box as selectors

Not mentioned above: "in the bounding box of min=(1,2,3) and max=(4,5,6), which features have:
* Added/removed volume
* have at least one vertices
* How many vertices there are

Ad nauseam. And the other tasks bounding boxes may introduce.

## Adding graphs and graph-like QA generation
So the task here is twofold:
1. One-shot questions (covered before the "additional human notes")
2. Graph-like reasoning with figuring out what the user has asked, then proving it.
