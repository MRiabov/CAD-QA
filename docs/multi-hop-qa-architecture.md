# Multi-Hop CAD-QA Architecture

This note describes the proposed generation architecture for the BrowseComp-like
Multi-Hop CAD-QA track in
[`specs/multi-hop-qa-task-spec.md`](../specs/multi-hop-qa-task-spec.md).

The current design is intentionally simple:

```text
CadQuery script
-> trace and typed ontology graph
-> answer-first target sampling
-> broad clue mining
-> candidate-count gates
-> deterministic text templates
-> checklist prompt
-> deterministic verifier and audit report
```

There is no public DSL and no required LLM generation step. The public question
is a natural-language checklist produced from typed ontology atoms by a
rule-based verbalizer. External models may still be used later for evaluation,
but they are not part of the trusted generation path.

## Design Goals

- Generate genuine-looking, obfuscated multi-hop questions over CadQuery code.
- Keep every accepted answer deterministic and verifier-backed.
- Make individual clues broad enough that no single clue acts like a direct
  reference.
- Keep public wording understandable from the shown script alone, including for
  small models that know CadQuery but not this benchmark's private ontology.
- Produce enough private structure to audit, regenerate, balance, and debug each
  row.
- Prefer boring, inspectable templates over clever surface variation.

## Non-Goals

- Do not expose a formal query language to benchmarked models.
- Do not ask an LLM to invent facts, choose the answer, or judge uniqueness.
- Do not accept rare one-off clues that identify the target by themselves.
- Do not use private ontology terms in public prompts unless grounded directly
  in visible CadQuery code.
- Do not optimize for paragraph naturalness before correctness, breadth, and
  auditability are solved.

## Core Artifacts

### Ontology Graph

The private graph is built from the normalized CadQuery script, trace snapshots,
and static parse information. It can be partial, but each row must declare which
families it relies on.

Useful graph families:

- operation nodes and source spans;
- temporal order between operations;
- operation semantics, such as additive, subtractive, transform, selector, or
  workplane-changing steps;
- selector usage, such as `.faces(">Z")`, `.edges("|Z")`, or `.vertices(...)`;
- parameter and expression usage;
- sketch and profile nodes from `.circle(...)`, `.rect(...)`, `.polyline(...)`,
  `.close()`, helper-returned point lists, and recoverable sketch chains;
- intrinsic profile geometry, such as area, perimeter, centroid, local bounding
  box, edge count, vertex count, circular segment count, and line segment count;
- volume and bounding-box deltas;
- topology deltas, such as face, edge, circular-edge, or vertex count changes;
- relation edges between operations, workplanes, profiles, selected entities,
  parameters, material regions, and derived geometry labels.

Profile metrics have two scopes:

- `profile_intrinsic`: measurements of the sketch/profile itself;
- `feature_application_effect`: measurements of what happened when a feature
  used the profile.

The generator should keep these scopes separate. For example, profile perimeter
belongs to `profile_intrinsic`, while edge-count delta after a cut belongs to
the cut feature's application effect.

### Hidden Query Program

The hidden query program is the private canonical row. It is not shown to
models.

```json
{
  "query_version": "cadqa_multihop_query_v1",
  "answer_type": "feature_id",
  "target_entity_type": "feature",
  "intermediate_entity_types": ["profile", "workplane", "face"],
  "public_prompt_style": "constraint_checklist",
  "target_id": "f17",
  "clauses": [],
  "projection_paths": [],
  "candidate_set_trace": [],
  "rejected_clues": [],
  "difficulty": {},
  "required_graph_families": []
}
```

The hidden program stores enough information to rerun the resolver, explain why
the row was accepted, and diagnose rejected alternatives.

### Public Prompt

The first public format should stay as a checklist:

```text
Given the CadQuery script, identify the feature that satisfies all of these
constraints:
- ...
- ...
- ...
Return exactly one feature ID.
```

Checklist prompts are less natural than paragraphs, but they are easier to
verify and audit. They also make it obvious which public sentence corresponds
to which private clause.

