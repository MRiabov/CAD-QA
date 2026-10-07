# row:graph:src_a7788080e2ac9568:synth:v0:parameterized_path_point_rank

- **source**: original-pool
- **hop**: 3  |  **format**: coordinate  |  **tool**: submit_coordinate
- **gold**: `[21, -8, 196]`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -87))
wp2 = wp1.splineApprox([[23, 0, 0], [23, 4, 2], [21, 8, 4], [19, 12, 6], [17, 16, 8], [14, 19, 10], [10, 21, 12], [6, 22, 14], [1, 23, 16], [-3, 23, 18], [-7, 22, 20], [-11, 20, 22], [-15, 18, 24], [-18, 15, 26], [-20, 11, 28], [-22, 7, 30], [-23, 3, 32], [-23, -1, 34], [-22, -6, 36], [-21, -10, 38], [-19, -14, 40], [-16, -17, 42], [-12, -19, 44], [-8, -21, 46], [-4, -23, 48], [0, -23, 50], [4, -23, 52], [8, -21, 54], [12, -19, 56], [16, -17, 58], [19, -14, 60], [21, -10, 62], [22, -6, 64], [23, -1, 66], [23, 3, 68], [22, 7, 70], [20, 11, 72], [18, 15, 74], [15, 18, 76], [11, 20, 78], [7, 22, 80], [3, 23, 82], [-1, 23, 84], [-6, 22, 86], [-10, 21, 88], [-14, 19, 90], [-17, 16, 92], [-19, 12, 94], [-21, 8, 96], [-23, 4, 98], [-23, 0, 100], [-23, -4, 102], [-21, -8, 104], [-19, -12, 106], [-17, -16, 108], [-14, -19, 110], [-10, -21, 112], [-6, -22, 114], [-1, -23, 116], [3, -23, 118], [7, -22, 120], [11, -20, 122], [15, -18, 124], [18, -15, 126], [20, -11, 128], [22, -7, 130], [23, -3, 132], [23, 1, 134], [22, 6, 136], [21, 10, 138], [19, 14, 140], [16, 17, 142], [12, 19, 144], [8, 21, 146], [4, 23, 148], [0, 23, 150], [-4, 23, 152], [-8, 21, 154], [-12, 19, 156], [-16, 17, 158], [-19, 14, 160], [-21, 10, 162], [-22, 6, 164], [-23, 1, 166], [-23, -3, 168], [-22, -7, 170], [-20, -11, 172], [-18, -15, 174], [-15, -18, 176], [-11, -20, 178], [-7, -22, 180], [-3, -23, 182], [1, -23, 184], [6, -22, 186], [10, -21, 188], [14, -19, 190], [17, -16, 192], [19, -12, 194], [21, -8, 196], [23, -4, 198], [23, 0, 200]], makeWire=True)
wp3 = wp2.wires()
wp4 = wp3.val()
wp5 = cq.Workplane('XZ', origin=(0, 0, -87))
wp6 = wp5.center(23, 0)
wp7 = wp6.rect(5, 8)
wp8 = wp7.sweep(wp4, isFrenet=True, multisection=True)
wp9 = cq.Workplane('XY', origin=(0, 0, -87))
wp10 = wp9.workplane(offset=-13)
wp11 = wp10.rect(26, 26)
wp12 = wp11.extrude(200)
result = wp12
```

Identify the target path point that satisfies all of these constraints:
- The target point belongs to a path in the sketch.
- The target point has a value for Z coordinate.
- From the remaining candidates, choose the 3rd item after sorting by descending Z coordinate.

Return exactly one coordinate tuple of the path point, for example `(0, 1, 3)`.
```

## Model output (trace)

```
1) The path in the sketch is the spline wire created by splineApprox on wp1 (Workplane('XY', origin=(0,0,-87))) using the given list of 3D world coordinate points. The points are on the spline. 2) The list contains 101 points with Z coordinates from 0 to 200 inclusive in increments of 2 (e.g., (23,0,0), (23,4,2), ..., (23,0,200)). Each point has a Z value. 3) Sorting all points by descending Z yields order: (23,0,200) Z=200, (23,-4,198) Z=198, (21,-8,196) Z=196, ... The 3rd item is (21, -8, 196).

{"name": "submit_coordinate", "arguments": {"value": [21, -8, 196]}}.

But note: The list includes negative numbers; it's fine.

We should also note that the splineApprox points might be interpreted relative to the workplane? Let's double-check: In CadQuery, when using a Workplane in a plane, point coordinates are interpreted as 2D if given as (x,y) and 3D if given as (x,y,z). For the 3D case, they are world coordinates. Since the workplane's origin is (0,0,-87), the world coordinates of the points are as given. So (21,-8,196) is world.

Therefore, final answer.

The target path points are the list of 3D coordinates used in the splineApprox. These points have Z values from 0 to 200 in increments of 2. Sorting by descending Z gives the order: (23,0,200), (23,-4,198), (21,-8,196), ... so the third item is (21, -8, 196).

```json
{"name": "submit_coordinate", "arguments": {"value": [21, -8, 196]}}
```
