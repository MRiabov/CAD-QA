# Multi-Hop CAD-QA Task Specification

This document describes the desired future benchmark track for complex
multi-hop CAD question answering. It is intentionally a product and research
specification, not an implementation contract. It defines what the benchmark
should test once the underlying graph, trace, and verifier infrastructure are
ready.

The current `graph_query` implementation in CAD-QA is a useful diagnostic
family over operation-level feature graphs. This document describes a more
ambitious sibling track: BrowseComp-style CAD questions where the model must
resolve uncertain references, compose several CAD facts, and converge on a
unique answer without being handed a fixed template.

## 1. Motivation

CAD-QA Core asks whether a model can mentally execute a CadQuery script and
answer local questions about operations, selectors, topology, bounding boxes,
volume deltas, point membership, and provenance.

Multi-Hop CAD-QA asks whether a model can answer questions such as:

```text
Which geometric feature has parameter A, moved by B along Y, and occurs after
operation D?

Which feature after the second box added the most net volume, and what is its
axis length?

Of the boxes with dimensions (1, 2, 3) and (4, 5, 6), which one changed the
bounding box more along Y?

Which cut removed material from the feature whose top face was selected before
the final fillet?
```

These questions are valuable because they test the kind of compositional CAD
reasoning a design agent needs: identifying entities under indirect
descriptions, tracking construction history, relating parameters to geometry,
and combining spatial, topological, and provenance facts.

## 2. Boundary With CAD-QA Core

Multi-Hop CAD-QA should be a separate benchmark track or task family, not a
rename of the existing `graph_query` rows.

CAD-QA Core:

- uses stable, implementation-facing task contracts;
- emphasizes deterministic labels over single scripts;
- includes current feature-level graph diagnostics;
- should avoid claiming BrowseComp-style high-uncertainty reasoning.

Multi-Hop CAD-QA:

- samples connected subgraphs from richer CAD knowledge graphs;
- composes constraints across multiple entity and relation types;
- uses natural-language questions generated from stored latent programs;
- obfuscates direct anchors when safe;
- rejects rows unless the answer is unique and verifier-backed;
- reports difficulty by graph structure, ambiguity, and required CAD concepts.

The two tracks should share source IDs, trace IDs, split policy, label policy,
and verifier infrastructure where possible.

## 3. Core Task Definition

Each example contains:

1. A normalized CadQuery script.
2. A hidden CAD knowledge graph derived from trace and geometry labels.
3. A hidden constraint record over that graph.
4. A natural-language question rendered from the constraint record.
5. A verifier-backed answer and resolved evidence chain.
6. Difficulty metadata and ambiguity diagnostics.

Public prompts should show the source code, the question, and the required
answer format. They should not expose the hidden constraint record, resolved
entity IDs, graph paths, diagnostic labels, or verifier outputs unless the
evaluation mode explicitly includes symbolic trace metadata.

## 4. Desired Graph Substrate

The graph should eventually include more than operation nodes.

Node types:

```text
source
feature
operation
parameter
workplane
sketch
profile
solid
face
edge
vertex
axis
centerline
material_region
selector
measurement
```

Relation types:

```text
before
after
immediately_before
immediately_after
input_to
created_by
modified_by
deleted_by
bounded_by
selected_by
located_on
parallel_to
perpendicular_to
coaxial_with
adjacent_to
contained_in
intersects
translated_by
rotated_by
scaled_by
parameter_of
has_measurement
adds_material_to
removes_material_from
```

Useful attributes:

```text
operation name
source line
parameter values
axis and frame
radius, diameter, length, height, width, depth
signed and absolute volume delta
bounding-box extents and deltas
topology counts and topology deltas
centroid, normal, centerline, and orientation
selector expression and selector result
provenance confidence
kernel stability status
```

The graph may be partially available in early versions, but every released row
must declare which node and relation families it depends on.

## 5. Prompt And Constraint Shape

The public task should not expose a query DSL. SailorFog-QA publishes ordinary
`question`/`answer` rows, and its difficulty comes from graph sampling and
obfuscated clues rather than from asking the model to read a formal language.
Multi-Hop CAD-QA should follow the same principle.

For the MVP, the default public prompt should be a natural-language constraint
checklist:

```text
Given the CadQuery script below, identify the feature that satisfies all of the
following constraints:

- It is a subtractive feature.
- It acts on a face selected by a side-face selector.
- That selected face is adjacent to the face used by the deepest blind cut.
- It creates the largest increase in circular edge count among matching
  features.
- It does not change the global bounding box.

Return exactly one feature ID.
```

