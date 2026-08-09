# row:graph:graph:src_3cbce23163879930:q1:argmax_origin_z_workplane

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
wp1 = cq.Workplane('XY', origin=(-34, 0, 0))
wp2 = wp1.box(244, 109, 200)
wp3 = cq.Workplane('XY', origin=(-34, 0, 0))
wp4 = wp3.box(236, 100, 196)
wp5 = wp4.translate([0, 0, 2])
wp6 = wp2.cut(wp5)
wp7 = cq.Workplane(cq.Plane(origin=cq.Vector(-34, 0, 0), xDir=cq.Vector(2, 2, 0), normal=cq.Vector(2, -2, 0)))
wp8 = wp7.rect(535, 400)
wp9 = wp8.extrude(-535)
wp10 = wp6.cut(wp9)
wp11 = cq.Workplane(cq.Plane(origin=cq.Vector(-34, 0, 0), xDir=cq.Vector(2, 2, 0), normal=cq.Vector(2, -2, 0)))
wp12 = wp11.rect(535, 40)
wp13 = wp12.extrude(-4)
wp14 = wp10.cut(wp13)
wp15 = cq.Workplane(cq.Plane(origin=cq.Vector(-34, 0, 0), xDir=cq.Vector(2, 2, 0), normal=cq.Vector(2, -2, 0)))
wp16 = wp15.center(0, -10)
wp17 = wp16.rect(535, 1)
wp18 = wp17.extrude(-4)
wp19 = wp14.cut(wp18)
wp20 = cq.Workplane(cq.Plane(origin=cq.Vector(-34, 0, 0), xDir=cq.Vector(2, 2, 0), normal=cq.Vector(2, -2, 0)))
wp21 = wp20.center(0, 0)
wp22 = wp21.rect(535, 1)
wp23 = wp22.extrude(-4)
wp24 = wp19.cut(wp23)
wp25 = cq.Workplane(cq.Plane(origin=cq.Vector(-34, 0, 0), xDir=cq.Vector(2, 2, 0), normal=cq.Vector(2, -2, 0)))
wp26 = wp25.center(0, 10)
wp27 = wp26.rect(535, 1)
wp28 = wp27.extrude(-4)
wp29 = wp24.cut(wp28)
result = wp29
```

Identify the target workplane that satisfies all of these constraints:
- Among the remaining candidates, choose the one with the greatest workplane origin height.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
The custom planes (wp7, wp11, wp15, wp20, wp25) have origin z=0. Their local y-axis is along global z because normal=(2,-2,0) and xDir=(2,2,0) yield cross product (0,0,8). The center offsets: wp16 (y=-10) -> z=-10; wp21 (y=0) -> z=0; wp26 (y=10) -> z=10. wp5 has z=2. Thus greatest origin height is wp26.

{"name": "submit_text", "arguments": {"text": "wp26"}}
```
