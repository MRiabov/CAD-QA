# row:graph:graph:src_445c19cac5db338d:q1:argmin_origin_z_workplane

- **source**: original-pool
- **hop**: 1  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp11`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY')
wp2 = wp1.box(197, 200, 10)
wp3 = cq.Workplane('XY')
wp4 = wp3.box(197, 13, 3)
wp5 = wp4.translate([0, -36, 3])
wp6 = cq.Workplane('XY')
wp7 = wp6.box(197, 13, 3)
wp8 = wp7.translate([0, 36, 3])
wp9 = wp2.cut(wp5)
wp10 = wp9.cut(wp8)
wp11 = cq.Workplane(cq.Plane(origin=cq.Vector(-98, 0, -5), xDir=cq.Vector(0, 3, 0), normal=cq.Vector(3, 0, 0)))
wp12 = wp11.polyline([[-29, 0], [29, 0], [0, 7]])
wp13 = wp12.close()
wp14 = wp13.extrude(197, combine=0)
wp15 = wp10.union(wp14)
result = wp15
```

Identify the target workplane that satisfies all of these constraints:
- Among the remaining candidates, choose the one with the smallest workplane origin height.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
The script constructs a base box (wp2), cuts two recesses (wp5, wp8) from it, and then unions a triangular extrusion (wp14) created on a custom workplane.  

Workplanes defined:  
- `wp1` (XY origin)  
- `wp2` (the first box, origin at XY)  
- `wp3` (XY origin) → `wp4` box then translated to `wp5`  
- `wp6` (XY origin) → `wp7` box then translated to `wp8`  
- `wp11` custom workplane with origin at (-98, 0, -5)  

The target must be among the remaining candidates (workplane variables). The custom workplane `wp11` has origin height `-5`, which is lower than `wp1`, `wp3`, `wp6` (height 0).  

Thus the smallest workplane origin height is `wp11`.  

{"name": "submit_text", "arguments": {"text": "wp11"}}
```
