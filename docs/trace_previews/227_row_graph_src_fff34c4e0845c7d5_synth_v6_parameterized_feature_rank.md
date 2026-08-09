# row:graph:src_fff34c4e0845c7d5:synth:v6:parameterized_feature_rank

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
- The target feature has centroid Y coordinate.
- Among the remaining candidates, choose the 3rd candidate when ordered from smallest to greatest centroid Y coordinate.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
We are asked to find the centroid Y coordinate of the target feature, then order candidates by that Y and pick the 3rd smallest.  

The script builds:  
- `wp6` — a swept body along a 3D spline (many points), cross-section circle radius 9.  
- `wp10` — revolve of circle radius 14 around Y direction (axis from (0,0) to (0,3)), starting at (46,0) on XZ plane at z=-86 → sphere-like torus at lower end.  
- `wp14` — similar revolve at (46,171) → upper end cap.  
- `wp15` = union of sweep and lower revolve.  
- `wp16` = union also with upper revolve.  

The possible candidate Workplanes in the script: `wp1, wp2, wp3, wp4, wp5, wp6, wp7, wp8, wp9, wp10, wp11, wp12, wp13, wp14, wp15, wp16`.  
We are told to consider “the target feature has centroid Y coordinate” and “[among remaining candidates choose the 3rd smallest]”. Likely they mean the features that are solids (wp6, wp10, wp14, wp15, wp16) — those have centroid Y.

- `wp10` is around z=-86, so Y ≈ -86.  
- `wp14` is around z=171-86=85, so Y ≈ 85.  
- `wp6` is a long sweep from z=-86 to z=171, centroid Y somewhere near middle.  
- `wp15` = union sweep + lower revolve → centroid lower than sweep alone.  
- `wp16` = union all three → centroid near (85 -86)/2? Actually closer to middle, slightly above sweep’s centroid.

Ordering smallest to greatest Y:  
1. wp10 (~ -86)  
2. wp15 (lower than sweep but > -86)  
3. wp6 (middle) — 3rd smallest.

Thus target is `wp6`.

```json
{"name": "submit_text", "arguments": {"text": "wp6"}}
```
```
