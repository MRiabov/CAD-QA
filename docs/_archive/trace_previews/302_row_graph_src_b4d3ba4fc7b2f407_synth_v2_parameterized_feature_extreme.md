# row:graph:src_b4d3ba4fc7b2f407:synth:v2:parameterized_feature_extreme

- **source**: original-pool
- **hop**: 3  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp7`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, 5))
wp2 = wp1.box(104, 51, 3, centered=[True, True, False])
wp3 = wp2.faces('<Z')
wp4 = wp3.workplane()
wp5 = wp4.rect(104, 200)
wp6 = wp5.extrude(9, combine=False)
wp7 = wp2.union(wp6)
wp8 = wp7.faces('>Z')
wp9 = wp8.workplane()
wp10 = wp9.rect(104, 197)
wp11 = wp10.cutBlind(-9)
wp12 = wp11.faces('>Z')
wp13 = wp12.workplane()
wp14 = wp13.pushPoints([[-17, 0], [17, 0]])
wp15 = wp14.rect(1, 200)
wp16 = wp15.extrude(-9, combine=False)
wp17 = wp16.edges('|X')
wp18 = wp17.fillet(2)
result = wp18
```

Identify the target feature that satisfies all of these constraints:
- The target feature's face count is greater than 0.0.
- The target feature has a value for centroid Y coordinate.
- From the remaining candidates, choose the one with the least centroid Y coordinate.
- If candidates are still tied, use the largest overall height as the tie-break.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
All solids (wp2, wp6, wp7, wp11, wp16, wp18) have centroid Y = 0. Their heights: wp2=3, wp6=9, wp7=12, wp11=9, wp16=9, wp18≈9. The least centroid Y tie is broken by largest height, so wp7 (height 12) is selected.

{"name": "submit_text", "arguments": {"text": "wp7"}}
```
