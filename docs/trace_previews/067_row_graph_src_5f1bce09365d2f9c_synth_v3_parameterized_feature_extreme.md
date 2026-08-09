# row:graph:src_5f1bce09365d2f9c:synth:v3:parameterized_feature_extreme

- **source**: original-pool
- **hop**: 2  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp12`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XZ')
wp2 = wp1.moveTo(71, 0)
wp3 = wp2.circle(29)
wp4 = wp3.revolve(360, [0, 0, 0], [0, 3, 0])
wp5 = cq.Workplane('XY')
wp6 = wp5.splineApprox([[96, 0, 0], [96, 2, 2], [95, 5, 3], [95, 7, 5], [94, 10, 6], [94, 12, 8], [93, 14, 9], [92, 16, 11], [91, 18, 12], [89, 21, 13], [88, 23, 15], [86, 25, 16], [85, 26, 17], [83, 28, 18], [81, 30, 19], [79, 31, 20], [77, 33, 21], [75, 34, 22], [73, 36, 23], [71, 37, 23], [69, 38, 24], [66, 39, 24], [64, 40, 25], [62, 40, 25], [59, 41, 25], [57, 41, 25], [55, 42, 25], [53, 42, 25], [50, 43, 25], [48, 43, 24], [46, 43, 24], [44, 43, 23], [42, 43, 23], [40, 43, 22], [38, 43, 21], [36, 43, 20], [34, 43, 19], [32, 43, 18], [30, 43, 17], [29, 43, 16], [27, 43, 15], [25, 42, 13], [24, 42, 12], [23, 42, 11], [21, 42, 9], [20, 42, 8], [19, 42, 6], [17, 43, 5], [16, 43, 3], [15, 43, 2], [14, 43, 0], [13, 44, -2], [12, 44, -3], [11, 45, -5], [10, 45, -6], [9, 46, -8], [8, 47, -9], [7, 48, -11], [5, 48, -12], [4, 49, -13], [3, 50, -15], [2, 51, -16], [1, 52, -17], [-1, 53, -18], [-2, 55, -19], [-4, 56, -20], [-5, 57, -21], [-7, 58, -22], [-8, 59, -23], [-10, 61, -23], [-12, 62, -24], [-14, 63, -24], [-16, 64, -25], [-18, 65, -25], [-20, 66, -25], [-22, 67, -25], [-24, 68, -25], [-26, 69, -25], [-29, 70, -25], [-31, 70, -24], [-33, 71, -24], [-36, 71, -23], [-38, 72, -23], [-41, 72, -22], [-43, 72, -21], [-46, 72, -20], [-48, 72, -19], [-51, 72, -18], [-53, 71, -17], [-56, 71, -16], [-58, 70, -15], [-60, 69, -13], [-62, 68, -12], [-65, 67, -11], [-67, 66, -9], [-69, 65, -8], [-71, 63, -6], [-73, 62, -5], [-74, 60, -3], [-76, 58, -2], [-77, 56, 0]], makeWire=True)
wp7 = wp6.wires()
wp8 = wp7.val()
wp9 = cq.Workplane('XZ')
wp10 = wp9.moveTo(96, 0)
wp11 = wp10.rect(9, 29)
wp12 = wp11.sweep(wp8, isFrenet=True)
wp13 = wp4.cut(wp12)
result = wp13
```

Identify the target feature that satisfies all of these constraints:
- The target feature has edge count.
- Among the remaining candidates, choose the one with the greatest edge count.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
wp4 is a torus; wp8 is a single spline wire; wp11 is a rectangle with 4 edges. wp12 is the sweep of wp11 along wp8, forming a rectangular-cross-section solid with 12 edges. wp13 is wp4 cut by wp12, producing a torus with a hole; its edge count is lower than that of the swept solid. Among the candidates, wp12 has the greatest edge count.

{"name": "submit_text", "arguments": {"text": "wp12"}}
```
