# row:graph:src_508d59eca5f1151e:synth:v0:parameterized_path_point_extreme

- **source**: original-pool
- **hop**: 3  |  **format**: coordinate  |  **tool**: submit_coordinate
- **gold**: `[-59, -23, 26]`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY')
wp2 = wp1.splineApprox([[96, 0, 0], [75, 19, 25], [46, 25, 20], [31, 29, 2], [26, 41, -16], [22, 67, -26], [6, 94, -8], [-16, 83, 22], [-24, 52, 23], [-28, 34, 7], [-37, 27, -12], [-59, 23, -26], [-90, 11, -16], [-90, -11, 16], [-59, -23, 26], [-37, -27, 12], [-28, -34, -7], [-24, -52, -23], [-16, -83, -22], [6, -94, 8], [22, -67, 26], [26, -41, 16], [31, -29, -2], [46, -25, -20], [75, -19, -25], [96, 0, 0]], makeWire=True)
wp3 = cq.Workplane('XZ')
wp4 = wp3.moveTo(96, 0)
wp5 = wp4.circle(4)
wp6 = wp5.sweep(wp2, isFrenet=True, multisection=True)
result = wp6
```

Identify the target path point that satisfies all of these constraints:
- The target point belongs to a path in the sketch.
- The target point has a value for Z coordinate.
- From the remaining candidates, choose the one with the largest Z coordinate.
- If candidates are still tied, use the least distance to the global origin as the tie-break.

Return exactly one coordinate tuple of the path point, for example `(0, 1, 3)`.
```

## Model output (trace)

```
We need to identify the target path point from the list of points used in splineApprox. The constraints: belongs to a path in the sketch (the spline points are the path). The target point has a value for Z coordinate (all points have Z). From remaining candidates (all points), choose the one with the largest Z coordinate. Then if tie, least distance to origin.

Let's list all points from the splineApprox list:

[96,0,0], [75,19,25], [46,25,20], [31,29,2], [26,41,-16], [22,67,-26], [6,94,-8], [-16,83,22], [-24,52,23], [-28,34,7], [-37,27,-12], [-59,23,-26], [-90,11,-16], [-90,-11,16], [-59,-23,26], [-37,-27,12], [-28,-34,-7], [-24,-52,-23], [-16,-83,-22], [6,-94,8], [22,-67,26], [26,-41,16], [31,-29,-2], [46,-25,-20], [75,-19,-25], [96,0,0]

Now find largest Z: Look at Z values: 0,25,20,2,-16,-26,-8,22,23,7,-12,-26,-16,16,26,12,-7,-23,-22,8,26,16,-2,-20,-25,0. The maximum Z is 26? Actually we have two 26s: [22,67,26]? Wait: [22,67,-26] has -26, not 26. Let's re-check: point 9? Actually list:

Index: (I'll number)
1: [96,0,0] z=0
2: [75,19,25] z=25
3: [46,25,20] z=20
4: [31,29,2] z=2
5: [26,41,-16] z=-16
6: [22,67,-26] z=-26
7: [6,94,-8] z=-8
8: [-16,83,22] z=22
9: [-24,52,23] z=23
10: [-28,34,7] z=7
11: [-37,27,-12] z=-12
12: [-59,23,-26] z=-26
13: [-90,11,-16] z=-16
14: [-90,-11,16] z=16
15: [-59,-23,26] z=26
16: [-37,-27,12] z=12
17: [-28,-34,-7] z=-7
18: [-24,-52,-23] z=-23
19: [-16,-83,-22] z=-22
20: [6,-94,8] z=8
21: [22,-67,26] z=26
22: [26,-41,16] z=16
23: [31,-29,-2] z=-2
24: [46,-25,-20] z=-20
25: [75,-19,-25] z=-25
26: [96,0,0] z=0

So maximum Z is 26? Actually there are two points with Z=26: point 15: [-59,-23,26] and point 21: [22,-67,26]. Also point 2 has 25, point 9 has 23, point 8 has 22, etc. So largest Z = 26. So candidates: [-59,-23,26] and [22,-67,26]. Then tie-break: least distance to global origin (0,0,0). Compute distances:

For [-59,-23,26]: distance = sqrt(59^2 + 23^2 + 26^2) = sqrt(3481 + 529 + 676) = sqrt(4686) ≈ 68.45
For [22,-67,26]: distance = sqrt(22^2 + 67^2 + 26^2) = sqrt(484 + 4489 + 676) = sqrt(5649) ≈ 75.16

So the smaller distance is the first one. Therefore target point is (-59, -23, 26). But careful: The question says "Return exactly one coordinate tuple of the path point". So we output as array: [-59, -23, 26]. Must be in list format. Also note that the script uses splineApprox with makeWire=True, which creates a wire from those points; the path is that wire. So the points are indeed the sketch points.

Thus answer: [-59, -23, 26].

Now emit tool call.

{"name": "submit_coordinate", "arguments": {"value": [-59, -23, 26]}}
```
