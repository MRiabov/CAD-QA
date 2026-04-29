# Translator Input Packets

These are the sanitized payloads intended for the first question-translator model call. They exclude gold answers, predicates, candidate sets, evidence chains, distractors, and verifier status.

## mhqa_mock_001

- Packet version: `cadqa_translator_input_mock_v0`
- Source ID: `src_mock_advanced_holes`
- Role: `question_translator`

### Render Request

- `style`: constraint_checklist
- `answer_type`: feature_id
- `answer_instruction`: Return exactly one feature ID.
- `audience`: CAD benchmark model reading CadQuery code
- `target_difficulty`: mhqa_level_3_complex_4_5_hops
- `rewrite_goal`: Make the question read like a natural CAD reasoning prompt while preserving every approved clue.

### Public Source Code

```python
import cadquery as cq

wp0 = cq.Workplane("XY")
box_a = wp0.box(1, 2, 3)
box_b = cq.Workplane("XY").box(4, 5, 6)
feature_after_box_2 = box_b.extrude(2)
hole_1_wp = feature_after_box_2.faces(">Z").workplane().center(-1.5, 0)
hole_1 = hole_1_wp.hole(1)
hole_2_wp = hole_1.faces(">Z").workplane().center(0, 0)
hole_2 = hole_2_wp.hole(1)
hole_3_wp = hole_2.faces(">Z").workplane().center(1.5, 0)
hole_3 = hole_3_wp.hole(1)
result = hole_3
```

### Approved Clues

- `c01` `operation_semantics`: The target is a subtractive hole feature.
- `c02` `temporal`: The target comes after two earlier hole features in the repeated pattern.
- `c03` `selector`: The target is placed from a workplane made from the top face of the immediately previous result.
- `c04` `spatial`: The target's center offset lies on the positive-X side of the repeated hole pattern.
- `c05` `metric`: The target removes material and leaves the global bounding box unchanged.

### Allowed Terms

`feature`, `hole`, `workplane`, `top face`, `previous result`, `positive-X`, `center offset`, `removes material`, `global bounding box`

### Forbidden Question Strings

`hole_1`, `hole_2`, `hole_3`, `hole_1_wp`, `hole_2_wp`, `hole_3_wp`, `feature_after_box_2`

### Forbidden Content

- Do not reveal the gold answer.
- Do not mention hidden predicates, candidate sets, evidence chains, verifier status, or distractor analysis.
- Do not add new CAD facts that are not present in approved_clues.
- Do not ask for an explanation or chain of thought.
- Do not refer to source line numbers.

### Required Translator Output Shape

```json
{
  "question": "string",
  "clue_map": [
    {
      "clause_id": "string",
      "text_span": "string"
    }
  ],
  "self_check": {
    "forbidden_strings_present": "boolean",
    "unsupported_cad_facts": "array",
    "ambiguous_phrases": "array"
  }
}
```

## mhqa_mock_002

- Packet version: `cadqa_translator_input_mock_v0`
- Source ID: `src_mock_cadevolve_helix_boss`
- Role: `question_translator`

### Render Request

- `style`: constraint_checklist
- `answer_type`: feature_id
- `answer_instruction`: Return exactly one feature ID.
- `audience`: CAD benchmark model reading CadQuery code
- `target_difficulty`: mhqa_level_3_complex_4_5_hops
- `rewrite_goal`: Preserve the approved clues but make the final-step relation less direct if possible.

