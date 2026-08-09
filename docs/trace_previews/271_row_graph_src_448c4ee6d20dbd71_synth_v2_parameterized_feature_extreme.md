# row:graph:src_448c4ee6d20dbd71:synth:v2:parameterized_feature_extreme

- **source**: original-pool
- **hop**: 2  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp5`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -100))
wp2 = wp1.circle(33)
wp3 = wp2.workplane(offset=198)
wp4 = wp3.circle(70)
wp5 = wp4.loft(combine=True)
wp6 = cq.Workplane('XY', origin=(0, 0, -100))
wp7 = wp6.circle(20)
wp8 = wp7.workplane(offset=198)
wp9 = wp8.circle(58)
wp10 = wp9.loft(combine=True)
wp11 = wp5.cut(wp10)
wp12 = cq.Workplane('XY', origin=(0, 0, -100))
wp13 = wp12.splineApprox([[64, 0, 0], [33, 53, 8], [-26, 55, 16], [-59, 7, 24], [-37, -45, 32], [17, -54, 40], [53, -14, 47], [39, 37, 55], [-10, 51, 63], [-47, 19, 71], [-40, -29, 79], [3, -47, 87], [40, -22, 95], [39, 21, 103], [3, 43, 111], [-33, 24, 119], [-37, -15, 127], [-7, -38, 135], [27, -25, 142], [34, 9, 150], [10, 32, 158], [-21, 25, 166], [-31, -4, 174], [-12, -27, 182], [15, -23, 190], [26, 0, 198]], makeWire=True)
wp14 = wp13.val()
wp15 = cq.Workplane('XY', origin=(0, 0, -100))
wp16 = wp15.moveTo(64, 0)
wp17 = wp16.rect(13, 5)
wp18 = wp17.sweep(wp14, isFrenet=True, multisection=True)
wp19 = wp11.union(wp18, clean=True)
result = wp19
```

Identify the target feature that satisfies all of these constraints:
- The target feature has a value for volume.
- From the remaining candidates, choose the one with the largest volume.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
The script builds multiple shapes by lofting circles and sweeping a rectangle along a spline. The final result is a union of a cut (wp5 cut by wp10) and a sweep (wp18).  

- wp5 is a loft from a circle of radius 33 at z=-100 to radius 70 at z=98 (offset 198).  
- wp10 is a loft from a circle of radius 20 at z=-100 to radius 58 at z=98.  
- wp11 subtracts wp10 from wp5, giving a hollow cone-like shape.  
- wp18 sweeps a 13x5 rectangle along a spline from (64,0,-100) to (26,0,98).  
- wp19 unions wp11 and wp18.  

The question: find the target feature with a volume, then among remaining candidates pick the largest volume.  
Candidates are intermediate workplanes (e.g., wp5, wp10, wp11, wp18, wp19). The individual lofts wp5 and wp10 each have volume, but wp5 (larger radii) has larger volume than wp10. However, after cutting, wp11 = wp5 - wp10 has volume less than wp5. wp18 (sweep) volume is relatively small. wp19 = union of wp11 and wp18 has volume slightly larger than wp11 but still less than wp5 alone.  

Thus among the named variables that have a volume, **wp5** has the largest volume.

{"name": "submit_text", "arguments": {"text": "wp5"}}
```
