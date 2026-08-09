# row:graph:src_f8d598a7cae260b8:synth:v0:parameterized_feature_extreme

- **source**: original-pool
- **hop**: 2  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp11`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -67))
wp2 = wp1.circle(27)
wp3 = wp2.workplane(offset=100)
wp4 = wp3.circle(57)
wp5 = wp4.loft(combine=True)
wp6 = cq.Workplane('XY', origin=(0, 0, -67))
wp7 = wp6.circle(18)
wp8 = wp7.workplane(offset=100)
wp9 = wp8.circle(49)
wp10 = wp9.loft(combine=True)
wp11 = wp5.cut(wp10)
wp12 = cq.Workplane('XY', origin=(0, 0, -67))
wp13 = wp12.splineApprox([[16, 0, 0], [13, 12, 4], [1, 19, 8], [-14, 15, 12], [-21, 1, 16], [-17, -15, 20], [-2, -24, 24], [16, -19, 28], [26, -3, 32], [22, 16, 36], [4, 28, 40], [-17, 24, 44], [-31, 6, 48], [-27, -18, 52], [-7, -33, 56], [18, -30, 60], [35, -9, 64], [32, 18, 68], [11, 37, 72], [-19, 35, 76], [-39, 13, 80], [-38, -19, 84], [-15, -41, 88], [18, -41, 92], [43, -17, 96], [43, 18, 100]], makeWire=True)
wp14 = cq.Workplane(cq.Plane(origin=cq.Vector(16, 0, -17), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, -2, 0)))
wp15 = wp14.rect(4, 100)
wp16 = wp15.sweep(wp13, isFrenet=True, multisection=True)
wp17 = wp11.union(wp16, clean=True)
result = wp17
```

Identify the target feature that satisfies all of these constraints:
- The target feature has a value for overall height.
- From the remaining candidates, choose the one with the least overall height.
- If candidates are still tied, use the largest edge count as the tie-break.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
The solid features are wp5, wp10, wp11, wp16, wp17. Their overall heights: wp5, wp10, wp11 are 100; wp16 and wp17 are larger. Among those with height 100, wp11 has the largest edge count (4) vs 2 for wp5 and wp10. So the target is wp11.

{"name": "submit_text", "arguments": {"text": "wp11"}}
```