## Constraint Types

The task spec defines the explicit `constraint_type` enum:

```text
temporal
metric
topological
selector
provenance
spatial
comparative
parameter
operation_semantics
relation
```

Each mined clue must have one primary constraint type. The type is used for
coverage, balancing, template selection, and failure analysis.

## Pipeline

### 1. Build The Private Graph

For each source script:

- parse CadQuery call chains and source spans;
- identify feature-like operations and stable feature IDs;
- collect selector calls and the call chain they affect;
- collect parameter definitions and expression uses;
- extract sketch/profile chains and compute intrinsic profile geometry;
- attach trace-derived metrics and topology deltas when available;
- attach feature-application metrics to the operation that used each profile;
- emit typed nodes and relations with label-source pointers.

Rows should be rejected when a required graph family is missing or unstable.

### 2. Sample The Answer First

Sample the target before writing any question. Initial answer types should be:

- `feature_id`;
- `number`;
- `enum`.

For the first generator spike, focus on `feature_id`. Balance target sampling
by operation family, script family, constraint mix, and difficulty bucket.

### 3. Mine Atomic Ontology Clues

For a sampled target, enumerate true ontology atoms. Each atom is an internal
structured fact, not public prose.

Example atom:

```json
{
  "clause_id": "c03",
  "constraint_type": "selector",
  "target_entity_type": "feature",
  "relation": "uses_selector",
  "arguments": {
    "selector": ".faces(\">Z\")",
    "call_context": "workplane creation"
  },
  "candidate_count": 12,
  "label_sources": ["static_call_chain", "trace.selector_table"]
}
```

The atom should be evaluated against all candidates before it is verbalized.

Non-feature atoms must also declare how they project to the requested answer
type. A profile clue in a `feature_id` question is not enough by itself; it must
include a path such as:

```text
feature --uses_profile--> profile
profile --has_measurement(profile_intrinsic.perimeter)--> value
```

or:

```text
feature --uses_profile--> profile
profile --used_by--> feature
feature --has_measurement(feature_application_effect.edge_count_delta)--> value
```

This allows prompts to reason through profiles, faces, workplanes, and material
regions while still returning a stable feature ID.

### 4. Apply Atomic Clue Gates

Any single clue that narrows too much is a leak. Apply these gates before
composing the question:

- `min_individual_candidate_count = 5`;
- `min_temporal_side_range = 5` for before/after clues;
- reject `immediately_before`, `immediately_after`, `final_step`, and
  `only_feature_with_X` unless the candidate count still passes;
- reject rare selectors or one-off provenance facts when they identify fewer
  than five candidates;
- reject clues whose target type is incompatible with the requested answer.
- reject non-feature clues that do not have a stable projection path to the
  requested answer type.

This intentionally discards many correct facts. A clue can be true and still be
bad for the hard track if it selects one or two entities by itself.

### 5. Verbalize With Rule Templates

The verbalizer maps accepted atoms to public clue text. It is deterministic:

```text
(constraint_type, relation, target_entity_type, argument_shape)
-> template family
-> grounded public sentence
```

The template has access only to safe public fields, such as visible CadQuery
calls, source-local variable names, operation classes, ranges, and broad
relations.

Good public clue wording is grounded in visible code:

- "uses `.faces(\">Z\")` before creating a workplane";
- "is made by a `.cutBlind(...)` call that removes material";
- "uses a radius expression also used by another circular sketch operation";
- "uses the closed point list later passed to `.polyline(...)`";
- "uses the profile with the largest computed perimeter among the repeated
  `.polyline(...).close()` cuts";
- "uses a profile whose resulting cut creates the largest edge-count increase";
- "comes after at least five earlier feature operations";
- "changes the final object's volume while leaving its outer bounding box
  unchanged";
- "is joined into the running object by a later `.union(...)` call".

Avoid ontology-only wording:

