# CADEditQA: Dataset And Training Spec

CADEditQA is a natural continuation of CAD-QA.

CAD-QA asks:

> Given CadQuery code, what geometry, topology, selector result, point label, or
> provenance relation follows from the construction?

CADEditQA asks:

> Given CadQuery code, current labels, and a target property, what constrained
> edit should be applied to achieve it?

This is useful for CAD agents because it moves from diagnosis to correction.

## 1. Core Task Definition

Each example contains:

1. A normalized CadQuery script.
2. A trace-backed current geometric state.
3. A target condition.
4. A constrained edit space.
5. A required structured output format.
6. Verifier-computed ground-truth edit, candidate ranking, or reward.

Example:

```text
Feature `wp8` cuts a circular hole with radius 2.0 mm. The target is to remove
more material while preserving the hole center and cut direction.

Allowed actions: increase radius, decrease radius, unchanged, no_valid_edit.
Return exactly one action.
```

Expected answer:

```text
increase radius
```

## 2. Main Task Families

### Task 1: Parameter Edit Direction

Choose whether an editable parameter should increase, decrease, remain
unchanged, or has no valid monotonic edit.

Targets:

- larger/smaller final volume;
- larger/smaller bounding-box dimension;
- more/fewer selected entities;
- larger/smaller cut volume;
- larger/smaller feature radius or height.

### Task 2: Parameter Edit Value

Predict a new value or delta for one parameter under verifier tolerance.

Output:

```json
{"parameter": "radius", "value": 3.0}
```

Use only when the target is well-conditioned and the solution is unique or
canonical.

### Task 3: Feature To Edit

Given candidate feature IDs and a target condition, choose which feature should
be edited.

This is most useful when provenance labels identify which feature controls a
target entity, material region, or topology change.

### Task 4: Selector Repair

Given a selector expression and target entity count/type, choose a replacement
selector from candidates.

Example targets:

- select all vertical edges;
- select only top faces;
- select one cylindrical face;
- avoid selecting edges introduced by a fillet.

### Task 5: Workplane Or Coordinate Repair

Choose an offset, rotation, or workplane change that places a feature at the
target coordinate or on the intended face.

The answer should be constrained to candidate edits until continuous coordinate
repair is reliable.

### Task 6: Operation Removal Or Replacement

Choose whether removing or replacing one operation satisfies a target property,
such as restoring sharp edges, removing a hole, or changing volume in the
desired direction.

### Task 7: Candidate Edit Selection

Given several concrete edit candidates, choose the candidate with the best
verifier score.

This is often safer than open numeric prediction for early releases.

### Task 8: Candidate Edit Ranking

Rank candidate edits by verifier score, minimal side effects, or target error.

Use only when ranking labels are stable and ties are handled explicitly.

## 3. Output Formats

### Format A: Discrete Direction

```text
increase
decrease
unchanged
no_valid_edit
```

### Format B: Candidate Selection

```text
candidate_b
```

### Format C: Numeric Parameter Edit

```json
{"feature_id": "wp13", "parameter": "radius", "value": 3.0}
```

### Format D: Edit Record

```json
{
  "feature_id": "wp13",
  "action": "replace_selector",
  "old": "edges(\"|Z\")",
  "new": "edges(\"|X\")"
}
```

## 4. Recommended MVP

MVP v0.1:

- `parameter_edit_direction`;
- `feature_to_edit`;
- `selector_repair` with candidate choices;
- `workplane_offset_repair` with candidate choices.

Do not start with unrestricted code editing. It is too hard to grade and too
easy to turn into general CAD generation.

## 5. Ground Truth Generation

Ground truth should be verifier-derived:

1. Apply candidate edit to normalized source or parameterized template.
2. Execute in isolated worker.
3. Recompute target labels.
4. Check target satisfaction and side effects.
5. Choose canonical answer using deterministic tie-breaking.

Tie-breaking should prefer:

1. target satisfied;
2. no execution/kernel failure;
3. smallest edit magnitude;
4. fewest non-target label changes;
5. stable candidate ID ordering.

## 6. Ambiguity Filtering

Reject or label `no_valid_edit` when:

- multiple candidates tie and no deterministic rule is meaningful;
- target property is insensitive to the allowed edit;
- edit causes execution failure;
- edit changes unrelated topology too much;
- target is impossible under the constrained edit space;
- label is kernel-unstable.

## 7. Reward Design

Verifier reward for candidate edit tasks:

```text
reward =
  +1.0 if target satisfied
  - target_error_penalty
  - edit_magnitude_penalty
  - side_effect_penalty
  - parse_failure_penalty
```

Rewards are research artifacts unless frozen into an official task metric.
Official public tasks should still have deterministic labels and parsers.

## 8. Evaluation Metrics

Report:

- exact candidate accuracy;
- target satisfaction rate;
- invalid output rate;
- numeric value pass rate under tolerance;
- target error;
- edit magnitude ratio to canonical edit;
- side-effect rate;
- verifier execution failure rate;
- per-task and per-split metrics.

## 9. Splits

CADEditQA uses CAD-QA split groups:

- source ID;
- generator ID;
- source subtree;
- operation signature;
- topology signature;
- counterfactual group;
- edit group.

All candidate edits for a base source stay in the same split.

## 10. Training Recipes

SFT is useful for:

- structured output format compliance;
- discrete edit direction;
- candidate selection;
- provenance-guided feature choice.

Verifier-guided rejection sampling or RL may help when:

- many candidate edits exist;
- exact labels are easy to verify but hard to derive analytically;
- numeric edit magnitude has a smooth target error.

Do not use RL before a deterministic supervised baseline is healthy.

## 11. Failure Modes To Study

- correct diagnosis but wrong editable feature;
- correct direction but wrong magnitude;
- selector repair that changes the wrong entities;
- workplane repair in local rather than global coordinates;
- edit satisfies target but causes large side effects;
- output format invalid;
- overfitting to variable names or comments.
