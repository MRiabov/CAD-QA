# row:graph:src_2567a3d79e3e7bb7:synth:v3:parameterized_feature_extreme

- **source**: original-pool
- **hop**: 2  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp9`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XZ')
wp2 = wp1.moveTo(68, 0)
wp3 = wp2.circle(32)
wp4 = wp3.revolve(350, [0, 0, 0], [0, 3, 0])
wp5 = cq.Workplane('XY')
wp6 = wp5.splineApprox([[98, 0, 0], [96, 6, 11], [89, 11, 21], [79, 15, 28], [68, 17, 31], [56, 18, 29], [45, 17, 24], [37, 17, 15], [33, 18, 4], [32, 20, -8], [35, 25, -18], [40, 32, -26], [46, 41, -30], [52, 52, -30], [55, 64, -26], [56, 73, -18], [54, 81, -8], [50, 85, 4], [43, 84, 15], [35, 80, 24], [26, 73, 29], [19, 63, 31], [12, 53, 28], [7, 45, 21], [4, 39, 11], [2, 37, 0], [-1, 39, -11], [-4, 45, -21], [-8, 54, -28], [-13, 64, -31], [-20, 75, -29], [-28, 83, -24], [-35, 88, -15], [-42, 89, -4], [-47, 85, 8], [-50, 78, 18], [-49, 68, 26], [-47, 57, 30], [-42, 45, 30], [-37, 35, 26], [-33, 28, 18], [-31, 23, 8], [-31, 20, -4], [-36, 20, -15], [-43, 21, -24], [-54, 22, -29], [-66, 23, -31], [-78, 22, -28], [-88, 19, -21], [-95, 14, -11], [-98, 9, 0], [-96, 3, 11], [-90, -3, 21], [-80, -8, 28], [-69, -11, 31], [-57, -13, 29], [-46, -13, 24], [-39, -14, 15], [-34, -15, 4], [-34, -17, -8], [-37, -21, -18], [-43, -28, -26], [-50, -37, -30], [-56, -48, -30], [-61, -58, -26], [-63, -68, -18], [-61, -76, -8], [-57, -80, 4], [-50, -80, 15], [-42, -77, 24], [-33, -70, 29], [-24, -61, 31], [-17, -52, 28], [-11, -44, 21], [-7, -39, 11], [-5, -37, 0], [-3, -39, -11], [0, -45, -21], [3, -55, -28], [7, -65, -31], [13, -76, -29], [20, -85, -24], [28, -90, -15], [34, -92, -4], [40, -89, 8], [43, -82, 18], [43, -72, 26], [42, -61, 30], [38, -49, 30], [34, -38, 26], [30, -30, 18], [29, -25, 8], [29, -23, -4], [34, -23, -15], [41, -25, -24], [52, -27, -29], [64, -28, -31], [76, -28, -28], [86, -26, -21], [94, -22, -11], [97, -17, 0]], makeWire=True)
wp7 = cq.Workplane(cq.Plane(origin=cq.Vector(98, 0, 0), xDir=cq.Vector(0, 0, 3), normal=cq.Vector(3, 0, 0)))
wp8 = wp7.rect(3, 3)
wp9 = wp8.sweep(wp6, isFrenet=True)
wp10 = wp4.cut(wp9)
wp11 = cq.Workplane(cq.Plane(origin=cq.Vector(35, 0, 0), xDir=cq.Vector(0, 0, 3), normal=cq.Vector(3, 0, 0)))
wp12 = wp11.rect(65, 23)
wp13 = wp12.extrude(-65)
wp14 = wp13.edges()
wp15 = wp14.fillet(1)
wp16 = wp15.rotate([0, 0, 0], [0, 3, 0], 0)
wp17 = wp10.union(wp16)
wp18 = wp15.rotate([0, 0, 0], [0, 3, 0], 90)
wp19 = wp17.union(wp18)
wp20 = wp15.rotate([0, 0, 0], [0, 3, 0], 180)
wp21 = wp19.union(wp20)
wp22 = wp15.rotate([0, 0, 0], [0, 3, 0], 270)
wp23 = wp21.union(wp22)
result = wp23
```

Identify the target feature that satisfies all of these constraints:
- The target feature can be described by its centroid height.
- Within the narrowed set, select the candidate with the maximum centroid height.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
The swept solid wp9 is created from a path (spline wire wp6) that reaches y-coordinates up to 85, while all other solids in the script (revolved solid wp4, rectangular blocks wp15 and its rotated copies) have centroids at y=0. Therefore, among the narrowed set of solids, wp9 has the maximum centroid height.

{"name": "submit_text", "arguments": {"text": "wp9"}}
```
