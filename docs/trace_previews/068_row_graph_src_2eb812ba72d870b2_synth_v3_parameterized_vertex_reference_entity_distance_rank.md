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
Let's reason step by step through the construction.

1. **Sphere shell**  
   wp1 and wp2 create a sphere of radius 112 centered at (0, 1, -69).  
   wp3 and wp4 create a sphere of radius 105 at the same center.  
   wp5 = wp2.cut(wp4) gives a spherical shell of thickness 7.

2. **Intersect with cube**  
   wp7 offsets workplane by 51 along Z (so plane is at Z = -69 + 51 = -18).  
   wp8 creates a 446×446 square centered at (0, 1) in that plane.  
   wp9 extrudes it 446 along Z, making a cube from Z=-18 to Z=428 (since start is -18, extrusion goes 446 upward).  
   wp10 = wp5.intersect(wp9) restricts sphere shell to this cube.

3. **Cut central cylinder**  
   wp12 creates circle radius 8 at (0, 1) in XY plane (origin is same as before).  
   wp13 extrudes both sides by 223, so from Z=-292 to Z=154 (since center Z = -69).  
   wp14 = wp10.cut(wp13) removes the central vertical cylinder.

4. **Six rectangular prism additions on faces**  
   The remaining blocks (wp15–wp38) are six rectangular prisms (4×4 cross-section, extruded -30 along custom normals) at different positions.

   The reference bounding-box center given is `(-64.268678, -56.410814, -26.660254)`.  
   That likely corresponds to one of these added blocks.

5. **Finding target vertex**  
   The Z coordinate of the target vertex is 428.0.  
   The top face of the big cube is at Z=428 (since -18 + 446 = 428). So the vertex lies on that top face.  
   We sort all vertices on that top face by descending distance to that reference center, pick the 4th.

Given six blocks, only some will intersect the top face Z=428. These are the long extrusions from the cube — but the added rectangular prisms have extrusion -30 along tilted normals, so they are below Z=428 except possibly edges.

Actually, the top face Z=428 is part of the original intersect volume (wp10) after cutting cylinder and adding prisms; the prisms are added below, so top Z=428 vertices come from the original cube top.  

Our candidates: vertices at Z=428 from final shape.  
Given the reference center is around (-64, -56, -26), the farthest top vertices from there will be opposite corners.

Those top corners coordinates (from cube, ignoring the cylinder cut) are:  
Cube goes from X=-223 to 223, Y=-222 to 224 (since center Y=1).  
Top Z=428 vertices:  
(±223, 1±223, 428).

Sort by distance from (-64.27, -56.41, -26.66):

Distances squared roughly:  
- (223, 224, 428): dx=287.27, dy=280.41, dz=454.66 → large  
- (223, -222, 428): dx=287.27, dy=165.59, dz=454.66 → smaller  
- (-223, 224, 428): dx=-158.73, dy=280.41, dz=454.66  
- (-223, -222, 428): dx=-158.73, dy=-165.59, dz=454.66 → closest among corners

Descending order:  
1. (223, 224, 428)  
2. (-223, 224, 428)  
3. (223, -222, 428)  
4. (-223, -222, 428)  

4th item = (-223, -222, 428).

Thus the target vertex is (-223, -222, 428).

```json
{"name": "submit_coordinate", "arguments": {"value": [-223, -222, 428]}}
```
```
