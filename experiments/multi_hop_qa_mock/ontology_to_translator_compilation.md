# Ontology To Translator Packet Compilation

This file shows the missing layer: low-level ontology relation atoms are
compiled into canonical clue text before any LLM translator is called.

## mhqa_mock_001

### Raw Ontology Clauses

```json
[
  {
    "clause_id": "c01",
    "constraint_type": "operation_semantics",
    "relation": "operation_with_material_effect",
    "arguments": {
      "operation": "hole",
      "material_effect": "subtractive",
      "entity_label": "feature"
    }
  },
  {
    "clause_id": "c02",
    "constraint_type": "temporal",
    "relation": "operation_has_prior_count",
    "arguments": {
      "operation": "hole",
      "prior_count": 2,
      "scope": "repeated pattern"
    }
  },
  {
    "clause_id": "c03",
    "constraint_type": "selector",
    "relation": "feature_placed_from_selected_face",
    "arguments": {
      "selector_axis": "Z",
      "selector_direction": "positive",
      "face_role": "top face",
      "source_state": "immediately previous result",
      "via": "workplane"
    }
  },
  {
    "clause_id": "c04",
    "constraint_type": "spatial",
    "relation": "parameter_sign_in_pattern",
    "arguments": {
      "parameter": "center offset",
      "axis": "X",
      "sign": "positive",
      "scope": "repeated hole pattern"
    }
  },
  {
    "clause_id": "c05",
    "constraint_type": "metric",
    "relation": "metric_bundle",
    "arguments": {
      "material_effect": "removes material",
      "bbox_effect": "leaves global bounding box unchanged"
    }
  }
]
```

### Compiled Canonical Clues

- `c01` `operation_semantics` `normal`: The target is a subtractive hole feature.
- `c02` `temporal` `normal`: The target comes after two earlier holes in the repeated pattern.
- `c03` `selector` `normal`: The target is placed from a workplane made from the top face of the immediately previous result.
- `c04` `spatial` `normal`: The target's center offset lies on the positive-X side of the repeated hole pattern.
- `c05` `metric` `normal`: The target removes material and leaves global bounding box unchanged.

### Translator Receives

- public source code
- answer type and answer instruction
- compiled canonical clues
- forbidden strings/content
- output schema

It still does not receive gold answers, predicates, candidate sets,
evidence chains, distractors, or verifier status.

## mhqa_mock_002

### Raw Ontology Clauses

```json
[
  {
    "clause_id": "c01",
    "constraint_type": "operation_semantics",
    "relation": "profile_operation_extruded_feature",
    "arguments": {
      "profile_operation": "circle",
      "feature_operation": "extrude",
      "object_label": "circular boss",
      "negative_classes": [
        "helical sweep",
        "union step"
      ]
    }
  },
  {
    "clause_id": "c03",
    "constraint_type": "parameter",
    "relation": "profile_and_feature_parameters",
    "arguments": {
      "profile_parameter_name": "radius",
      "profile_parameter_value": 5,
      "feature_parameter_name": "extrusion distance",
      "feature_parameter_value": 8
    }
  },
  {
    "clause_id": "c04",
    "constraint_type": "spatial",
    "relation": "argmax_workplane_coordinate",
    "arguments": {
      "coordinate": "Z",
      "entity_set": "repeated boss workplanes",
      "reference": "workplane origin"
    }
  },
  {
    "clause_id": "c05",
    "constraint_type": "relation",
    "relation": "input_to_accumulated_union",
    "arguments": {
      "input_label": "target boss",
      "target_label": "final accumulated-body union",
      "leakage_risk": "high"
    }
  }
]
```

### Compiled Canonical Clues

- `c01` `operation_semantics` `normal`: The target is an extruded circular boss, not helical sweep and not union step.
- `c03` `parameter` `normal`: The target uses radius 5 and extrusion distance 8.
- `c04` `spatial` `normal`: The target's workplane origin has the greatest Z coordinate among the repeated boss workplanes.
- `c05` `relation` `high`: The target feeds the final accumulated-body union.

### Translator Receives

- public source code
- answer type and answer instruction
- compiled canonical clues
- forbidden strings/content
- output schema

It still does not receive gold answers, predicates, candidate sets,
evidence chains, distractors, or verifier status.

## mhqa_mock_003

### Raw Ontology Clauses

```json
[
  {
    "clause_id": "c01",
    "constraint_type": "operation_semantics",
    "relation": "profile_operation_cut_kind",
    "arguments": {
      "profile_operation": "rect",
      "feature_operation": "cutBlind",
      "object_label": "rectangular blind cut",
      "negative_classes": [
        "star-shaped through cut"
      ]
    }
  },
  {
    "clause_id": "c02",
    "constraint_type": "selector",
    "relation": "selector_face_axis_direction",
    "arguments": {
      "axis": "Y",
      "direction": "positive",
      "entity_label": "face selector"
    }
  },
  {
    "clause_id": "c03",
    "constraint_type": "parameter",
    "relation": "rect_parameters_symbolic",
    "arguments": {
      "width_symbol": "A",
      "width_description": "box length",
      "height_symbol": "th",
      "height_expression": "R_out * R_in"
    }
  },
  {
    "clause_id": "c04",
    "constraint_type": "spatial",
    "relation": "loop_member_coordinate_sign",
    "arguments": {
      "axis": "Z",
      "sign": "positive",
      "entity_set": "repeated rectangular cuts"
    }
  },
  {
    "clause_id": "c05",
    "constraint_type": "metric",
    "relation": "metric_bundle",
    "arguments": {
      "material_effect": "removes material",
      "bbox_effect": "does not change the outer bounding box"
    }
  }
]
```

### Compiled Canonical Clues

- `c01` `operation_semantics` `normal`: The target is a rectangular blind cut, not a star-shaped through cut.
- `c02` `selector` `normal`: The target is made from the positive-Y face selector.
- `c03` `parameter` `normal`: The target's rectangle uses the box length for one side and R_out * R_in for the other.
- `c04` `spatial` `normal`: The target is the positive-Z member of the repeated rectangular cuts.
- `c05` `metric` `normal`: The target removes material and does not change the outer bounding box.

### Translator Receives

- public source code
- answer type and answer instruction
- compiled canonical clues
- forbidden strings/content
- output schema

It still does not receive gold answers, predicates, candidate sets,
evidence chains, distractors, or verifier status.