- "has a bounding-box delta measurement";
- "feeds the accumulated-body union";
- "creates a material region";
- "is associated with the selected CadEvolve source script";
- "has provenance from the profile node".

If a concept cannot be explained using script-visible language, that clue
should not be public.

### 6. Search For A Clause Set

After atomic gates, search combinations of broad clues.

The accepted set must satisfy:

- each individual clue passes the breadth gate;
- partial combinations leave plausible distractors;
- the full combination resolves to exactly one target;
- every non-feature clue has a projection path to the requested target type;
- the set covers at least two constraint types;
- the hidden evidence chain is long enough for the target difficulty bucket;
- no clue contains a private ID or private diagnostic field.

The search can be deterministic with a seed. Tie-breaking should prefer broader
individual clues, stronger graph evidence, and better constraint-type coverage.

### 7. Render The Checklist

The renderer only assembles text from approved clauses. It does not invent new
facts.

Required output:

```json
{
  "question": "Given the CadQuery script, identify ...",
  "answer_format": "feature_id",
  "clue_map": [
    {
      "clause_id": "c01",
      "public_text": "..."
    }
  ]
}
```

The `clue_map` is required so auditors can trace every public sentence back to
the ontology atom and candidate-count gate that allowed it.

### 8. Re-Resolve And Audit

Run the deterministic resolver after rendering.

Reject if:

- the full clue set returns zero or multiple candidates;
- any clue cannot be evaluated;
- any clue's individual candidate count is below the configured threshold;
- a temporal clue violates the side-range threshold;
- the public text includes private IDs or banned ontology jargon;
- the clue set mixes incompatible target types;
- the answer changes after rendering.

Record rejected clues and rejected clause sets. These failure records are useful
for improving graph coverage and template wording.

### 9. Materialize Rows

Accepted rows should produce:

- public JSONL row;
- private hidden query JSONL row;
- candidate-set trace;
- rejected-clue manifest;
- difficulty report;
- source-family and constraint-type coverage report.

## Architecture Components

### Graph Builder

Creates typed nodes, relations, source spans, label-source pointers, and
stability flags from each script and trace artifact.

### Sketch/Profile Extractor

Builds sketch and profile nodes from recoverable CadQuery chains and bounded
helper outputs. It computes local and world profile geometry, including area,
perimeter, centroid, bounding boxes, edge count, vertex count, and primitive
segment counts.

The extractor must record whether a measurement is `profile_intrinsic` or
`feature_application_effect`.

### Target Sampler

Selects answer-first targets under quotas for answer type, operation family,
source family, and constraint mix.

### Atom Miner

Enumerates true structured clues for the sampled target. It does not write
public prose.

### Candidate Counter

Evaluates each atom against all candidate targets and records the candidate set
left by that atom alone. For non-feature atoms, counting is performed after
projecting the atom back to the requested target type.

### Gate Evaluator

Applies breadth, temporal side-range, wording-eligibility, target-type, and
label-stability gates. It also rejects non-feature clues without stable
projection paths.

### Rule-Based Verbalizer

Maps approved atoms to canonical public clue sentences. This is the core
wording component for the generation path.

### Clause Set Searcher

Combines broad clues until the full set uniquely identifies the answer while
preserving plausible distractors for partial sets.

### Checklist Renderer

Formats the public prompt and emits the `clue_map`.

### Verifier

Re-evaluates the hidden program and rendered clue set. It should return exact
failure reasons, such as:

- `empty_candidate_set`;
- `ambiguous_candidate_set`;
- `individual_clue_too_narrow`;
- `temporal_side_range_too_small`;
- `missing_label_family`;
- `unstable_label`;
- `unsupported_predicate`;
- `target_type_mismatch`;
- `prompt_leak_detected`;
- `public_wording_not_grounded`.

### Row Materializer

Writes public rows, private labels, rejection manifests, and coverage reports.

## Difficulty Accounting

Difficulty should be computed from graph and candidate-set properties, not
estimated from wording.

Suggested fields:

