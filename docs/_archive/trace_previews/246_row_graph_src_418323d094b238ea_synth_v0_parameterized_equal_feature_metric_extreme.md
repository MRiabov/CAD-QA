# row:graph:src_418323d094b238ea:synth:v0:parameterized_equal_feature_metric_extreme

- **source**: original-pool
- **hop**: 3  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp4`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY')
wp2 = wp1.box(173, 200, 110)
wp3 = wp2.faces('>Y')
wp4 = wp3.edges('|Z')
wp5 = wp4.chamfer(35)
wp6 = wp5.faces('<Y')
wp7 = wp6.edges('|Z')
wp8 = wp7.fillet(5)
wp9 = wp8.faces('>Z')
wp10 = wp9.edges()
wp11 = wp10.fillet(5)
wp12 = wp11.faces('<Z')
wp13 = wp12.edges()
wp14 = wp13.fillet(5)
wp15 = cq.Workplane('XY')
wp16 = wp15.moveTo(-52, 100)
wp17 = wp16.lineTo(-86, 65)
wp18 = wp17.lineTo(-86, 100)
wp19 = wp18.close()
wp20 = wp19.extrude(55, combine=0)
wp21 = wp14.union(wp20)
wp22 = cq.Workplane('XY')
wp23 = wp22.moveTo(52, 100)
wp24 = wp23.lineTo(86, 65)
wp25 = wp24.lineTo(86, 100)
wp26 = wp25.close()
wp27 = wp26.extrude(55, combine=0)
wp28 = wp21.union(wp27)
wp29 = wp28.faces('>Z')
wp30 = wp29.workplane()
wp31 = wp30.pushPoints([[61, 74], [-61, 74], [-61, -74], [61, -74]])
wp32 = wp31.cskHole(41, 80, 135, depth=None)
result = wp32
```

Identify the target feature that satisfies all of these constraints:
- The target feature has overall height equal to 110.0.
- The target feature has centroid Y coordinate.
- Among the remaining candidates, choose the one with the greatest centroid Y coordinate.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
Let’s unpack step-by-step.

- The overall model height is 110.0 (from `wp2.box(173,200,110)`), so any feature with that height means it is a full-height shape or a face/edge derived on top/bottom faces.
- Among features, we need centroid Y coordinate—and then highest Y.
- The box’s Y range: from -100 to +100, centroid Y = 0.
- The chamfer at `wp5` reduces edges at Y=100, but doesn’t shift centroid of the whole part.
- The fillets at `wp8`, `wp11`, `wp14` only round edges.
- `wp20` and `wp27` are extrusions from the XY plane up 55 in Z, located near Y=100 and Y=65 (triangles). Their centroids are around Y ≈ 82.5.
- After union (`wp28`), top face Z=110 is at `wp29`.
- `wp30` workplane on top yields 4 holes at Y=74 and Y=-74.
- The holes’ centroid Y = 0 (symmetric). The highest centroid among all distinct added features comes from `wp20` and `wp27`.
- Between them, they are symmetric. Highest centroid Y is from the top portion of the triangular extrusions at Y ≈ 82.5.

But the question says: target feature overall height 110 — only full-height candidates: the original box or derived faces/edges that span full height. Among those, edges `|Z` are vertical and have height 110.

Edges from `wp3` (`>Y`) → `|Z` are vertical edges at the top-front Y face. These have Y=100. Those edges appear at `wp4`.

Thus: wp4 edges are Y=100, height=110 — highest Y centroid among full-height features.

Answer: `wp4`.

```json
{"name": "submit_text", "arguments": {"text": "wp4"}}
```
```
