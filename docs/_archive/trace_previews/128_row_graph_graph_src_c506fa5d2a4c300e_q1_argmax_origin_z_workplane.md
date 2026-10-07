# row:graph:graph:src_c506fa5d2a4c300e:q1:argmax_origin_z_workplane

- **source**: original-pool
- **hop**: 1  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp15`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY')
wp2 = wp1.sphere(633)
wp3 = cq.Workplane(cq.Plane(origin=cq.Vector(100, 0, 0), xDir=cq.Vector(0, 0, 3), normal=cq.Vector(3, 0, 0)))
wp4 = wp3.box(1267, 1267, 1267, centered=[1, 1, 0])
wp5 = wp2.cut(wp4)
wp6 = cq.Workplane(cq.Plane(origin=cq.Vector(-100, 0, 0), xDir=cq.Vector(0, 0, -3), normal=cq.Vector(-3, 0, 0)))
wp7 = wp6.box(1267, 1267, 1267, centered=[1, 1, 0])
wp8 = wp5.cut(wp7)
wp9 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 100, 0), xDir=cq.Vector(0, 0, 3), normal=cq.Vector(0, 3, 0)))
wp10 = wp9.box(1267, 1267, 1267, centered=[1, 1, 0])
wp11 = wp8.cut(wp10)
wp12 = cq.Workplane(cq.Plane(origin=cq.Vector(0, -100, 0), xDir=cq.Vector(0, 0, -3), normal=cq.Vector(0, -3, 0)))
wp13 = wp12.box(1267, 1267, 1267, centered=[1, 1, 0])
wp14 = wp11.cut(wp13)
wp15 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 0, 100), xDir=cq.Vector(3, 0, 0), normal=cq.Vector(0, 0, 3)))
wp16 = wp15.box(1267, 1267, 1267, centered=[1, 1, 0])
wp17 = wp14.cut(wp16)
wp18 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 0, -100), xDir=cq.Vector(-3, 0, 0), normal=cq.Vector(0, 0, -3)))
wp19 = wp18.box(1267, 1267, 1267, centered=[1, 1, 0])
wp20 = wp17.cut(wp19)
result = wp20
```

Identify the target workplane that satisfies all of these constraints:
- Among the remaining candidates, choose the one with the greatest workplane origin height.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
The construction starts with a sphere of radius 633 centered at the origin.  
Six large boxes (1267×1267×1267) are cut from it, each positioned along a cardinal axis direction at ±100 from the origin. Their planes have normals pointing outward along ±X, ±Y, ±Z (with appropriate xDir adjustments).  

Each box is centered in its local XY plane (centered=[1,1,0]), meaning the box extends equally in the two in-plane directions but is flush to the plane’s origin on the third axis. The plane origins are at (±100,0,0), (0,±100,0), (0,0,±100).  

The cuts remove six “caps” from the sphere, leaving a central shape.  
The question asks for the workplane with the greatest **workplane origin height** — i.e., the highest Z-coordinate among all workplane origins.  

Among all defined workplanes, the origins with Z ≠ 0 are:  
- wp15: (0,0,100)  
- wp18: (0,0,-100)  

The greatest height is 100, from wp15.

The target variable name is `wp15`.

```json
{"name": "submit_text", "arguments": {"text": "wp15"}}
```
```
