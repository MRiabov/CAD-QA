# CADEditQA Task Specification Draft

This is a draft seed specification for edit-oriented CAD-QA task families. The
first implemented slices should be conservative and should reuse CAD-QA source
records, traces, label policies, split groups, and verifier infrastructure.

## Purpose

Edit rows should test whether a model can propose constrained edits to a
CadQuery script after diagnosing a construction, topology, placement, or feature
problem. The row moves from answering what the script does to choosing a small,
auditable action that changes the script or a parameter in a verifier-checked
way.

## Naming and Framing

The working label `CADEditQA` refers to edit-verification rows over the same
source records, ontology graph, query programs, split metadata, and verifier
core. The paper framing should describe these as graph-first CAD edit
prediction rows.

CADEditQA rows are not free-form design tasks. Public rows should use
constrained answer formats, target metadata, and verifier-oriented structured
answers so edit success, magnitude error, and side effects can be scored
consistently.

## Relationship to CAD-QA

Edit rows must reuse the same source programs, operation graphs, isolated
execution traces, raw labels, provenance records, split grouping, and verifier
infrastructure used by the graph-first benchmark. Edit semantics should be
represented as query programs over source variants, feature effects, and target
measurements.

## Likely Task Families

- `parameter_edit_direction`: choose whether to increase, decrease, or preserve
  a numeric parameter to satisfy a target property.
- `parameter_edit_value`: predict the new parameter value or delta.
- `feature_to_edit`: choose which feature should be edited to satisfy a target.
- `operation_removal_effect`: choose whether removing a feature satisfies a
  target condition.
- `selector_repair`: choose a selector that targets the intended faces or
  edges.
- `workplane_offset_repair`: choose a workplane offset or translation that
  places a feature at the target coordinate.
- `topology_target_edit`: choose an edit that reaches a requested face/edge
  count when a constrained answer exists.

## Output Schema Direction

Initial outputs should be simple and verifier-friendly:

- discrete labels such as `increase`, `decrease`, `unchanged`, `no_valid_edit`;
- numeric deltas in millimetres;
- candidate IDs from a finite edit list;
- constrained records:

```json
{
  "feature_id": "wp13",
  "action": "set_parameter",
  "parameter": "radius",
  "value": 3.0
}
```

The first schema should prefer deterministic parsing and bounded numeric ranges
over broad natural-language repair descriptions.

## Verifier Contract

An edit answer is valid only if the verifier can apply the proposed action to
the same normalized source or trace template and remeasure the target property.
Scores should be derived from exact checks:

- target condition satisfied;
- no execution failure introduced;
- side effects bounded;
- edit magnitude close to optimal when optimality is part of the task;
- output parse valid.

Heuristic checks may be diagnostic baselines, not official labels.

## Splits and Leakage

CADEditQA must reuse group-safe splitting. Source groups, generator groups,
operation signatures, topology signatures, and counterfactual groups must not
leak across protected train/test splits.

Edit candidates derived from the same base source must stay in the same split
as that source.

## First Repair Slices

### `parameter_edit_direction`

Given a script, a target property, and one editable numeric parameter, choose:

```text
increase
decrease
unchanged
no_valid_edit
```

Example:

```text
The final part should have a larger Z bounding-box maximum. The editable
parameter is `height` in feature `wp4.extrude(height)`. Which direction should
the parameter change?
```

### `feature_to_edit`

Given a target property and several feature IDs, choose the feature whose edit
can satisfy the target with minimal side effects.

### `selector_repair`

Given a selector expression that selects the wrong count of entities and a
target count or target entity type, choose one candidate selector.

### `workplane_offset_repair`

Given a misplaced feature and candidate offsets, choose the offset that places
the feature center at the target coordinate under verifier tolerance.

## Future Implementation Targets

- numeric parameter value prediction;
- edit program synthesis under a restricted DSL;
- multi-step edit planning;
- provenance-guided edit selection;
- RL/rejection sampling with verifier rewards;
- multimodal edit tasks using optional render artifacts.
