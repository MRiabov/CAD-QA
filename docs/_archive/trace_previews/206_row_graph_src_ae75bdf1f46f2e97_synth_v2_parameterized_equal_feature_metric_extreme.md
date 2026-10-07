# row:graph:src_ae75bdf1f46f2e97:synth:v2:parameterized_equal_feature_metric_extreme

- **source**: original-pool
- **hop**: 3  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp7`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -8))
wp2 = wp1.circle(85)
wp3 = wp2.circle(70)
wp4 = wp3.extrude(16)
wp5 = cq.Workplane(cq.Plane(origin=cq.Vector(85, 0, 0), xDir=cq.Vector(0, 2, 0), normal=cq.Vector(2, 0, 0)))
wp6 = wp5.circle(7)
wp7 = wp6.extrude(15)
wp8 = cq.Workplane(cq.Plane(origin=cq.Vector(-85, 0, 0), xDir=cq.Vector(0, -2, 0), normal=cq.Vector(-2, 0, 0)))
wp9 = wp8.circle(7)
wp10 = wp9.extrude(15)
wp11 = wp4.union(wp7)
wp12 = wp11.union(wp10)
result = wp12
```

Identify the target feature that satisfies all of these constraints:
- The target feature's centroid Y coordinate is 0.0.
- The target feature has a value for centroid X coordinate.
- From the remaining candidates, choose the one with the largest centroid X coordinate.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
The script creates a central disc (wp4) from two concentric circles extruded 16 units, and two cylindrical bosses on opposite sides: wp7 from a circle at (85,0,0) extruded 15 units, and wp10 from a circle at (-85,0,0) extruded 15 units.  

The target feature needs centroid Y = 0.0 and a centroid X value. All three solids have Y=0 by symmetry. The candidates are wp4 (centroid X=0), wp7 (centroid X=85), and wp10 (centroid X=-85). Among these, the largest centroid X is 85, which belongs to wp7.

```json
{"name": "submit_text", "arguments": {"text": "wp7"}}
```
```
