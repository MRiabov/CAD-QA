# row:graph:src_45411243056a83aa:synth:v4:parameterized_feature_extreme

- **source**: original-pool
- **hop**: 3  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp9`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 15, 0))
wp2 = wp1.box(200, 30, 88)
wp3 = wp2.edges('|Z')
wp4 = wp3.fillet(1)
wp5 = wp4.faces('<Y')
wp6 = wp5.workplane()
wp7 = wp6.pushPoints([[-60, -29], [-60, -15], [-60, 0], [-60, 15], [-60, 29], [-20, -29], [-20, -15], [-20, 0], [-20, 15], [-20, 29], [20, -29], [20, -15], [20, 0], [20, 15], [20, 29], [60, -29], [60, -15], [60, 0], [60, 15], [60, 29]])
wp8 = wp7.polygon(3, 6)
wp9 = wp8.extrude(30, combine=False)
wp10 = wp4.union(wp9)
result = wp10
```

Identify the target feature that satisfies all of these constraints:
- The target feature satisfies centroid Y coordinate less than 15.0.
- The target feature can be described by its centroid height.
- Within the narrowed set, select the candidate with the maximum centroid height.
- For any remaining tie, keep the candidate with the minimum centroid Y coordinate.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
**Hop 1**: Variables with centroid Y < 15.0: wp5 (centroid Y=0), wp9 (centroid Y=-15), wp10 (centroid Y≈14.61). wp2 and wp4 excluded (Y≥15).

**Hop 2**: All three have centroid height (z)=0, so tie in maximum.

**Hop 3**: Tie-break by minimum centroid Y: wp5 Y=0, wp9 Y=-15, wp10 Y≈14.61 → wp9 smallest.

{"name": "submit_text", "arguments": {"text": "wp9"}}
```
