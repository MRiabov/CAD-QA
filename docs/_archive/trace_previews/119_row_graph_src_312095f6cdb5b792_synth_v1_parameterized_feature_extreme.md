# row:graph:src_312095f6cdb5b792:synth:v1:parameterized_feature_extreme

- **source**: original-pool
- **hop**: 3  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp40`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -16))
wp2 = wp1.cylinder(64, 77)
wp3 = cq.Workplane('XY', origin=(0, 0, -16))
wp4 = wp3.cylinder(64, 62)
wp5 = wp2.cut(wp4)
wp6 = cq.Workplane('XY', origin=(0, 0, -16))
wp7 = wp6.polyline([[62, -2], [77, -2], [77, 2], [62, 2]])
wp8 = wp7.close()
wp9 = wp8.extrude(64)
wp10 = wp9.rotate([0, 0, -16], [0, 0, -14], 0)
wp11 = wp5.union(wp10)
wp12 = cq.Workplane(cq.Plane(origin=cq.Vector(75, 16, -16), xDir=cq.Vector(0, 2, 0), normal=cq.Vector(2, 0, 0)))
wp13 = wp12.circle(5)
wp14 = wp13.extrude(24)
wp15 = wp11.union(wp14)
wp16 = cq.Workplane(cq.Plane(origin=cq.Vector(75, -16, -16), xDir=cq.Vector(0, 2, 0), normal=cq.Vector(2, 0, 0)))
wp17 = wp16.circle(5)
wp18 = wp17.extrude(24)
wp19 = wp15.union(wp18)
wp20 = cq.Workplane('XY', origin=(0, 0, -16))
wp21 = wp20.polyline([[62, -2], [77, -2], [77, 2], [62, 2]])
wp22 = wp21.close()
wp23 = wp22.extrude(64)
wp24 = wp23.rotate([0, 0, -16], [0, 0, -14], 180)
wp25 = wp19.union(wp24)
wp26 = cq.Workplane(cq.Plane(origin=cq.Vector(-75, -16, -16), xDir=cq.Vector(0, -2, 0), normal=cq.Vector(-2, 0, 0)))
wp27 = wp26.circle(5)
wp28 = wp27.extrude(24)
wp29 = wp25.union(wp28)
wp30 = cq.Workplane(cq.Plane(origin=cq.Vector(-75, 16, -16), xDir=cq.Vector(0, -2, 0), normal=cq.Vector(-2, 0, 0)))
wp31 = wp30.circle(5)
wp32 = wp31.extrude(24)
wp33 = wp29.union(wp32)
wp34 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 77, -16), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, 2, 0)))
wp35 = wp34.circle(20)
wp36 = wp35.extrude(-15)
wp37 = wp33.cut(wp36)
wp38 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 77, 16), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, 2, 0)))
wp39 = wp38.circle(5)
wp40 = wp39.extrude(-202)
wp41 = wp37.cut(wp40)
wp42 = cq.Workplane(cq.Plane(origin=cq.Vector(0, -77, -16), xDir=cq.Vector(-2, 0, 0), normal=cq.Vector(0, -2, 0)))
wp43 = wp42.circle(20)
wp44 = wp43.extrude(-15)
wp45 = wp41.cut(wp44)
wp46 = cq.Workplane(cq.Plane(origin=cq.Vector(0, -77, 16), xDir=cq.Vector(-2, 0, 0), normal=cq.Vector(0, -2, 0)))
wp47 = wp46.circle(5)
wp48 = wp47.extrude(-202)
wp49 = wp45.cut(wp48)
result = wp49
```

Identify the target feature that satisfies all of these constraints:
- The target feature has centroid height greater than -16.0.
- The target feature has centroid Y coordinate.
- Among the remaining candidates, choose the one with the smallest centroid Y coordinate.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
The main cylindrical shell (wp5, wp11) and rectangular prisms (wp9, wp24) have centroid z=16, Y=0. Cylinders oriented along X (wp14, wp18, wp28, wp32) have centroid z=-16, excluded. Short cut cylinders (wp36, wp44) also have z=-16. Long cut cylinders wp40 (origin (0,77,16), extrude -202) spans y from -125 to 77, centroid y = -24, z=16. wp48 (origin (0,-77,16), extrude -202) spans y from -77 to 125, centroid y = 24, z=16. Only wp40 and wp48 have z > -16; among them wp40 has smallest Y (-24). Therefore target feature is wp40.

{"name": "submit_text", "arguments": {"text": "wp40"}}
```
