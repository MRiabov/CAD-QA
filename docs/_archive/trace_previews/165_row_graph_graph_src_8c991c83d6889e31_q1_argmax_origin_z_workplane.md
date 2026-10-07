# row:graph:graph:src_8c991c83d6889e31:q1:argmax_origin_z_workplane

- **source**: original-pool
- **hop**: 1  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp9`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -91))
wp2 = wp1.splineApprox([[81, 0, 0], [79, 20, 4], [71, 39, 7], [59, 56, 11], [44, 69, 15], [25, 77, 18], [5, 81, 22], [-15, 80, 25], [-35, 74, 29], [-52, 63, 33], [-66, 48, 36], [-76, 30, 40], [-81, 10, 44], [-81, -10, 47], [-76, -30, 51], [-66, -48, 54], [-52, -63, 58], [-35, -74, 62], [-15, -80, 65], [5, -81, 69], [25, -77, 73], [44, -69, 76], [59, -56, 80], [71, -39, 84], [79, -20, 87], [81, 0, 91], [79, 20, 94], [71, 39, 98], [59, 56, 102], [44, 69, 105], [25, 77, 109], [5, 81, 113], [-15, 80, 116], [-35, 74, 120], [-52, 63, 123], [-66, 48, 127], [-76, 30, 131], [-81, 10, 134], [-81, -10, 138], [-76, -30, 142], [-66, -48, 145], [-52, -63, 149], [-35, -74, 153], [-15, -80, 156], [5, -81, 160], [25, -77, 163], [44, -69, 167], [59, -56, 171], [71, -39, 174], [79, -20, 178], [81, 0, 182]], makeWire=True)
wp3 = cq.Workplane('XZ', origin=(0, 0, -91))
wp4 = wp3.moveTo(81, 0)
wp5 = wp4.circle(9)
wp6 = wp5.sweep(wp2)
wp7 = wp6.rotate([0, 0, -91], [0, 0, -87], 180)
wp8 = wp6.union(wp7)
wp9 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 0, -45), xDir=cq.Vector(-3, 0, 1), normal=cq.Vector(-1, 0, -3)))
wp10 = wp9.rect(203, 19)
wp11 = wp10.extrude(2, both=True)
wp12 = wp8.union(wp11)
result = wp12
```

Identify the target workplane that satisfies all of these constraints:
- Among the remaining candidates, choose the one with the greatest workplane origin height.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
The script builds a shape by sweeping a circle along a 3D spline, mirroring it (rotate 180°), unioning, then adding a rectangular extrude.  

The question asks for the workplane among the remaining candidates with the greatest origin height. The only explicitly created workplanes are `wp1`, `wp3`, `wp9`.  
- `wp1` origin z = -91  
- `wp3` origin z = -91  
- `wp9` origin z = -45  

Comparing z-heights: -45 > -91. So `wp9` has the greatest origin height.  

The answer must be a source variable name.  

```json
{"name": "submit_text", "arguments": {"text": "wp9"}}
```
```
