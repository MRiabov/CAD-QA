# row:graph:src_cac1d4a39cbe829e:synth:v1:parameterized_feature_rank

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
wp1 = cq.Workplane('XY', origin=(0, 0, -85))
wp2 = wp1.splineApprox([[93, 0, 0], [89, 24, 3], [81, 46, 7], [66, 65, 10], [48, 79, 14], [26, 89, 17], [2, 93, 20], [-21, 90, 24], [-44, 82, 27], [-63, 68, 31], [-78, 50, 34], [-88, 28, 38], [-92, 5, 41], [-91, -19, 44], [-83, -41, 48], [-69, -61, 51], [-52, -77, 55], [-30, -87, 58], [-7, -92, 61], [17, -91, 65], [39, -84, 68], [59, -71, 72], [76, -53, 75], [87, -32, 78], [92, -9, 82], [91, 14, 85], [85, 37, 89], [72, 58, 92], [55, 74, 95], [35, 86, 99], [12, 92, 102], [-12, 92, 106], [-35, 86, 109], [-56, 74, 113], [-73, 57, 116], [-85, 37, 119], [-91, 14, 123], [-92, -10, 126], [-86, -33, 130], [-75, -54, 133], [-59, -71, 136], [-39, -84, 140], [-16, -91, 143], [8, -92, 147], [31, -87, 150], [52, -77, 153], [70, -61, 157], [83, -41, 160], [91, -18, 164], [92, 5, 167], [88, 29, 171]], makeWire=True)
wp3 = cq.Workplane('XY', origin=(0, 0, -85))
wp4 = wp3.circle(85)
wp5 = wp4.extrude(171)
wp6 = cq.Workplane('XZ', origin=(0, 0, -85))
wp7 = wp6.transformed(offset=[93, 0, 0])
wp8 = wp7.rect(15, 15)
wp9 = wp8.sweep(wp2, isFrenet=True, multisection=True)
wp10 = wp5.union(wp9)
result = wp10
```

Identify the target feature that satisfies all of these constraints:
- The target feature has volume.
- Among the remaining candidates, choose the 2nd candidate when ordered from smallest to greatest volume.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
The script creates two solid components:  
- `wp10` is the union of `wp5` (an extruded cylinder) and `wp9` (a swept shape along the spline).  
- The workplanes themselves (`wp1`–`wp8`) are not solids; they are construction or sketch objects.  
- Among workplanes, only `wp5`, `wp9`, and `wp10` have volume.  

Sorting by volume: `wp9` (sweep) is smallest, `wp5` (cylinder) is middle, `wp10` (union) is largest.  

The 2nd smallest volume candidate is `wp5`.

```json
{"name": "submit_text", "arguments": {"text": "wp5"}}
```
```
