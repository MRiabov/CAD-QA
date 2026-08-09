# row:graph:src_ec27c2c6c3c4874c:synth:v0:parameterized_feature_rank

- **source**: original-pool
- **hop**: 2  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp11`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -68))
wp2 = wp1.circle(27)
wp3 = wp2.workplane(offset=100)
wp4 = wp3.circle(57)
wp5 = wp4.loft(combine=True)
wp6 = cq.Workplane('XY', origin=(0, 0, -68))
wp7 = wp6.circle(18)
wp8 = wp7.workplane(offset=100)
wp9 = wp8.circle(49)
wp10 = wp9.loft(combine=True)
wp11 = wp5.cut(wp10)
wp12 = cq.Workplane('XY', origin=(0, 0, -68))
wp13 = wp12.splineApprox([[16, 0, 0], [16, 3, 1], [16, 6, 2], [14, 9, 3], [13, 12, 4], [10, 15, 5], [7, 17, 6], [4, 18, 7], [1, 19, 8], [-3, 19, 9], [-7, 18, 10], [-10, 17, 11], [-13, 15, 12], [-16, 12, 13], [-19, 9, 14], [-20, 5, 15], [-21, 1, 16], [-21, -3, 17], [-21, -7, 18], [-19, -11, 19], [-17, -15, 20], [-14, -18, 21], [-11, -21, 22], [-7, -22, 23], [-2, -24, 24], [2, -24, 25], [7, -23, 26], [11, -22, 27], [16, -19, 28], [19, -16, 29], [22, -12, 30], [25, -8, 31], [26, -3, 32], [26, 2, 33], [26, 7, 34], [24, 12, 35], [22, 16, 36], [19, 21, 37], [14, 24, 38], [10, 27, 39], [4, 28, 40], [-1, 29, 41], [-7, 29, 42], [-12, 27, 43], [-17, 24, 44], [-22, 21, 45], [-26, 17, 46], [-29, 11, 47], [-31, 6, 48], [-31, 0, 49], [-31, -6, 50], [-30, -12, 51], [-27, -18, 52], [-23, -23, 53], [-19, -27, 54], [-13, -30, 55], [-7, -33, 56], [-1, -34, 57], [6, -34, 58], [12, -32, 59], [18, -30, 60], [24, -26, 61], [28, -21, 62], [32, -15, 63], [35, -9, 64], [36, -2, 65], [36, 5, 66], [35, 12, 67], [32, 18, 68], [28, 24, 69], [23, 30, 70], [17, 34, 71], [11, 37, 72], [3, 39, 73], [-4, 39, 74], [-11, 38, 75], [-19, 35, 76], [-25, 31, 77], [-31, 26, 78], [-36, 20, 79], [-39, 13, 80], [-41, 5, 81], [-41, -3, 82], [-40, -11, 83], [-38, -19, 84], [-34, -26, 85], [-29, -32, 86], [-22, -37, 87], [-15, -41, 88], [-7, -43, 89], [2, -44, 90], [10, -43, 91], [18, -41, 92], [26, -37, 93], [33, -31, 94], [38, -25, 95], [43, -17, 96], [45, -8, 97], [46, 0, 98], [46, 9, 99], [43, 18, 100]], makeWire=True)
wp14 = cq.Workplane(cq.Plane(origin=cq.Vector(16, 0, -17), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, -2, 0)))
wp15 = wp14.rect(4, 100)
wp16 = wp15.sweep(wp13, isFrenet=True, multisection=True)
wp17 = wp11.union(wp16, clean=True)
result = wp17
```

Identify the target feature that satisfies all of these constraints:
- The target feature has a value for volume.
- From the remaining candidates, choose the 2nd item after sorting by ascending volume.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
We need to identify which variables represent solid features with volume, then sort them by volume ascending and pick the 2nd one.

From the script:
- `wp5` is a loft of two circles (radius 27 and 57, height 100) → solid.
- `wp10` is a loft of two circles (radius 18 and 49, height 100) → solid.
- `wp11` = `wp5` cut `wp10` → solid (hollowed loft).
- `wp16` is a sweep of a 4×100 rectangle along a closed spline → solid.
- `wp17` = `wp11` union `wp16` → solid.

All are solids, so candidate features: `wp5`, `wp10`, `wp11`, `wp16`, `wp17`.

Volumes (estimated by reasoning):
- `wp5` (large cone-like shape): large volume.
- `wp10` (inner smaller cone): smaller than `wp5`.
- `wp11` = `wp5` minus `wp10` → volume = `wp5` - `wp10`, so smaller than `wp5` but larger than `wp10`.
- `wp16` (swept rectangle ring along long wavy closed path): relatively large volume, possibly larger than `wp5`.
- `wp17` (union) → largest of all.

Order ascending: `wp10` (smallest), then `wp11` (2nd smallest).  
So the target is `wp11`.

```json
{"name": "submit_text", "arguments": {"text": "wp11"}}
```
```
