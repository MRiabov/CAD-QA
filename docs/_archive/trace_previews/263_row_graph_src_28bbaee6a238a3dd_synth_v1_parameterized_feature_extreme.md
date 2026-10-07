# row:graph:src_28bbaee6a238a3dd:synth:v1:parameterized_feature_extreme

- **source**: original-pool
- **hop**: 2  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp6`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(-9, 11, -23))
wp2 = wp1.splineApprox([[59, 0, 0], [58, 7, 1], [57, 15, 2], [54, 21, 3], [51, 28, 5], [47, 34, 5], [43, 40, 6], [38, 45, 8], [32, 49, 9], [25, 53, 10], [18, 56, 11], [11, 58, 12], [4, 58, 13], [-4, 58, 14], [-11, 58, 16], [-18, 56, 16], [-25, 53, 17], [-32, 49, 19], [-38, 45, 20], [-43, 40, 21], [-47, 34, 22], [-51, 28, 23], [-54, 21, 24], [-57, 15, 25], [-58, 7, 27], [-59, 0, 27], [-58, -7, 28], [-57, -15, 30], [-54, -21, 31], [-51, -28, 32], [-47, -34, 33], [-43, -40, 34], [-38, -45, 35], [-32, -49, 36], [-25, -53, 38], [-18, -56, 38], [-11, -58, 40], [-4, -58, 41], [4, -58, 42], [11, -58, 43], [18, -56, 44], [25, -53, 45], [32, -49, 46], [38, -45, 47], [43, -40, 49], [47, -34, 49], [51, -28, 51], [54, -21, 52], [57, -15, 53], [58, -7, 54], [59, 0, 55], [58, 7, 56], [57, 15, 57], [54, 21, 58], [51, 28, 60], [47, 34, 60], [43, 40, 62], [38, 45, 63], [32, 49, 64], [25, 53, 65], [18, 56, 66], [11, 58, 67], [4, 58, 68], [-4, 58, 69], [-11, 58, 71], [-18, 56, 71], [-25, 53, 73], [-32, 49, 74], [-38, 45, 74], [-43, 40, 76], [-47, 34, 77], [-51, 28, 78], [-54, 21, 79], [-57, 15, 80], [-58, 7, 82], [-59, 0, 82], [-58, -7, 84], [-57, -15, 85], [-54, -21, 85], [-51, -28, 87], [-47, -34, 88], [-43, -40, 89], [-38, -45, 90], [-32, -49, 91], [-25, -53, 93], [-18, -56, 93], [-11, -58, 95], [-4, -58, 96], [4, -58, 97], [11, -58, 98], [18, -56, 99], [25, -53, 100], [32, -49, 101], [38, -45, 102], [43, -40, 104], [47, -34, 104], [51, -28, 106], [54, -21, 107], [57, -15, 108], [58, -7, 109], [59, 0, 110]], makeWire=True)
wp3 = cq.Workplane('XZ', origin=(-9, 11, -23))
wp4 = wp3.moveTo(59, 0)
wp5 = wp4.circle(6)
wp6 = wp5.sweep(wp2, multisection=True)
wp7 = wp6.edges()
wp8 = wp7.fillet(1)
wp9 = cq.Workplane(cq.Plane(origin=cq.Vector(45, 33, -19), xDir=cq.Vector(0, 0, 1), normal=cq.Vector(-1, -1, 0)))
wp10 = wp9.circle(1)
wp11 = wp10.extrude(1)
wp12 = wp8.union(wp11)
wp13 = cq.Workplane(cq.Plane(origin=cq.Vector(17, 64, -13), xDir=cq.Vector(0, 0, 1), normal=cq.Vector(-1, -1, 0)))
wp14 = wp13.circle(1)
wp15 = wp14.extrude(1)
wp16 = wp12.union(wp15)
wp17 = cq.Workplane(cq.Plane(origin=cq.Vector(-26, 68, -6), xDir=cq.Vector(0, 0, 1), normal=cq.Vector(1, -1, 0)))
wp18 = wp17.circle(1)
wp19 = wp18.extrude(1)
wp20 = wp16.union(wp19)
wp21 = cq.Workplane(cq.Plane(origin=cq.Vector(-59, 42, 0), xDir=cq.Vector(0, 0, 1), normal=cq.Vector(1, -1, 0)))
wp22 = wp21.circle(1)
wp23 = wp22.extrude(1)
wp24 = wp20.union(wp23)
wp25 = cq.Workplane(cq.Plane(origin=cq.Vector(-67, 0, 7), xDir=cq.Vector(0, 0, 1), normal=cq.Vector(1, 0, 0)))
wp26 = wp25.circle(1)
wp27 = wp26.extrude(1)
wp28 = wp24.union(wp27)
wp29 = cq.Workplane(cq.Plane(origin=cq.Vector(-45, -35, 13), xDir=cq.Vector(0, 0, 1), normal=cq.Vector(1, 1, 0)))
wp30 = wp29.circle(1)
wp31 = wp30.extrude(1)
wp32 = wp28.union(wp31)
result = wp32
```

Identify the target feature that satisfies all of these constraints:
- The target feature can be described by its face count.
- Within the narrowed set, select the candidate with the maximum face count.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
This script creates a spline-based 3D path and then extrudes circles of radius 1 along it using `sweep` with `multisection`.  
The spline path curves through many points, making the resulting solid a long, closed, tubular shape.  

By repeatedly calling `union`, it adds discrete small cylinders (each from a circle extruded 1 unit) at various positions along the path’s trajectory.  

The most complex and largest face count comes from the main swept body, which is `wp6` (or equivalently the result of `wp5.sweep(wp2, multisection=True)`).  
That object has many small faces from the sweeping along the spline, so it has the maximum number of faces.  

The variable assigned to this result before further unions is `wp6`.

```json
{
  "name": "submit_text",
  "arguments": {
    "text": "wp6"
  }
}
```
```
