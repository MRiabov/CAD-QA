# row:graph:src_962a96132d3c97fb:synth:v2:parameterized_feature_extreme

- **source**: original-pool
- **hop**: 2  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp2`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -31))
wp2 = wp1.cylinder(124, 89)
wp3 = cq.Workplane('XY', origin=(0, 0, -31))
wp4 = wp3.splineApprox([[95, 0, 0], [92, 22, 5], [84, 44, 10], [70, 63, 15], [51, 79, 20], [29, 90, 25], [3, 94, 30], [-24, 91, 35], [-50, 81, 40], [-72, 62, 45], [-87, 36, 50], [-94, 6, 55], [-91, -26, 59], [-76, -56, 64], [-50, -80, 69], [-16, -93, 74], [23, -92, 79], [59, -74, 84], [85, -41, 89], [94, 3, 94], [81, 49, 99], [44, 83, 104], [-8, 94, 109], [-61, 72, 114], [-93, 19, 119], [-82, -47, 124]], makeWire=True)
wp5 = wp4.wires()
wp6 = wp5.val()
wp7 = cq.Workplane('XY', origin=(0, 0, -31))
wp8 = wp7.moveTo(95, 0)
wp9 = wp8.circle(5)
wp10 = wp9.sweep(wp6, isFrenet=True)
wp11 = wp2.union(wp10)
wp12 = cq.Workplane('XY', origin=(0, 0, -31))
wp13 = wp12.splineApprox([[-47, 82, 0], [-65, 68, 5], [-80, 51, 10], [-90, 29, 15], [-94, 5, 20], [-92, -20, 25], [-83, -45, 30], [-67, -66, 35], [-45, -83, 40], [-18, -93, 45], [12, -94, 50], [42, -85, 55], [68, -66, 59], [87, -38, 64], [94, -3, 69], [89, 33, 74], [68, 65, 79], [35, 88, 84], [-7, 94, 89], [-50, 80, 94], [-83, 46, 99], [-94, -3, 104], [-77, -54, 109], [-32, -89, 114], [30, -90, 119], [82, -47, 124]], makeWire=True)
wp14 = wp13.wires()
wp15 = wp14.val()
wp16 = cq.Workplane('XY', origin=(0, 0, -31))
wp17 = wp16.moveTo(-47, 82)
wp18 = wp17.circle(5)
wp19 = wp18.sweep(wp15, isFrenet=True)
wp20 = wp11.union(wp19)
wp21 = cq.Workplane('XY', origin=(0, 0, -31))
wp22 = wp21.splineApprox([[-47, -82, 0], [-27, -91, 5], [-4, -94, 10], [20, -92, 15], [43, -84, 20], [64, -70, 25], [80, -50, 30], [91, -25, 35], [94, 3, 40], [89, 31, 45], [75, 57, 50], [52, 79, 55], [23, 92, 59], [-11, 94, 64], [-44, 83, 69], [-73, 60, 74], [-91, 26, 79], [-93, -14, 84], [-78, -54, 89], [-44, -83, 94], [2, -95, 99], [50, -80, 104], [86, -40, 109], [93, 17, 114], [63, 71, 119], [0, 95, 124]], makeWire=True)
wp23 = wp22.wires()
wp24 = wp23.val()
wp25 = cq.Workplane('XY', origin=(0, 0, -31))
wp26 = wp25.moveTo(-47, -82)
wp27 = wp26.circle(5)
wp28 = wp27.sweep(wp24, isFrenet=True)
wp29 = wp20.union(wp28)
result = wp29
```

Identify the target feature that satisfies all of these constraints:
- The target feature has volume.
- Among the remaining candidates, choose the one with the greatest volume.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
The script constructs three sweeps along different spline wires, each starting from a 5‑radius circle, then unions them with a central cylinder.  
The cylinder (wp2) has volume. Each sweep (wp10, wp19, wp28) also has volume. Among these four solids, the cylinder’s radius is 89 and height 124 → volume ~ π·89²·124. The sweeps have a small cross‑section (radius 5) but are long (length ~ the spline’s path). The cylinder clearly has far greater volume.  
Thus the target feature is the cylinder, created at `wp2`.

```json
{"name": "submit_text", "arguments": {"text": "wp2"}}
```
```
