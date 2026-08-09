# row:graph:src_fff34c4e0845c7d5:synth:v5:parameterized_feature_rank

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
wp1 = cq.Workplane('XY', origin=(0, 0, -86))
wp2 = wp1.splineApprox([[46, 0, 0], [24, 39, 6], [-19, 41, 13], [-45, 6, 19], [-29, -35, 26], [14, -43, 32], [44, -11, 39], [33, 31, 46], [-9, 45, 52], [-43, 17, 59], [-37, -27, 66], [3, -46, 73], [40, -22, 79], [40, 22, 86], [3, 46, 93], [-37, 27, 100], [-43, -17, 107], [-9, -45, 114], [33, -31, 121], [44, 11, 128], [14, 43, 135], [-29, 35, 142], [-45, -6, 150], [-19, -41, 157], [24, -39, 164], [46, 0, 171]], makeWire=True)
wp3 = cq.Workplane('XZ', origin=(0, 0, -86))
wp4 = wp3.moveTo(46, 0)
wp5 = wp4.circle(9)
wp6 = wp5.sweep(wp2, multisection=True)
wp7 = cq.Workplane('XZ', origin=(0, 0, -86))
wp8 = wp7.moveTo(46, 0)
wp9 = wp8.circle(14)
wp10 = wp9.revolve(360, (0, 0), (0, 3))
wp11 = cq.Workplane('XZ', origin=(0, 0, -86))
wp12 = wp11.moveTo(46, 171)
wp13 = wp12.circle(14)
wp14 = wp13.revolve(360, (0, 0), (0, 3))
wp15 = wp6.union(wp10)
wp16 = wp15.union(wp14)
result = wp16
```

Identify the target feature that satisfies all of these constraints:
- The target feature has centroid X coordinate.
- Among the remaining candidates, choose the 3rd candidate when ordered from greatest to smallest centroid X coordinate.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
We have a series of CAD operations. The splineApprox creates a path (wp2). The circles are swept along that path (wp6) or revolved to form rings (wp10 and wp14). Then unions combine them.

The question asks: find the target feature with centroid X coordinate, and among candidates, choose the 3rd **greatest** centroid X coordinate.

We must determine which Workplane variables are "candidates" — likely those that result in separate solids before union.  
- wp6: the swept body (spline path with circle of radius 9).  
- wp10: revolved body (circle radius 14 at start of path).  
- wp14: revolved body (circle radius 14 at end of path).  

The path starts at (46, 0, 0) relative to origin (0,0,-86) and ends at (46, 0, 171) relative to origin. At the start (X=46), the revolved ring wp10 centroid X ≈ 46. At the end (X=46 also), wp14 centroid X = 46. But wait: the path goes through points with varying X, so the swept body centroid will have X somewhere between -45 and 46.  

Centroid X likely:  
- wp10: X ≈ 46  
- wp14: X ≈ 46  
- wp6: smaller because path goes negative X.  

Ordered from greatest X: both wp10 and wp14 tie. The 3rd greatest is wp6.

But we must confirm "target feature" — the constraints: "has centroid X coordinate" indicates they are filtering by X. Among remaining candidates (meaning the three solids), 3rd from greatest gives wp6. But we must return a source variable name — the variable that defines the feature. wp6 is the swept body source.

Thus answer: `wp6`.

```json
{"name": "submit_text", "arguments": {"text": "wp6"}}
```
```
