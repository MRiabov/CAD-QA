# row:graph:src_a86494cf88397ae4:synth:v4:parameterized_path_point_reference_entity_distance

- **source**: original-pool
- **hop**: 5  |  **format**: coordinate  |  **tool**: submit_coordinate
- **gold**: `[44, 69, 15]`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -91))
wp2 = wp1.splineApprox([[81, 0, 0], [71, 39, 7], [44, 69, 15], [5, 81, 22], [-35, 74, 29], [-66, 48, 36], [-81, 10, 44], [-76, -30, 51], [-52, -63, 58], [-15, -80, 65], [25, -77, 73], [59, -56, 80], [79, -20, 87], [79, 20, 94], [59, 56, 102], [25, 77, 109], [-15, 80, 116], [-52, 63, 123], [-76, 30, 131], [-81, -10, 138], [-66, -48, 145], [-35, -74, 153], [5, -81, 160], [44, -69, 167], [71, -39, 174], [81, 0, 182]], makeWire=True)
wp3 = cq.Workplane('XZ', origin=(0, 0, -91))
wp4 = wp3.moveTo(81, 0)
wp5 = wp4.circle(9)
wp6 = wp5.sweep(wp2)
wp7 = wp6.rotate([0, 0, -91], [0, 0, -87], 180)
wp8 = wp6.union(wp7)
wp9 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 0, -45), xDir=cq.Vector(-3, 0, 1), normal=cq.Vector(-1, 0, -3)))
wp10 = wp9.rect(203, 19)
wp11 = wp10.extrude(2, both=True)
wp12 = wp8.union(wp11)
result = wp12
```

Identify the target path point that satisfies all of these constraints:
- The target point belongs to a path in the sketch.
- The target path point's X coordinate is 44.0.
- Use as the reference the added-material region with centroid coordinates (0.0, 0.0, 0.0).
- The target path point exists and has a point location.
- Among the remaining candidates, choose the one whose point location is closest to the solid centroid of the reference added-material region.

Return exactly one coordinate tuple of the path point, for example `(0, 1, 3)`.
```

## Model output (trace)

```
**Hop 1:** The path is defined by `wp1.splineApprox([...], makeWire=True)`. Points with X=44 are `(44,69,15)` and `(44,-69,167)`.

**Hop 2:** The reference "added-material region" has centroid `(0,0,0)`. Distances computed in the local coordinate frame (the same frame as the path points) are used.

**Hop 3:** Distance from `(44,69,15)` to `(0,0,0)` is ~83.2; from `(44,-69,167)` is ~186.0.

**Hop 4:** Only these two candidates satisfy X=44 and belong to the path. The first is closer to the reference centroid.

**Hop 5:** The target path point is `(44,69,15)`.

{"name": "submit_coordinate", "arguments": {"value": [44, 69, 15]}}
```
