# row:graph:src_d593f529e4ece0ed:synth:v1:parameterized_equal_feature_metric_extreme

- **source**: original-pool
- **hop**: 3  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp13`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('YZ', origin=(-100, 0, 0))
wp2 = wp1.circle(30)
wp3 = wp2.extrude(200)
wp4 = cq.Workplane('YZ', origin=(-100, 0, 0))
wp5 = wp4.circle(13)
wp6 = wp5.extrude(200)
wp7 = wp3.cut(wp6)
wp8 = cq.Workplane('YZ', origin=(-100, 0, 0))
wp9 = wp8.workplane(offset=21)
wp10 = wp9.circle(15)
wp11 = wp10.circle(13)
wp12 = wp11.extrude(3)
wp13 = wp7.cut(wp12)
wp14 = cq.Workplane('YZ', origin=(-100, 0, 0))
wp15 = wp14.workplane(offset=103)
wp16 = wp15.circle(15)
wp17 = wp16.circle(13)
wp18 = wp17.extrude(3)
wp19 = wp13.cut(wp18)
result = wp19
```

Identify the target feature that satisfies all of these constraints:
- The target feature matches the overall height value 60.0.
- The target feature can be described by its centroid X coordinate.
- Within the narrowed set, select the candidate with the maximum centroid X coordinate.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
1. Features with overall height 60.0 (diameter 60) are those with outer radius 30: wp3 (solid cylinder), wp7 (tube after first cut), wp13 (tube after left groove cut), wp19 (tube after both grooves). 2. Their centroid X coordinates: wp3 and wp7 are symmetric about x=0 → centroid X=0. wp13 removes material only from left side (x=-79 to -76) → centroid shifts right, >0. wp19 removes material from both left and right sides (x=-79 to -76 and x=3 to 6) → centroid shift is less than wp13. 3. Maximum centroid X is achieved by wp13.

{"name": "submit_text", "arguments": {"text": "wp13"}}
```
