# row:graph:src_5a4cb92eccd9464d:synth:v0:parameterized_equal_feature_metric_extreme

- **source**: original-pool
- **hop**: 3  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp15`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -97))
wp2 = wp1.workplane(offset=80)
wp3 = wp2.circle(100)
wp4 = wp3.extrude(-13)
wp5 = cq.Workplane('XY', origin=(0, 0, -97))
wp6 = wp5.workplane(offset=80)
wp7 = wp6.circle(99)
wp8 = wp7.extrude(-13)
wp9 = wp4.cut(wp8)
wp10 = cq.Workplane('XY', origin=(0, 0, -97))
wp11 = wp10.sphere(127)
wp12 = cq.Workplane('XY', origin=(0, 0, -97))
wp13 = wp12.workplane(offset=80)
wp14 = wp13.rect(254, 254)
wp15 = wp14.extrude(-254)
wp16 = wp11.cut(wp15)
wp17 = wp16.union(wp9)
result = wp17
```

Identify the target feature that satisfies all of these constraints:
- The target feature has centroid Y coordinate equal to 0.0.
- The target feature has volume.
- Among the remaining candidates, choose the one with the greatest volume.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
The script builds solids: cylinders wp4 (r=100, h=13), wp8 (r=99, h=13), ring wp9 (wp4 cut wp8), sphere wp11 (r=127), cube wp15 (254³), spherical cap wp16 (wp11 cut wp15), union wp17 (wp16 union wp9). All are symmetric about Y, so centroid Y=0. Volumes: wp4 ≈ 408,407; wp8 ≈ 400,000; wp9 ≈ 8,124; wp11 ≈ 8.58 million; wp15 = 16,387,064; wp16 ≈ 772,000; wp17 ≈ 780,000. The greatest volume is wp15 (cube).

{"name": "submit_text", "arguments": {"text": "wp15"}}
```