Internally, each bullet should map to a hidden constraint record with evidence
and verifier hooks. This record is not a public task language. It is an audit
artifact used to regenerate the prompt, validate the answer, measure hops, and
detect ambiguity.

Conceptual hidden record:

```json
{
  "constraint_version": "cadqa_multihop_constraints_v1",
  "answer_type": "feature_id",
  "target_entity_type": "feature",
  "public_prompt_style": "constraint_checklist",
  "constraints": [
    {
      "public_text": "It acts on a face selected by a side-face selector.",
      "predicate": "selected_face.normal_axis in ['X', 'Y']",
      "hop_type": "G",
      "evidence_chain": [
        "feature --selected_by--> face",
        "face --has_normal--> axis"
      ]
    },
    {
      "public_text": "It does not change the global bounding box.",
      "predicate": "feature.measurements.bbox_delta == [0, 0, 0]",
      "hop_type": "G",
      "evidence_chain": [
        "feature --has_measurement--> bbox_delta"
      ]
    }
  ],
  "tie_break": "reject_unless_unique"
}
```

The exact schema can change. The required property is that every public clue is
recoverable from stored deterministic constraints and that the official answer
can be independently revalidated from graph and trace labels.

## 6. Generation Method

Generation should be answer-first and graph-grounded.

1. Build the richest available CAD knowledge graph for a script.
2. Sample an answer entity or scalar answer from stable graph labels.
3. Sample a connected subgraph that uniquely identifies or computes that
   answer.
4. Add distractor entities with overlapping attributes.
5. Render a natural-language question from the constraint record.
6. Optionally obfuscate direct anchors, such as replacing a feature ID with a
   description of its parameters, position, order, or provenance.
7. Resolve the constraints against the graph.
8. Reject the row unless the answer is unique, stable, and not leaked by the
   prompt.

This is different from enumerating a fixed list of hardcoded templates. The
template may render language, but the task structure should come from sampled
graph constraints and verifier-backed uniqueness checks.

## 7. Obfuscation Policy

Obfuscation should increase reasoning difficulty without making labels vague.

Allowed obfuscations:

- Replace feature IDs with operation descriptions.
- Replace exact operation order with ordinal or relative references.
- Replace exact parameter values with safe ranges or comparisons.
- Refer to a selector result rather than naming the selected entity.
- Refer to a spatial relation rather than naming a face, edge, or solid.
- Refer to a topology or volume change rather than naming an operation.

Disallowed obfuscations:

- Vague wording that can describe multiple graph entities.
- Hidden references that require external world knowledge.
- Ambiguous units or coordinate frames.
- Qualitative phrases where no deterministic threshold is stored.
- Questions whose answer depends on human design intent rather than trace
  labels.

Every obfuscated clue must map back to a concrete graph predicate, threshold,
or relation in the hidden constraint record.

## 8. Task Families

### 8.1 Entity Identification

Identify a feature, face, edge, vertex, workplane, selector, axis, or material
region from a composed description.

Example:

```text
Which feature has the largest positive volume delta among operations after the
second box?
```

### 8.2 Attribute Lookup After Resolution

First resolve an entity, then return one of its attributes.

Example:

```text
What is the axis length of the feature that added the most volume?
```

### 8.3 Comparative Reasoning

Resolve two or more entities, compute comparable attributes, and choose or
return the comparison result.

Example:

```text
Which of the two boxes with parameter triples (1, 2, 3) and (4, 5, 6) changed
the bounding box more along Y?
```

### 8.4 Relation Existence

Determine whether a composed relation holds between two resolved entities.

Example:

```text
Did the feature selected before the final fillet remove material from the
solid created by the first extrusion?
```

### 8.5 Chain Completion

Follow a relation path and return the final entity or value.

Example:

```text
Which cut modified the face selected by the workplane operation immediately
after the first cylindrical feature?
```

### 8.6 Spatial-Graph Reasoning

Combine graph references with point, axis, centerline, or region measurements.

Example:

```text
What is the shortest distance between the centerline of the first through-hole
and the cylinder that removed the most volume?
```

### 8.7 Ambiguity Detection

Detect when a natural-language question is under-specified or maps to multiple
valid answers.

Example:

```text
Which small hole is closest to the box?
```

This family is optional but important. It prevents the benchmark from teaching
models to invent a unique answer when the CAD graph does not support one.

## 9. Answer Formats

Allowed answer types:

```text
feature_id
entity_id
integer
number
coordinate
axis_id
enum
json
invalid_or_ambiguous
```

Numeric answers must include units and tolerance. Entity answers must be stable
under the dataset's entity-ID policy. Multi-part answers should use structured
JSON only when all fields are independently validated.

## 10. Difficulty Metadata

Each row should record measurable difficulty fields:

