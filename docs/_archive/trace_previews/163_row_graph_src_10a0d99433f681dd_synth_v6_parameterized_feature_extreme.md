# row:graph:src_10a0d99433f681dd:synth:v6:parameterized_feature_extreme

- **source**: original-pool
- **hop**: 2  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp13`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY')
wp2 = wp1.box(150, 200, 189)
wp3 = cq.Workplane('XY')
wp4 = wp3.box(139, 189, 179)
wp5 = wp2.cut(wp4)
wp6 = wp5.faces('>X')
wp7 = wp6.workplane()
wp8 = wp7.pushPoints([[-63, 0], [-47, 0], [-32, 0], [-16, 0], [0, 0], [16, 0], [32, 0], [47, 0], [63, 0]])
wp9 = wp8.rect(11, 95)
wp10 = wp9.cutBlind(-150)
wp11 = wp10.faces('<X')
wp12 = wp11.edges('>Z')
wp13 = wp12.chamfer(3)
wp14 = cq.Workplane('XY')
wp15 = wp14.splineApprox([[52, 0, -72], [38, 36, -66], [3, 52, -61], [-33, 40, -55], [-52, 7, -49], [-42, -31, -43], [-10, -51, -37], [28, -44, -32], [51, -13, -26], [46, 25, -20], [16, 50, -14], [-22, 47, -9], [-49, 19, -3], [-49, -19, 3], [-22, -47, 9], [16, -50, 14], [46, -25, 20], [51, 13, 26], [28, 44, 32], [-10, 51, 37], [-42, 31, 43], [-52, -7, 49], [-33, -40, 55], [3, -52, 61], [38, -36, 66], [52, 0, 72]], makeWire=True)
wp16 = cq.Workplane('XY')
wp17 = wp16.workplane(offset=-72)
wp18 = wp17.moveTo(52, 0)
wp19 = wp18.circle(17)
wp20 = wp19.sweep(wp15, isFrenet=True)
wp21 = wp13.cut(wp20)
result = wp21
```

Identify the target feature that satisfies all of these constraints:
- The target feature has a value for edge count.
- From the remaining candidates, choose the one with the largest edge count.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
We start with a large box `wp2` (150×200×189), then cut a smaller box `wp4` (139×189×179) from it. This leaves a shell-like shape.

Then from the right face (`>X`), we create a workplane, push nine points along Y=0, draw 11×95 rectangles at each, and cut blind by -150. This creates nine slots through the wall.

Next, from the left face (`<X`), we take the top edge (`>Z`) and chamfer it by 3.

Finally, we construct a spline-based sweep: a circle of radius 17 swept along a 3D spline, cutting the entire shape. That sweep removes material from the slotted wall.

We now want the feature with the largest edge count among the candidates. The variable names represent intermediate results: `wp13` is the shape after chamfer, `wp21` is after subtracting the sweep. The sweep removes some edges from `wp13`, so `wp13` likely has more edges.

Comparing all candidates that have edge count values, `wp13` is before the final cut, so it retains all edges from the chamfer and slots; `wp21` loses edges where the sweep removes material. The largest edge count is in `wp13`.

Thus the answer is `wp13`.

```json
{"name": "submit_text", "arguments": {"text": "wp13"}}
```
```
