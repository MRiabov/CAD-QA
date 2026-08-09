# row:graph:src_076afe82034b0268:synth:v3:parameterized_feature_extreme

- **source**: original-pool
- **hop**: 2  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp16`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY')
wp2 = wp1.cylinder(200, 36)
wp3 = cq.Workplane('XY')
wp4 = wp3.cylinder(200, 32)
wp5 = wp2.cut(wp4)
wp6 = cq.Workplane('XY')
wp7 = wp6.splineApprox([[33, 0, 0], [28, 17, 8], [15, 29, 16], [-3, 33, 24], [-20, 26, 32], [-31, 12, 40], [-32, -6, 48], [-24, -22, 56], [-9, -32, 64], [9, -31, 72], [25, -22, 80], [32, -5, 88], [30, 12, 96], [19, 27, 104], [2, 33, 112], [-15, 29, 120], [-28, 17, 128], [-33, -1, 136], [-27, -18, 144], [-14, -30, 152], [4, -33, 160], [21, -26, 168], [31, -11, 176], [32, 7, 184], [23, 23, 192], [8, 32, 200]], makeWire=True)
wp8 = wp7.wires()
wp9 = wp8.val()
wp10 = cq.Workplane('XZ')
wp11 = wp10.transformed(offset=[33, 0, 100])
wp12 = wp11.rect(3, 5)
wp13 = wp12.sweep(wp9, isFrenet=True, multisection=True)
wp14 = wp5.cut(wp13)
wp15 = wp14.faces('>Z')
wp16 = wp15.edges()
wp17 = wp16.fillet(1)
wp18 = wp17.faces('<Z')
wp19 = wp18.edges()
wp20 = wp19.fillet(1)
result = wp20
```

Identify the target feature that satisfies all of these constraints:
- The target feature has centroid height.
- Among the remaining candidates, choose the one with the greatest centroid height.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
We start by analyzing the script step by step to understand the resulting solid and its features.

1. `wp2 = wp1.cylinder(200, 36)` — A cylinder of height 200 and radius 36 along Z.  
2. `wp4 = wp3.cylinder(200, 32)` — A smaller cylinder of radius 32, same height, aligned.  
3. `wp5 = wp2.cut(wp4)` — A hollow tube (wall thickness = 4).  
4. `wp7 = wp6.splineApprox(...)` — Creates a 3D spline wire from a list of points; this spirals upward from z=0 to z=200. Radius varies between ~33 and ~-33 in X and Y.  
5. `wp8 = wp7.wires()`, `wp9 = wp8.val()` — Extracts the single wire.  
6. `wp11` — Transformed Workplane offset by (33, 0, 100).  
7. `wp12 = wp11.rect(3, 5)` — A small rectangle (3x5) at (33,0,100) as a section profile.  
8. `wp13 = wp12.sweep(wp9, isFrenet=True, multisection=True)` — Sweeps this profile along the spline wire.  
9. `wp14 = wp5.cut(wp13)` — Cuts the swept solid out of the tube.  
10. `wp15 = wp14.faces('>Z')` — Selects the top-most face (highest Z).  
11. `wp16 = wp15.edges()` — Edges of that top face.  
12. `wp17 = wp16.fillet(1)` — Fillets those edges with radius 1.  
13. `wp18 = wp17.faces('<Z')` — Selects the bottom-most face.  
14. `wp19 = wp18.edges()` — Edges of bottom face.  
15. `wp20 = wp19.fillet(1)` — Fillets bottom edges.

We now are asked:  
- The *target feature* has centroid height.  
- Among remaining candidates, choose the one with **greatest centroid height**.

The “features” here likely refer to the edges or faces created/modified. The top face’s edges (wp16) are filleted first, then the bottom face’s edges.  
The centroid heights:
- Top edges (wp16): at the top of the tube (z ≈ 200).  
- Bottom edges (wp19): at z = 0.  

The top edges have greater centroid height than bottom edges. Since the fillet operation doesn’t move the centroid significantly, wp16’s edges are the highest.

Thus the variable `wp16` refers to the top edges with greatest centroid height.

```json
{"name": "submit_text", "arguments": {"text": "wp16"}}
```
```