- number of graph nodes in the hidden subgraph;
- number of relation hops in the shortest evidence chain;
- number of static/text-derived hops;
- number of geometry/trace-derived hops;
- static-hop ratio;
- number of distractor entities;
- number of entity types involved;
- number of relation types involved;
- whether obfuscation was used;
- whether comparison or aggregation is required;
- whether spatial geometry, topology, provenance, or selector semantics are
  required;
- whether the row is code-only, trace-assisted, or tool-allowed;
- ambiguity margin between the correct answer and nearest distractor.

Suggested public difficulty buckets:

```text
mhqa_level_1_direct_0_1_hops
mhqa_level_2_bridge_2_hops
mhqa_level_3_complex_4_5_hops
mhqa_level_4_hard_6_8_hops
mhqa_level_5_extreme_9_10_hops
```

Level 1 and Level 2 rows are useful for curriculum, debugging, and calibration,
but they are not the main research target. Level 3 is the minimum useful
release difficulty for Multi-Hop CAD-QA. Level 4 should be difficult even for
strong closed-book models. Level 5 should be deliberately hard enough that
humans may struggle without tool support, which is part of the intended
research value.

## 11. Hop Composition Policy

Multi-Hop CAD-QA should not reward long questions whose reasoning chain is
mostly recoverable from source text. Operation order, variable names, literal
arguments, and direct call ordering are useful clues, but they should not carry
the benchmark.

Use this hop taxonomy:

```text
S = static/text-derived hop
G = geometry/trace-derived hop
```

Static/text-derived hops can be inferred from the source without executing CAD
geometry. Examples:

- operation order;
- literal argument values;
- variable assignment and reuse;
- direct call sequence;
- "feature A occurs before feature B";
- "the second box operation".

Geometry/trace-derived hops require trace, selector, topology, spatial, or
measurement labels. Examples:

- selector result;
- selected face, edge, vertex, or solid;
- face orientation, adjacency, or opposite-face relation;
- material added or removed by a feature;
- volume delta, bounding-box delta, centroid, centerline, or distance;
- topology delta, such as new faces or circular edges;
- profile perimeter, profile area, or sketch-derived geometry;
- feature provenance over material regions or topology entities.

Release-quality rows should satisfy:

- release difficulty should usually be Level 3 to Level 5;
- release rows should span 4-10 logical hops;
- Level 3 rows have 4-5 logical hops;
- Level 4 rows have 6-8 logical hops;
- Level 5 rows have 9-10 logical hops;
- rows with fewer than 3 logical hops are not useful as release rows for this
  track;
- no more than one third of counted hops may be static/text-derived;
- at least two thirds of counted hops should be geometry/trace-derived.

For example:

```json
{
  "logical_hops": 5,
  "static_hops": 1,
  "geometry_hops": 4,
  "static_hop_ratio": 0.2
}
```

Rows that exceed the static-hop ratio should be demoted to CAD-QA Core,
feature-level graph diagnostics, or static-code comprehension, even if the
question sounds complex.

## 12. Realistic Target Examples

The examples below are shaped by CADEvolve-style scripts with roughly 15-30
operations: repeated face selectors, workplanes, sketch profiles,
through-cuts, blind rectangular cuts, sweeps, extruded bosses, unions, and
custom planes.

### Example 1

Question:

```text
Which cut-through feature removes material from the face whose selected
profile has the largest increase in edge count, among cuts applied to non-top
faces?
```

Evidence chain:

```text
cut feature --selected_by--> face                  G
face --has_normal--> normal                        G
cut feature --uses_profile--> profile              G
profile --has_measurement(edge_count_delta)--> n   G
```

Hop count: 4 total, 0 S, 4 G.

### Example 2

Question:

```text
What is the volume removed by the blind rectangular cut whose sketch center
lies on the same selected face as the earlier star-shaped through-cut with the
largest perimeter?
```

Evidence chain:

```text
through-cut --uses_profile--> profile              G
profile --has_measurement(perimeter)--> value      G
through-cut --selected_by--> face                  G
blind-cut --selected_by--> same face               G
blind-cut --has_measurement(volume_delta)--> value G
```

Hop count: 5 total, 0 S, 5 G.

### Example 3

Question:

```text
Which union feature first combines a swept helix body with an extruded
circular boss whose workplane normal is not parallel to the sweep path tangent
at the nearest point?
```

Evidence chain:

```text
sweep feature --created_by--> swept solid          G
union --combines--> swept solid                    G
extrude feature --created_by--> boss solid         G
boss feature --located_on--> workplane normal      G
sweep path --nearest_tangent_to--> boss center     G
normal --not_parallel_to--> tangent                G
```