### Public Source Code

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -89))
wp2 = wp1.splineApprox([[79, 0, 0], [69, 38, 7], [42, 66, 14], [5, 78, 21], [-33, 71, 29], [-64, 46, 36], [-78, 10, 43], [-73, -29, 50], [-50, -61, 57], [-15, -77, 64], [24, -75, 72], [57, -54, 79], [76, -20, 86], [76, 20, 93], [57, 54, 100], [24, 75, 107], [-15, 77, 114], [-50, 61, 122], [-73, 29, 129], [-78, -10, 136], [-64, -46, 143], [-33, -71, 150], [5, -78, 157], [42, -66, 164], [69, -38, 172], [79, 0, 179]], makeWire=1)
wp3 = cq.Workplane('XZ', origin=(0, 0, -89))
wp4 = wp3.moveTo(79, 0)
wp5 = wp4.circle(11)
wp6 = wp5.sweep(wp2)
wp7 = cq.Workplane(cq.Plane(origin=cq.Vector(28, 85, -71), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0)))
wp8 = wp7.circle(5)
wp9 = wp8.extrude(8)
wp10 = wp6.union(wp9)
wp11 = cq.Workplane(cq.Plane(origin=cq.Vector(-72, 53, -53), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(-2, 2, 0)))
wp12 = wp11.circle(5)
wp13 = wp12.extrude(8)
wp14 = wp10.union(wp13)
wp15 = cq.Workplane(cq.Plane(origin=cq.Vector(-72, -53, -36), xDir=cq.Vector(2, -2, 0), normal=cq.Vector(-2, -2, 0)))
wp16 = wp15.circle(5)
wp17 = wp16.extrude(8)
wp18 = wp14.union(wp17)
wp19 = cq.Workplane(cq.Plane(origin=cq.Vector(28, -85, -18), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0)))
wp20 = wp19.circle(5)
wp21 = wp20.extrude(8)
wp22 = wp18.union(wp21)
wp23 = cq.Workplane(cq.Plane(origin=cq.Vector(28, 85, 18), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0)))
wp24 = wp23.circle(5)
wp25 = wp24.extrude(8)
wp26 = wp22.union(wp25)
wp27 = cq.Workplane(cq.Plane(origin=cq.Vector(-72, 53, 36), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(-2, 2, 0)))
wp28 = wp27.circle(5)
wp29 = wp28.extrude(8)
wp30 = wp26.union(wp29)
wp31 = cq.Workplane(cq.Plane(origin=cq.Vector(-72, -53, 54), xDir=cq.Vector(2, -2, 0), normal=cq.Vector(-2, -2, 0)))
wp32 = wp31.circle(5)
wp33 = wp32.extrude(8)
wp34 = wp30.union(wp33)
wp35 = cq.Workplane(cq.Plane(origin=cq.Vector(28, -85, 72), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0)))
wp36 = wp35.circle(5)
wp37 = wp36.extrude(8)
wp38 = wp34.union(wp37)
result = wp38
```

### Approved Clues

- `c01` `operation_semantics`: The target is an extruded circular boss, not the helical sweep and not a union step.
- `c03` `parameter`: The target uses a circular profile with radius 5 and extrusion distance 8.
- `c04` `spatial`: The target's workplane origin has the greatest Z coordinate among the repeated boss workplanes.
- `c05` `relation`: The target is an input to the final accumulated-body union. This clue is allowed but should be phrased less directly than naming the final union variable.

### Allowed Terms

`feature`, `extruded circular boss`, `helical sweep`, `union step`, `circle radius`, `extrusion distance`, `workplane origin`, `greatest Z coordinate`, `accumulated body`

### Forbidden Question Strings

`wp6`, `wp9`, `wp13`, `wp17`, `wp21`, `wp25`, `wp29`, `wp33`, `wp37`, `wp38`

### Forbidden Content

- Do not reveal the gold answer.
- Do not mention hidden predicates, candidate sets, evidence chains, verifier status, or distractor analysis.
- Do not add new CAD facts that are not present in approved_clues.
- Do not ask for an explanation or chain of thought.
- Do not refer to source line numbers.

### Required Translator Output Shape

```json
{
  "question": "string",
  "clue_map": [
    {
      "clause_id": "string",
      "text_span": "string"
    }
  ],
  "self_check": {
    "forbidden_strings_present": "boolean",
    "unsupported_cad_facts": "array",
    "ambiguous_phrases": "array"
  }
}
```

## mhqa_mock_003

- Packet version: `cadqa_translator_input_mock_v0`
- Source ID: `src_mock_shapenet_star_slots`
- Role: `question_translator`

### Render Request

- `style`: constraint_checklist
- `answer_type`: feature_id
- `answer_instruction`: Return exactly one loop-expanded feature ID.
- `audience`: CAD benchmark model reading CadQuery code
- `target_difficulty`: mhqa_level_4_hard_6_8_hops
- `rewrite_goal`: Render the clues clearly, but flag if the requested loop-expanded feature ID contract feels unnatural.

### Public Source Code

```python
import cadquery as cq
import math
A = 14.0
B = 26.0
C = 89.0
R_out = 4.0
R_in = 0.27
side_scale = 1.0
base = cq.Workplane("XY").box(A, B, C)
def star_points(n=5, inner=R_in, scale=1.0):
    pts = []
    total = n * 2
    for k in range(total):
        ang = 2 * math.pi * k / total
        rad = 1.0 if (k % 2 == 0) else inner
        pts.append((math.cos(ang) * rad * scale, math.sin(ang) * rad * scale))
    return pts
front_shape = star_points()
side_shape = star_points()
for face_tag in (">Y", "<Y"):
    base = base.faces(face_tag).workplane().polyline(front_shape).close().cutThruAll()
for face_tag in (">X", "<X"):
    base = base.faces(face_tag).workplane().polyline(side_shape).close().cutThruAll()
th = R_out * R_in
dY = min(R_out, B / 2.0)
dX = min(R_out, A / 2.0)
zpos = R_out + th / 2.0
for z in (zpos, -zpos):
    base = base.faces(">Y").workplane().center(0, z).rect(A, th).cutBlind(-dY)
    base = base.faces(">X").workplane().center(0, z).rect(B, th).cutBlind(-dX)
result = base
```

### Approved Clues

- `c01` `operation_semantics`: The target is a rectangular blind cut, not one of the star-shaped through cuts.
- `c02` `selector`: The target is made from the positive-Y face selector.
- `c03` `parameter`: The rectangle uses the box length A for one side and th = R_out * R_in for the other side.
- `c04` `spatial`: The target is the positive-Z member of the repeated rectangular cuts.
- `c05` `metric`: The target removes material without changing the outer bounding box.

### Allowed Terms

`loop-expanded feature`, `rectangular blind cut`, `star-shaped through cut`, `positive-Y face selector`, `box length`, `R_out * R_in`, `positive-Z`, `outer bounding box`

### Forbidden Question Strings

`slot_y_pos_upper_cut`, `slot_x_pos_upper_cut`, `slot_y_pos_lower_cut`, `slot_x_pos_lower_cut`, `front_star_cut_pos_y`

### Forbidden Content

- Do not reveal the gold answer.
- Do not mention hidden predicates, candidate sets, evidence chains, verifier status, or distractor analysis.
- Do not add new CAD facts that are not present in approved_clues.
- Do not ask for an explanation or chain of thought.
- Do not refer to source line numbers.

### Required Translator Output Shape

```json
{
  "question": "string",
  "clue_map": [
    {
      "clause_id": "string",
      "text_span": "string"
    }
  ],
  "self_check": {
    "forbidden_strings_present": "boolean",
    "unsupported_cad_facts": "array",
    "ambiguous_phrases": "array",
    "contract_concern": "string or null"
  }
}
```
