# row:graph:src_9395d21214e13847:synth:v0:parameterized_feature_extreme

- **source**: original-pool
- **hop**: 2  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp8`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -87))
wp2 = wp1.splineApprox([[23, 0, 0], [17, 16, 8], [1, 23, 16], [-15, 18, 24], [-23, 3, 32], [-19, -14, 40], [-4, -23, 48], [12, -19, 56], [22, -6, 64], [20, 11, 72], [7, 22, 80], [-10, 21, 88], [-21, 8, 96], [-21, -8, 104], [-10, -21, 112], [7, -22, 120], [20, -11, 128], [22, 6, 136], [12, 19, 144], [-4, 23, 152], [-19, 14, 160], [-23, -3, 168], [-15, -18, 176], [1, -23, 184], [17, -16, 192], [23, 0, 200]], makeWire=True)
wp3 = wp2.wires()
wp4 = wp3.val()
wp5 = cq.Workplane('XZ', origin=(0, 0, -87))
wp6 = wp5.center(23, 0)
wp7 = wp6.rect(5, 8)
wp8 = wp7.sweep(wp4, isFrenet=True, multisection=True)
wp9 = cq.Workplane('XY', origin=(0, 0, -87))
wp10 = wp9.workplane(offset=-13)
wp11 = wp10.rect(26, 26)
wp12 = wp11.extrude(200)
result = wp12
```

Identify the target feature that satisfies all of these constraints:
- The target feature has a value for centroid Y coordinate.
- From the remaining candidates, choose the one with the least centroid Y coordinate.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
The spline path is symmetric in Y, so the swept solid (wp8) has centroid Y=0. The extruded block (wp12) and all other shapes also have centroid Y=0. All shapes have the same Y value, but the sweep is the only feature created by a sweep operation. Among the remaining shapes, the sweep's centroid Y is the least (equal to 0, but it is the target).

{"name": "submit_text", "arguments": {"text": "wp8"}}
```