```json
{
  "constraint_type_counts": {
    "temporal": 1,
    "metric": 1,
    "selector": 1,
    "operation_semantics": 1
  },
  "individual_candidate_counts": {
    "c01": 11,
    "c02": 8,
    "c03": 6,
    "c04": 7
  },
  "min_individual_candidate_count": 6,
  "full_clause_candidate_count": 1,
  "min_temporal_side_range": 5,
  "partial_clause_min_candidate_count": 3,
  "shortest_evidence_hops": 5,
  "required_graph_families": ["selector", "metric", "temporal"]
}
```

External solver pass rates can be added later for release calibration, but they
should not be required for row correctness.

## Template Contract

Each template family should declare:

- supported `constraint_type`;
- supported relation names;
- supported target entity types;
- supported intermediate entity types;
- supported measurement scopes, such as `profile_intrinsic` or
  `feature_application_effect`;
- required public arguments;
- banned argument shapes;
- candidate-count requirements;
- required projection path shape for non-feature clues;
- examples of acceptable output;
- examples of rejected output.

Example:

```json
{
  "template_id": "selector.face_before_workplane.v1",
  "constraint_type": "selector",
  "relations": ["uses_selector_before_workplane"],
  "target_entity_types": ["feature"],
  "intermediate_entity_types": ["face", "workplane"],
  "measurement_scopes": [],
  "required_public_args": ["selector_literal"],
  "minimum_candidate_count": 5,
  "projection_path": "feature -> selected_by -> face -> located_on -> workplane",
  "text": "uses `{selector_literal}` before creating a workplane"
}
```

Templates should be versioned. Changing wording can change model behavior even
when the hidden predicate is unchanged.

## Experiments To Run

### Template Coverage Preview

Exercise every ontology node and relation family against one or two longer
CadEvolve scripts. Emit:

- accepted public clue examples;
- rejected clue examples with gate reasons;
- candidate counts for every clue;
- relation and parameter coverage summaries.

The current prototype lives under
[`experiments/multi_hop_qa_mock/`](../experiments/multi_hop_qa_mock/), especially
`build_comprehensive_ontology_preview.py` and
`preview/comprehensive_ontology_preview.md`.

### Candidate-Count Gate Sweep

Run the same sources with thresholds such as 3, 5, and 8.

Measure:

- yield;
- constraint-type imbalance;
- average candidate count per accepted clue;
- number of unique full clause sets;
- manual readability defects.

### Source-Family Coverage Audit

Sample additional random CadEvolve scripts and compare which templates still
produce valid public clues. This catches overfitting to one script shape, such
as repeated bosses, selector-heavy chains, or star/slot sketches.

### Wording Audit

Manually review generated prompts as if the reader has only:

- the CadQuery script;
- the public checklist;
- general programming/CAD knowledge.

Reject wording that depends on private benchmark terminology.

### Target-Type Compatibility Audit

Verify that every clue in a prompt can resolve to the requested answer type.
This should catch prompts that accidentally combine feature, face, vertex,
parameter, and profile clues without a clear shared target.

### Non-Feature Relation Gap Survey

Sample real CadEvolve scripts, choose mixed non-feature entities, and record
which relation opportunities are current, spec-only, or missing but necessary.
The current survey artifact is
[`experiments/multi_hop_qa_mock/preview/non_feature_relation_gap_survey.md`](../experiments/multi_hop_qa_mock/preview/non_feature_relation_gap_survey.md).

The first observed priority and complexity matrix is:

