# row:graph:src_076afe82034b0268:synth:v3:parameterized_feature_extreme

- **source**: original-pool
- **hop**: 2  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp16`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY')
wp2 = wp1.cylinder(200, 36)
wp3 = cq.Workplane('XY')
wp4 = wp3.cylinder(200, 32)
wp5 = wp2.cut(wp4)
wp6 = cq.Workplane('XY')
wp7 = wp6.splineApprox([[33, 0, 0], [28, 17, 8], [15, 29, 16], [-3, 33, 24], [-20, 26, 32], [-31, 12, 40], [-32, -6, 48], [-24, -22, 56], [-9, -32, 64], [9, -31, 72], [25, -22, 80], [32, -5, 88], [30, 12, 96], [19, 27, 104], [2, 33, 112], [-15, 29, 120], [-28, 17, 128], [-33, -1, 136], [-27, -18, 144], [-14, -30, 152], [4, -33, 160], [21, -26, 168], [31, -11, 176], [32, 7, 184], [23, 23, 192], [8, 32, 200]], makeWire=True)
wp8 = wp7.wires()
wp9 = wp8.val()
wp10 = cq.Workplane('XZ')
wp11 = wp10.transformed(offset=[33, 0, 100])
wp12 = wp11.rect(3, 5)
wp13 = wp12.sweep(wp9, isFrenet=True, multisection=True)
wp14 = wp5.cut(wp13)
wp15 = wp14.faces('>Z')
wp16 = wp15.edges()
wp17 = wp16.fillet(1)
wp18 = wp17.faces('<Z')
wp19 = wp18.edges()
wp20 = wp19.fillet(1)
result = wp20
```

Identify the target feature that satisfies all of these constraints:
- The target feature has centroid height.
- Among the remaining candidates, choose the one with the greatest centroid height.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
The hollow cylinder (wp5) is centered with height 200, so its top face (wp15) and top edges (wp16) have centroid height z=100; bottom edges (wp19) have z=-100. The spline wire (wp9) has points from z=0 to 200, giving centroid also at z=100. Among the edges selected for filleting (wp16 and wp19), wp16 has the greater centroid height. Therefore, the target feature is wp16.

{"name": "submit_text", "arguments": {"text": "wp16"}}
```
