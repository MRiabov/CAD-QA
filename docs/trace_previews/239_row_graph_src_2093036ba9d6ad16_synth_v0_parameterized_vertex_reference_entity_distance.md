# row:graph:src_2093036ba9d6ad16:synth:v0:parameterized_vertex_reference_entity_distance

- **source**: original-pool
- **hop**: 5  |  **format**: coordinate  |  **tool**: submit_coordinate
- **gold**: `[-100, -12, 3]`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(-7, 0, -17))
wp2 = wp1.circle(92)
wp3 = wp2.circle(78)
wp4 = wp3.extrude(71)
wp5 = cq.Workplane(cq.Plane(origin=cq.Vector(85, 0, 19), xDir=cq.Vector(0, 2, 0), normal=cq.Vector(2, 0, 0)))
wp6 = wp5.circle(8)
wp7 = wp6.extrude(15)
wp8 = cq.Workplane(cq.Plane(origin=cq.Vector(85, 0, 19), xDir=cq.Vector(0, 2, 0), normal=cq.Vector(2, 0, 0)))
wp9 = wp8.polyline([[0, -8], [0, 8], [15, 2]])
wp10 = wp9.close()
wp11 = wp10.extrude(15)
wp12 = wp4.union(wp7)
wp13 = wp12.union(wp11)
wp14 = cq.Workplane(cq.Plane(origin=cq.Vector(85, 0, 19), xDir=cq.Vector(0, 2, 0), normal=cq.Vector(2, 0, 0)))
wp15 = wp14.polyline([[0, -2], [0, 2], [19, 0]])
wp16 = wp15.close()
wp17 = wp16.extrude(15)
wp18 = wp13.union(wp17)
wp19 = wp17.rotate([-7, 0, -17], [-5, 0, -17], 180)
wp20 = wp18.union(wp19)
wp21 = cq.Workplane(cq.Plane(origin=cq.Vector(85, 0, 19), xDir=cq.Vector(0, 2, 0), normal=cq.Vector(2, 0, 0)))
wp22 = wp21.polyline([[0, -2], [0, 2], [19, 2], [19, -2]])
wp23 = wp22.close()
wp24 = wp23.extrude(15)
wp25 = wp20.cut(wp24)
wp26 = cq.Workplane(cq.Plane(origin=cq.Vector(85, 0, 19), xDir=cq.Vector(0, 0, 2), normal=cq.Vector(2, 0, 0)))
wp27 = wp26.circle(2)
wp28 = wp27.extrude(-15)
wp29 = wp25.cut(wp28)
wp30 = cq.Workplane(cq.Plane(origin=cq.Vector(-98, 0, 19), xDir=cq.Vector(0, 0, 2), normal=cq.Vector(-2, 0, 0)))
wp31 = wp30.circle(2)
wp32 = wp31.extrude(-15)
wp33 = wp29.cut(wp32)
wp34 = cq.Workplane(cq.Plane(origin=cq.Vector(85, 0, 19), xDir=cq.Vector(0, 0, 2), normal=cq.Vector(2, 0, 0)))
wp35 = wp34.rect(32, 24)
wp36 = wp35.extrude(2)
wp37 = wp33.union(wp36)
wp38 = cq.Workplane(cq.Plane(origin=cq.Vector(85, 0, 19), xDir=cq.Vector(0, 0, 2), normal=cq.Vector(2, 0, 0)))
wp39 = wp38.polyline([[0, -12], [0, 12], [32, 0]])
wp40 = wp39.close()
wp41 = wp40.extrude(1)
wp42 = wp37.union(wp41)
wp43 = cq.Workplane(cq.Plane(origin=cq.Vector(-98, 0, 19), xDir=cq.Vector(0, 0, 2), normal=cq.Vector(-2, 0, 0)))
wp44 = wp43.rect(32, 24)
wp45 = wp44.extrude(2)
wp46 = wp42.union(wp45)
wp47 = cq.Workplane(cq.Plane(origin=cq.Vector(-98, 0, 19), xDir=cq.Vector(0, 0, 2), normal=cq.Vector(-2, 0, 0)))
wp48 = wp47.polyline([[0, -12], [0, 12], [32, 0]])
wp49 = wp48.close()
wp50 = wp49.extrude(1)
wp51 = wp46.union(wp50)
result = wp51
```

Identify the target vertex that satisfies all of these constraints:
- Consider vertices from the constructed model.
- The target vertex has Z coordinate equal to 3.0.
- Use as the reference the endpoint at coordinates (87.0, 9.0, 17.0).
- The target vertex exists and has a point location.
- Among the remaining candidates, choose the one whose point location is farthest from the point location of the reference endpoint.

Return exactly one coordinate tuple of the vertex, for example `(0, 1, 3)`.
```

