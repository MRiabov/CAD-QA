# row:graph:src_f001f6b5b14fe211:synth:v4:parameterized_contained_endpoint_metric_extreme

- **source**: original-pool
- **hop**: 5  |  **format**: coordinate  |  **tool**: submit_coordinate
- **gold**: `[-100, 33, 0]`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('YZ', origin=(-100, 0, 0))
wp2 = wp1.circle(33)
wp3 = wp2.extrude(142)
wp4 = cq.Workplane('YZ', origin=(-100, 0, 0))
wp5 = wp4.workplane(offset=142)
wp6 = wp5.circle(33)
wp7 = wp6.workplane(offset=58)
wp8 = wp7.circle(48)
wp9 = wp8.loft(combine=1)
wp10 = wp3.union(wp9)
result = wp10
```

Identify the target edge endpoint that satisfies all of these constraints:
- The target endpoint belongs to an edge in the constructed model.
- The target point is contained on an edge in the constructed model.
- The target endpoint's Y coordinate is 33.0.
- The target endpoint has a value for X coordinate.
- From the remaining candidates, choose the one with the least X coordinate.

Return exactly one coordinate tuple of the edge endpoint, for example `(0, 1, 3)`.
```

## Model output (trace)

```
The solid is built by: (1) cylinder from x=-100 to x=42, radius 33 (wp1, wp2 .circle(33), wp3 .extrude(142)); (2) frustum from x=42 radius 33 to x=100 radius 48 (wp4 same YZ plane, wp5 offset 142 to x=42, wp6 circle radius 33, wp7 offset 58 to x=100, wp8 circle radius 48, wp9 .loft(combine=1)); (3) union cylinder and frustum (wp10 = wp3.union(wp9)). The final solid has three circular edges at x=-100 (radius 33), x=42 (radius 33), and x=100 (radius 48). Their vertices (circle start points) are at (-100,33,0) for x=-100, (42,33,0) for x=42, and (100,48,0) for x=100. Only (-100,33,0) and (42,33,0) have y=33. The vertex with the least X coordinate is (-100,33,0).

{"name": "submit_coordinate", "arguments": {"value": [-100, 33, 0]}}
```