| Priority | Capability | Complexity | Why First | Enables |
|---|---|---|---|---|
| P0 | `has_profile_geometry` | M | Most non-feature questions need real profile facts, and this is mostly AST/CadQuery chain extraction. | Profile perimeter/area/centroid/bounds, profile comparisons, sketch-shape clues. |
| P0 | `has_workplane_frame` | M | Profile geometry is not useful without local-to-world frame, origin, axes, and normal. | Workplane-normal clues, profile world coordinates, selector-to-profile grounding. |
| P0 | `has_profile_application_effect` | M | Connects intrinsic profile facts to operation deltas; prevents fake `profile.edge_count_delta` labels. | "Profile whose cut creates..." and cut/extrude effect clues. |
| P0 | Profile projection paths | S | Required so non-feature clues resolve back to `feature_id` answers. | `feature -> uses_profile -> profile -> metric` rows. |
| P0 | Template and gate support for measurement scopes | S | The verbalizer must distinguish `profile_intrinsic` from `feature_application_effect`. | Public wording that is precise and auditable. |
| P1 | `has_stable_face_id` | H | Selector-rich scripts need face identity, but stable topology matching is harder than profile extraction. | Face-selector clues, same-face joins, non-top/side-face reasoning. |
| P1 | `same_selected_face_as` | M | Once face IDs exist, equality joins are cheap and unlock many multi-hop rows. | "same selected face as..." and repeated selector patterns. |
| P1 | `has_sketch_center` | S | Easy for circle/rect/polyline profiles after profile geometry exists. | Center-offset clues, positive/negative side clues, coordinate lookup rows. |
| P1 | `has_path_tangent` | M | Needed for sweep/helix questions; can start from source-defined spline points. | Sweep tangent, normal-vs-path, nearest-direction comparisons. |
| P1 | `nearest_point_on_path` | M | Pairs with path tangent and profile/solid centroids. | Closest boss to sweep path, tangent at nearest point. |
| P2 | `has_material_region_geometry` | H | High value but depends on robust boolean/provenance evidence. | Added-volume centroid/bbox/adjacency/intersection rows. |
| P2 | `has_void_region_geometry` | H | Similar to material regions, but for cuts and through-voids. | Removed-volume, through-cut void, cut-intersection rows. |
| P2 | `adjacent_to` / `opposite_to` over faces and regions | H | Requires stable B-rep identity and geometry relation checks. | Face adjacency, opposite side face, material-region adjacency. |
| P2 | `intersects` / `contained_in` over material and void regions | H | Needs exact or conservative region evidence, not AABB-only heuristics. | Region intersection, containment, through-void questions. |

P0 should be implemented before broad prompt generation. P1 makes the questions
look substantially more like the target benchmark. P2 is where the benchmark
starts depending on heavier B-rep and boolean-diff infrastructure.

## Main Risks

### Templates Become Too Mechanical

Checklist prompts will look templated. That is acceptable for the first
generation path. Naturalness can be improved later by adding more template
variants after the verifier is reliable.

### Gates Reduce Yield

The `min_individual_candidate_count` rule will reject many rare but interesting
facts. This is intentional. A rare clue is often a disguised direct reference.

### Public Wording Leaks Private Ontology

Terms like `material_region`, `measurement`, `profile`, `provenance`, and
`accumulated body` can be meaningful internally but confusing publicly.
Templates should ground every derived concept in visible code.

### Graph Coverage Is Too Thin

If the graph lacks enough relation families, clause sets may be repetitive.
The rejection manifest should show which missing graph families block better
questions.

### Mixed Target Types Create Fake Multi-Hop Prompts

A prompt can sound rich while combining unrelated facts about faces, vertices,
parameters, and operations. The verifier must require a clear target projection
for every clue.

### Obfuscation Creates Ambiguity

Hard questions can become under-specified. The resolver should compute the
candidate set after every clue and reject any prompt whose full clue set is not
unique.

## Recommended Next Step

Turn the mock preview into the first deterministic generator spike:

1. Build ontology atoms from a small set of CadEvolve scripts.
2. Apply `min_individual_candidate_count = 5` and temporal side-range gates.
3. Verbalize accepted atoms with versioned templates.
4. Search broad clue sets that uniquely identify one feature.
5. Emit public checklist rows, private hidden queries, and rejection manifests.

Only after this rule-based path produces credible rows should optional model
calls be reconsidered, and then only for external evaluation or controlled
wording experiments.
