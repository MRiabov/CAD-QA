# row:graph:src_4f329454f966c395:synth:v4:parameterized_feature_extreme

- **source**: original-pool
- **hop**: 2  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp9`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -78))
wp2 = wp1.splineApprox([[89, 0, 0], [65, 61, 6], [6, 89, 12], [-57, 68, 19], [-88, 11, 25], [-72, -52, 31], [-17, -87, 37], [48, -75, 44], [86, -22, 50], [78, 43, 56], [27, 84, 62], [-38, 80, 68], [-83, 33, 75], [-83, -33, 81], [-38, -80, 87], [27, -84, 93], [78, -43, 99], [86, 22, 106], [48, 75, 112], [-17, 87, 118], [-72, 52, 124], [-88, -11, 131], [-57, -68, 137], [6, -89, 143], [65, -61, 149], [89, 0, 155]], makeWire=True)
wp3 = cq.Workplane('XZ', origin=(0, 0, -78))
wp4 = wp3.center(89, 0)
wp5 = wp4.circle(11)
wp6 = wp5.sweep(wp2, multisection=True)
wp7 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 0, 38), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, 0, 2)))
wp8 = wp7.circle(100)
wp9 = wp8.extrude(-22)
wp10 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 0, 38), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, 0, 2)))
wp11 = wp10.circle(78)
wp12 = wp11.extrude(-22)
wp13 = wp9.cut(wp12)
wp14 = wp13.edges()
wp15 = wp14.fillet(1)
wp16 = wp6.union(wp15)
result = wp16
```

Identify the target feature that satisfies all of these constraints:
- The target feature has volume.
- Among the remaining candidates, choose the one with the greatest volume.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
Let's walk through the script step-by-step.

1. `wp1` is a Workplane in XY with origin at (0,0,-78), but nothing is built on it yet — just defines the plane.
2. `wp2` is a splineApprox wire generated from many 3D points on `wp1`'s plane, with `makeWire=True`.
3. `wp3` switches to XZ plane at (0,0,-78).
4. `wp4` centers the workplane at (89, 0).
5. `wp5` makes a circle of radius 11.
6. `wp6` sweeps that circle along `wp2` (the spline wire) — this creates a solid torus-like or helical-like tube.
7. `wp7` creates a new workplane in a custom orientation (origin (0,0,38), normal (0,0,2)).
8. `wp8` draws a circle radius 100 on that plane.
9. `wp9` extrudes it -22 in the local Z direction (so downward), making a solid disk.
10. `wp10` is the same plane as `wp7`.
11. `wp11` makes a circle radius 78.
12. `wp12` extrudes -22, making a smaller solid disk inside the first.
13. `wp13` = `wp9` minus `wp12` → a **ring** (annular disk, 100 outer radius, 78 inner radius, thickness 22).
14. `wp14` gets the edges of the ring.
15. `wp15` fillets those edges (radius 1) → the ring with rounded edges.
16. `wp16` = union of the swept tube `wp6` and the filleted ring `wp15`.

Now, the question says:
- The target feature has **volume**.
- Among remaining candidates, choose the one with greatest volume.

Candidates here are the named workplane variables.  
But many are just workplanes (no volume), like `wp1`, `wp2`, `wp3`, `wp4`, `wp5`, `wp7`, `wp8`, `wp10`, `wp11`, `wp14`.  

Those with volume:  
- `wp6` (swept tube)  
- `wp9` (solid disk, later cut)  
- `wp12` (smaller disk, later subtracted, but by itself has volume)  
- `wp13` (ring)  
- `wp15` (filleted ring)  
- `wp16` (union of tube and ring)

But among intermediate candidates with positive volume, the largest single solid is clearly **wp9** (disk radius 100, thickness 22 → volume ≈ π * 100² * 22 ≈ 691,150).  
`wp6` is a thin tube along a long path — much smaller.  
`wp15` is just the ring — less volume than the full disk.  

Therefore, the feature with greatest volume among those that are directly named is `wp9`.

Final answer:

```json
{"name": "submit_text", "arguments": {"text": "wp9"}}
```
```