Hop count: 6 total, 0 S, 6 G.

### Example 4

Question:

```text
Which slot cut removes material from the side face whose post-cut topology
gains the same number of new edges as the opposite side face, but has the
smaller removed volume?
```

Evidence chain:

```text
slot cut --selected_by--> side face                G
side face --opposite_to--> side face               G
each face --has_measurement(edge_count_delta)--> n G
slot cut --removes_material_from--> material       G
material --has_measurement(volume)--> value        G
```

Hop count: 5 total, 0 S, 5 G.

### Example 5

Question:

```text
Which extruded circular boss is unioned after the swept body and has a
centroid closest to the material region added by the previous boss union?
```

Evidence chain:

```text
boss extrude --created_by--> boss solid            G
boss solid --input_to--> union                     G
union --after--> swept-body union                  S
previous union --adds_material_to--> material      G
boss solid --has_centroid--> centroid              G
centroid --distance_to--> material                 G
```

Hop count: 6 total, 1 S, 5 G.

### Example 6

Question:

```text
Which face selector feeds the cut that creates the most new circular edges
while preserving the global bounding box?
```

Evidence chain:

```text
selector --selected_by--> face                     G
face --input_to--> cut feature                     G
cut feature --has_measurement(circular_edge_delta) G
cut feature --has_measurement(bbox_delta)          G
```

Hop count: 4 total, 0 S, 4 G.

## 13. Evaluation Modes

Scores must not mix modes that expose different information.

```text
code_only
code_plus_symbolic_trace
code_plus_graph_summary
tool_allowed_execution
tool_allowed_search_over_trace
```

The primary closed-book benchmark should be `code_only`. Tool-allowed modes are
useful for CAD agents, but they measure search, tool use, and verifier
strategy in addition to internal CAD reasoning.

## 14. Rejection Rules

Reject or quarantine rows when:

- the source trace is incomplete;
- a referenced graph entity is unstable or missing;
- an obfuscated clue resolves to more than one candidate;
- aggregation has ties without a declared tie policy;
- the answer changes across repeated trace generation;
- entity IDs are not stable across the dataset export;
- the prompt leaks the answer through comments, diagnostics, or feature IDs;
- the question can be answered by a shallow single-token shortcut;
- more than one third of the evidence chain is static/text-derived;
- the evidence chain has fewer than 4 logical hops for release rows;
- the row depends on approximate provenance below the required confidence;
- the row depends on bounding-box overlap where exact geometry evidence is
  required.

## 15. Baselines

Report baselines that expose shortcuts:

- random among candidates;
- majority answer for enum tasks;
- operation-order heuristic;
- feature-ID lexical heuristic;
- nearest-source-line heuristic;
- static-code parameter parser;
- trace-oracle upper bound;
- graph-query oracle upper bound;
- closed-book LLM zero-shot;
- closed-book LLM few-shot;
- answer-only SFT;
- reasoning SFT when evidence chains are available.

For Level 3 rows, also report a cheap decomposition baseline that attempts to
turn the question into subquestions. This helps distinguish real graph
reasoning from memorized prompt patterns.

## 16. Dataset Split Rules

Multi-Hop CAD-QA must inherit CAD-QA leakage controls:

- source ID;
- generator ID;
- source subtree;
- operation signature;
- topology signature;
- counterfactual group;
- query graph family;
- answer entity family.

Questions generated from the same source graph or counterfactual group must
stay in the same split. Near-duplicate constraint records over the same source
family should also stay together.

## 17. MVP Prototype

A credible prototype should target 50-100 hand-audited generated rows, not a
large release.

Prototype scope:

- feature, operation, parameter, selector, and measurement nodes;
- `before`, `after`, `input_to`, `selected_by`, `created_by`,
  `modified_by`, `parameter_of`, and `has_measurement` relations;
- entity identification, attribute lookup, comparison, and relation-existence
  questions;
- Level 3 to Level 5 release rows, spanning 4-10 logical hops;
- static/text-derived hops at no more than one third of the chain;
- code-only prompts;
- stored hidden constraint records and evidence chains;
- strict uniqueness rejection.

Do not start with unrestricted natural-language question generation. Start with
structured hidden constraints, controlled checklist renderers, and verifier
rejection. Natural language diversity can be added after the labels and
difficulty controls are stable.

## 18. Non-Goals

This track does not require:

- open-ended CAD design generation;
- general web search;
- external mechanical-engineering knowledge;
- multimodal rendering as the default input;
- free-form explanations as official labels;
- replacing CAD-QA Core task families.

It should remain a CAD program reasoning benchmark. The hard part is not prose;
the hard part is making the answer require a real chain of trace-grounded CAD
facts.
