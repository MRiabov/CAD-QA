# row:graph:graph:src_36629229b5ba4373:q1:argmax_origin_z_workplane

- **source**: center-fix
- **hop**: 1  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp26`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 6, 0))
wp2 = wp1.box(188, 212, 126)
wp3 = cq.Workplane('XY', origin=(0, 6, 0))
wp4 = wp3.box(175, 200, 120)
wp5 = wp4.translate([0, 0, 3])
wp6 = wp2.cut(wp5)
wp7 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 6, 0), xDir=cq.Vector(2, 2, 0), normal=cq.Vector(2, -2, 0)))
wp8 = wp7.rect(567, 252)
wp9 = wp8.extrude(-567)
wp10 = wp6.cut(wp9)
wp11 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 6, 0), xDir=cq.Vector(2, 2, 0), normal=cq.Vector(2, -2, 0)))
wp12 = wp11.rect(567, 55)
wp13 = wp12.extrude(-6)
wp14 = wp10.cut(wp13)
wp15 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 6, 0), xDir=cq.Vector(2, 2, 0), normal=cq.Vector(2, -2, 0)))
wp16 = wp15.center(0, -14)
wp17 = wp16.rect(567, 1)
wp18 = wp17.extrude(-6)
wp19 = wp14.cut(wp18)
wp20 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 6, 0), xDir=cq.Vector(2, 2, 0), normal=cq.Vector(2, -2, 0)))
wp21 = wp20.center(0, 0)
wp22 = wp21.rect(567, 1)
wp23 = wp22.extrude(-6)
wp24 = wp19.cut(wp23)
wp25 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 6, 0), xDir=cq.Vector(2, 2, 0), normal=cq.Vector(2, -2, 0)))
wp26 = wp25.center(0, 14)
wp27 = wp26.rect(567, 1)
wp28 = wp27.extrude(-6)
wp29 = wp24.cut(wp28)
result = wp29
```

Identify the target workplane that satisfies all of these constraints:
- Among the remaining candidates, choose the one with the greatest workplane origin height.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
All explicit workplane origins are (0,6,0). wp26 = wp25.center(0,14) shifts origin to (0,6,14), the greatest z‑coordinate (height). No other workplane reaches a higher origin.

{"name": "submit_text", "arguments": {"text": "wp26"}}
```