## Model output (trace)

```
We need to parse the geometry step by step and track coordinates.

First, a large cylinder:
- wp1 at (-7, 0, -17) → wp2 circle 92 → wp3 circle 78? Actually both circles on same workplane: first circle radius 92, second circle radius 78. The second circle implies a hole (since it's on same plane). Then wp4 extrude 71 in Z.
So this creates a cylindrical ring from z=-17 to z=54 (since extrude in positive Z from that workplane), outer radius 92, inner radius 78.

Then relative to (85,0,19) workplane with xDir (0,2,0) and normal (2,0,0) – means local Z points in global X direction, local Y in global Y (since xDir=(0,2,0) gives Y direction), local X = cross(Y, Z) — but essentially this workplane is oriented so extrusion direction is +X global.  
This creates several extrusions along +X.

We have:
- wp7: circle r=8 extrude 15 → small cylinder from x=85 to x=100, centered at (85,0,19) locally → global center is (85,0,19) plus circle offset 0, so global cylinder extends from x=85 to 100, radius 8 in Y-Z.
- wp11: polyline [(0,-8),(0,8),(15,2)] close, extrude 15 → triangular prism shape along X.
- wp17: polyline [(0,-2),(0,2),(19,0)] close, extrude 15 → another triangular prism.
- wp19 rotates wp17 180° around axis through (-7,0,-17) to (-5,0,-17) — that's a vertical axis (parallel to Y) at z=-17? Actually points (-7,0,-17) and (-5,0,-17) define axis along X direction. So 180° rotation about X axis through those points would flip Z and Y signs relative to that axis.

But we have many unions, cuts, and features mirrored to the left side at (-98,0,19) as well.

The final result is symmetric with left and right features.

We need vertices with Z=3, reference endpoint (87,9,17). Compute distances.

Look at likely vertices: The right-side features have radii and triangles, some possibly with Z=3.

From wp7 circle radius 8 at x=85→100, center in Y-Z at (0,0) locally, so max Z=8, min=-8. Z=3 is possible; point (100, 0, 3) on cylinder far right. But is it a vertex? Cylinder edges are circles—vertices appear at seams or polyline endpoints.

Triangular prism wp11: vertices local: (0,-8), (0,8), (15,2) then closed – extruded in X, gives vertices at x=85 and x=100. Local y,z correspond to those points. One vertex: (85, 0, 8) to (100,0,8), (85,0,-8), (85,15,2? Wait careful: local polyline is on workplane’s XY, which is Y-Z global. Points: (0,-8) → y=0, z=-8; (0,8) → y=0,z=8; (15,2) → y=15,z=2? Actually xDir is (0,2,0) so local X maps to global Y. Local Y maps to global Z? Let's check orientation.

Workplane origin (85,0,19), xDir=(0,2,0) (points in +Y), normal=(2,0,0) (points in +X). Local X direction = xDir normalized -> global Y. Local Y = cross(normal, xDir) = cross((2,0,0),(0,2,0)) = (0,0,4) → normalized +Z. So:
- localX = global Y
- localY = global Z
Thus polyline points: (0,-8) → global (85+0, 0+0, 19-8) = (85,0,11) but wait: localY = -8 → global Z offset -8 → 19-8=11.  
Check: (0,8) → (85,0,27).  
(15,2) → localX=15 → global Y=0+15=15; localY=2 → Z=19+2=21 → (85,15,21).

So wp11 vertices: (85,0,11), (85,0,27), (85,15,21), and extruded +15 in local Z (which is global X direction) adds (+15 to x): (100,0,11), (100,0,27), (100,15,21). None have Z=3.

wp17: polyline [(0,-2),(0,2),(19,0)] → local points: (85,0,17), (85,0,21), (85+19? wait localX=19 → Y=19, localY=0 → Z=19) → (85,19,19). Extruded in X+15: (100,0,17), (100,0,21), (100,19,19). Still no Z=3.

Cut features and holes: wp24 extruded rect from local (-?), later wp36: rect(32,24) extrude 2 on plane at (85,0,19) oriented similarly. rect 32 wide in local X (global Y) and 24 in local Y (global Z). Centered? Not specified – Workplane rect defaults centered? In CadQuery rect centers on origin unless `centered=False`. Since not specified, default centered=True. So corners: local X ±16 → global Y ±16, local Y ±12 → global Z ±12. Extrude 2 in +X direction (local Z direction). So vertices at x=85 and x=87 (since extrude 2). For Z=3: local Y=3-19=-16? That's within -12 to 12? No -16 is outside. So no.

Let’s instead check left side symmetric features at (-98,0,19), same orientation but normal reversed. Mirror gives points negative X relative. Z still uses same local logic.

Probably the cylinder cut holes: wp28 circle r=2 extrude -15 (in -X from x=85). Its edges give vertices at x=85, Z=19±2? That’s Z=17 or 21. Not 3.

Look at wp41: triangle polyline [(0,-12),(0,12),(32,0)] close, extrude 1. Points: local (0,-12) → (85,0,7) because Z=19-12=7; (0,12) → (85,0,31); (32,0) → (85,32,19). Extruded to x=86 gives (86,0,7), etc. Still no Z=3.

The only opportunity for Z=3 might come from the rotated wp19 (wp17 rotated). wp17 vertices (85,0,17) and (85,0,21) and (85,19,19). Rotated 180° about axis through (-7,0,-17) to (-5,0,-17) (X direction). Rotation around X axis: (x,y,z) → (x, -y + 2*Y_axis_y?, but axis is at y=0, so reflection in Y? Actually rotation 180° about X flips sign of Y and Z relative to axis point. Axis points have y=0, z=-17, so new point: (x, -y, -z -34). Check (85,0,17) → (85, 0, -51). Z=-51. Not 3.

So far no Z=3 candidates. The reference endpoint (87,9,17) likely on some feature. Z=3 might be from combined cut intersections: maybe the intersection of cylinder (radius 8) with other shapes produces edges where Z=3? For cylinder at x=100, Z=3 is inside radius 8: y²+z²=64, with z=3 gives y=±√55≈7.416. Vertex possible from boolean? Not typical.

Given complexity, likely Z=3 vertex comes from small triangle wp41 (extrude 1) intersecting with cylinder cuts creating edge at Z=3? Hard. However, the final candidate might be (-?).

From wp35 rect (32,24) extrude 2: at x=87 (since origin 85 +2 extrude), local X=±16 → Y=±16, local Y=±12 → Z=19±12 = 7 to 31. No Z=3.

Thus Z=3 only appears if we consider bottom of something? Maybe from large ring's bottom: large ring from z=-17 to 54, so Z=3 is inside it. The ring vertices are circle approximations – but typically vertices come from polyline intersections, not smooth circles.

But given instructions, we must pick farthest from (87,9,17). Likely candidate is far left side: left feature at (-98,0,19) similar shapes, with possible vertex at x=-98, y=0, z=7 from triangle -> rotate gives something? Actually at left side wp45 rect(32,24) extrude 2 from (-98,0,19) normal (-2,0,0) → extrude in -X direction: from x=-98 to x=-100. So vertex at (-100, 16, 31) etc.

The farthest from (87,9,17) would be (-100, -16, 7) perhaps.

Check distance: sqrt((187)^2 + (25)^2 + (10)^2) ≈ 188.7.  

But Z must be 3. Among candidates with Z=3, maybe from bottom of wp45 rectangle: localY=-12 → Z=19-12=7, not 3. So no.

Wait: The plane for left side uses normal (-2,0,0) but same origin ( -98,0,19) and xDir (0,0,2). That maps localX to global Z, localY to global -Y. So localY=-12 → global Y = 0 - (-12)=12? Let's recompute:  
normal = (-2,0,0) = -X, xDir=(0,0,2)=+Z.  
localX = xDir = +Z  
localY = cross(normal, xDir) = cross((-2,0,0),(0,0,2)) = (0,4,0) → +Y. So localY=+Y.  
So rect centered: localX ±16 → global Z 19±16 → Z 3 to 35. Yes! Z=3 appears at localX=-16. So vertex at (x?, y?, z=3). Origin x=-98, extrude direction is -X (since normal -X). Extrude 2 → from x=-98 to x=-100. So vertex: x=-98 or -100, y = localY = ±12 → global Y=±12, Z = 19 + (-16) =3.  

So candidate vertices: (-98, -12, 3), (-98, 12, 3), (-100, -12, 3), (-100, 12, 3).  

Farthest from (87,9,17): compute distances:  
(-100,12,3): dx=-187, dy=3, dz=-14 → dist≈sqrt(34969+9+196)=sqrt(35174)≈187.55  
(-100,-12,3): dy=-21 → dist≈sqrt(34969+441+196)=sqrt(35606)≈188.69  
Thus (-100, -12, 3) is farthest.

Check (-98,-12,3): dy=-21, dz=-14, dx=-185 → sqrt(34225+441+196)=sqrt(34862)=186.7 — smaller.

Therefore target = (-100, -12, 3).

```json
{"name": "submit_coordinate", "arguments": {"value": [-100, -12, 3]}}
```
```
