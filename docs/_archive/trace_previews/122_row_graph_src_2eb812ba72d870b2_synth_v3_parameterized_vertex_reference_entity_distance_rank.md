# row:graph:src_2eb812ba72d870b2:synth:v3:parameterized_vertex_reference_entity_distance_rank

- **source**: original-pool
- **hop**: 5  |  **format**: coordinate  |  **tool**: submit_coordinate
- **gold**: `[-223, -222, 428]`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 1, -69))
wp2 = wp1.sphere(112)
wp3 = cq.Workplane('XY', origin=(0, 1, -69))
wp4 = wp3.sphere(105)
wp5 = wp2.cut(wp4)
wp6 = cq.Workplane('XY', origin=(0, 1, -69))
wp7 = wp6.workplane(offset=51)
wp8 = wp7.rect(446, 446)
wp9 = wp8.extrude(446)
wp10 = wp5.intersect(wp9)
wp11 = cq.Workplane('XY', origin=(0, 1, -69))
wp12 = wp11.circle(8)
wp13 = wp12.extrude(223, both=1)
wp14 = wp10.cut(wp13)
wp15 = cq.Workplane(cq.Plane(origin=cq.Vector(99, 1, -18), xDir=cq.Vector(-1, 0, 2), normal=cq.Vector(2, 0, 1)))
wp16 = wp15.center(10, 0)
wp17 = wp16.rect(4, 4)
wp18 = wp17.extrude(-30)
wp19 = wp14.union(wp18)
wp20 = cq.Workplane(cq.Plane(origin=cq.Vector(31, 95, -18), xDir=cq.Vector(0, -1, 2), normal=cq.Vector(0, 2, 1)))
wp21 = wp20.center(10, 0)
wp22 = wp21.rect(4, 4)
wp23 = wp22.extrude(-30)
wp24 = wp19.union(wp23)
wp25 = cq.Workplane(cq.Plane(origin=cq.Vector(-80, 59, -18), xDir=cq.Vector(-1, -1, 0), normal=cq.Vector(-1, 1, 1)))
wp26 = wp25.center(10, 0)
wp27 = wp26.rect(4, 4)
wp28 = wp27.extrude(-30)
wp29 = wp24.union(wp28)
wp30 = cq.Workplane(cq.Plane(origin=cq.Vector(-80, -58, -18), xDir=cq.Vector(1, -1, 0), normal=cq.Vector(-1, -1, 1)))
wp31 = wp30.center(10, 0)
wp32 = wp31.rect(4, 4)
wp33 = wp32.extrude(-30)
wp34 = wp29.union(wp33)
wp35 = cq.Workplane(cq.Plane(origin=cq.Vector(31, -94, -18), xDir=cq.Vector(0, -1, -2), normal=cq.Vector(0, -2, 1)))
wp36 = wp35.center(10, 0)
wp37 = wp36.rect(4, 4)
wp38 = wp37.extrude(-30)
wp39 = wp34.union(wp38)
result = wp39
```

Identify the target vertex that satisfies all of these constraints:
- The target vertex is one of the model vertices.
- The target vertex's Z coordinate is 428.0.
- Use as the reference the added-material region with bounding-box center coordinates (-64.268678, -56.410814, -26.660254).
- The target vertex exists and has a point location.
- From the remaining candidates, choose the 4th item after sorting by descending distance to the reference entity.

Return exactly one coordinate tuple of the vertex, for example `(0, 1, 3)`.
```

## Model output (trace)

```
We have a spherical shell (outer radius 112, inner radius 105) at origin (0,1,-69), intersected with a cube extruded 446 in Z starting at Z = 51 offset from that origin. That origin plus offset gives cube from Z = -18 to 428. So the shell is cut down to a cubical bounding region.

Added-material regions are the six small rectangular prisms (4x4 cross-section) extruded -30 along their local z, placed on angled planes at the given coordinates. Their bounding box center is given as (-64.268678, -56.410814, -26.660254). That's near one of these prisms, likely the one at (-80, -58, -18) with plane normal (-1,-1,1) and extrusion -30.

We need to find model vertices with Z = 428.0. The top face of the cube is at Z = 428 (since origin Z=-69 + offset 51 gives -18, plus extrude 446 gives 428). The intersection with the sphere will produce curved edges but the top face is flat at Z=428. The added prism near the given reference may have vertices that coincide with the top face? But the prisms extrude -30 from their local plane, so they are below the top face if their z is around -18 local. They won't reach 428.

Thus, target vertices with Z=428 are on the top face of the cube, where the spherical shell has been cut. The cube corners? Actually the cube is 446x446 in X/Y and 446 in Z, so the top face corners are at (±223, ±223, 428) relative to (0,1,-69) giving y around 1±223. Those are the vertices. 

Now we sort by distance to the reference point (-64.268678, -56.410814, -26.660254). Compute distances to four corners:

Top face corners:
(-223, 1-223= -222, 428) 
(-223, 1+223=224, 428)
(223, -222, 428)
(223, 224, 428)

Distances to ref:
1) (-223, -222): dx=-158.731, dy=-165.589, dz=454.660 → sqrt(25195+27420+206716)≈~520
2) (-223, 224): dx=-158.731, dy=280.411 → dy²≈78630, sum ~311k → ~558
3) (223, -222): dx=287.269 → dx²≈82524, sum ~314k → ~560
4) (223, 224): dx=287.269, dy=280.411 → sum ~82600+78630+206716≈367946 → ~607

Sorted descending: (223,224), (223,-222), (-223,224), (-223,-222). 4th is (-223, -222). So coordinate (-223, -222, 428).

But verify y: origin y=1, so corner y=1-223=-222. Yes.

Final answer: (-223, -222, 428).

{"name": "submit_coordinate", "arguments": {"value": [-223, -222, 428]}}
```
