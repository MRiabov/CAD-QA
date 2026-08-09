# row:graph:src_1fd9001060cfafdc:synth:v1:parameterized_feature_extreme

- **source**: original-pool
- **hop**: 2  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp18`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(3, -15, -70))
wp2 = wp1.circle(65)
wp3 = wp2.workplane(offset=114)
wp4 = wp3.circle(28)
wp5 = wp4.loft(combine=True)
wp6 = cq.Workplane('XY', origin=(3, -15, -70))
wp7 = wp6.circle(54)
wp8 = wp7.workplane(offset=114)
wp9 = wp8.circle(16)
wp10 = wp9.loft(combine=True)
wp11 = wp5.cut(wp10)
wp12 = cq.Workplane('XY', origin=(3, -15, -70))
wp13 = wp12.splineApprox([[65, 0, 0], [55, 35, 1], [27, 58, 2], [-8, 64, 3], [-41, 49, 5], [-60, 20, 6], [-61, -16, 7], [-43, -46, 8], [-12, -61, 9], [23, -58, 10], [50, -36, 11], [61, -4, 13], [53, 29, 14], [29, 53, 15], [-4, 60, 16], [-35, 48, 17], [-55, 22, 18], [-58, -11, 19], [-43, -40, 21], [-14, -56, 22], [18, -55, 23], [44, -37, 24], [57, -7, 25], [51, 24, 26], [30, 48, 27], [0, 56, 29], [-30, 47, 30], [-50, 24, 31], [-54, -7, 32], [-42, -35, 33], [-17, -51, 34], [13, -52, 35], [39, -37, 37], [52, -10, 38], [49, 19, 39], [31, 42, 40], [3, 52, 41], [-25, 45, 42], [-45, 25, 43], [-51, -3, 45], [-41, -30, 46], [-18, -46, 47], [9, -49, 48], [34, -36, 49], [47, -12, 50], [46, 15, 51], [31, 37, 53], [6, 47, 54], [-20, 43, 55], [-40, 25, 56], [-47, 0, 57], [-39, -25, 58], [-20, -42, 59], [6, -45, 61], [29, -35, 62], [43, -14, 63], [43, 11, 64], [30, 32, 65], [8, 43, 66], [-16, 40, 67], [-35, 25, 69], [-42, 3, 70], [-37, -20, 71], [-20, -37, 72], [3, -41, 73], [24, -33, 74], [38, -15, 75], [40, 8, 77], [29, 27, 78], [10, 38, 79], [-12, 37, 80], [-30, 25, 81], [-38, 5, 82], [-34, -16, 83], [-20, -32, 85], [0, -37, 86], [20, -31, 87], [33, -16, 88], [36, 5, 89], [28, 23, 90], [11, 34, 91], [-9, 34, 93], [-25, 24, 94], [-34, 6, 95], [-32, -12, 96], [-20, -27, 97], [-2, -33, 98], [16, -29, 99], [28, -16, 101], [32, 2, 102], [26, 19, 103], [12, 29, 104], [-6, 30, 105], [-21, 22, 106], [-29, 8, 107], [-28, -9, 109], [-19, -23, 110], [-4, -29, 111], [12, -26, 112], [24, -15, 113], [28, 0, 114]], makeWire=True)
wp14 = cq.Workplane('XZ', origin=(3, -15, -70))
wp15 = wp14.transformed(offset=[65, 0, 0], rotate=[0, 0, 0])
wp16 = wp15.polyline([[0, -5], [0, 5], [9, 0]])
wp17 = wp16.close()
wp18 = wp17.sweep(wp13, isFrenet=True, multisection=True)
wp19 = wp11.union(wp18, clean=True)
result = wp19
```

Identify the target feature that satisfies all of these constraints:
- The target feature has overall height.
- Among the remaining candidates, choose the one with the greatest overall height.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
Let’s break this down:

- `wp5` is a loft from a 65-radius circle to a 28-radius circle, height 114.
- `wp10` is a loft from a 54-radius circle to a 16-radius circle, same height.
- `wp11` = `wp5` cut by `wp10`, so the result is a hollow truncated cone shape (like a pipe with wall thickness).
- `wp18` is a sweep along a complex spline path (`wp13`). The path contains z-values up to 114 (the last point's z=114), so the sweep creates a 3D curved solid.
- `wp19` = `wp11` union `wp18`. So the two are joined.

Overall height: The loft (`wp5`/`wp10`) has height 114, the sweep (`wp18`) also reaches z=114. Both have the same height. The target must be the feature with greatest height — since they're equal, we need the one that *has* overall height. That is likely the swept feature because it's a single continuous solid along a long path, not a subtraction result.

The candidates for *source variable name* with *overall height*: The sweep `wp13` defines the path, but that’s a wire. The feature itself is `wp18`.

Therefore the greatest overall height feature is `wp18`.

```json
{"name": "submit_text", "arguments": {"text": "wp18"}}
```
```
