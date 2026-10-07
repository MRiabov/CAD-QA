# row:graph:graph:src_09b8d8412ad88a86:q1:argmin_origin_z_workplane

- **source**: original-pool
- **hop**: 1  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp1`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -2))
wp2 = wp1.box(198, 200, 37)
wp3 = wp2.faces('>Z')
wp4 = wp3.workplane()
wp5 = wp4.rect(198, 200)
wp6 = wp5.extrude(5)
wp7 = wp6.faces('>Z')
wp8 = wp7.workplane()
wp9 = wp8.rect(170, 172)
wp10 = wp9.cutBlind(-5)
wp11 = wp10.faces('>Z')
wp12 = wp11.workplane()
wp13 = wp12.rect(170, 172, forConstruction=True)
wp14 = wp13.vertices()
wp15 = wp14.cskHole(21, 28, 135)
result = wp15
```

Identify the target workplane that satisfies all of these constraints:
- Among the remaining candidates, choose the one with the smallest workplane origin height.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
Among all workplane variables created in the script, wp1 has the smallest origin height (z = -2). All later workplanes (wp4, wp8, wp12) have higher origins (16.5, 21.5, 21.5).

{"name": "submit_text", "arguments": {"text": "wp1"}}
```
