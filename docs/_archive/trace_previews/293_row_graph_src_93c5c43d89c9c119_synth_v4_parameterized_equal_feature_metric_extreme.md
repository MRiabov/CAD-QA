# row:graph:src_93c5c43d89c9c119:synth:v4:parameterized_equal_feature_metric_extreme

- **source**: original-pool
- **hop**: 3  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp13`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(-33, 0, 0))
wp2 = wp1.box(133, 98, 129)
wp3 = cq.Workplane('XY', origin=(-33, 0, 0))
wp4 = wp3.line(293, 0)
wp5 = cq.Workplane('YZ', origin=(-33, 0, 0))
wp6 = wp5.circle(22)
wp7 = wp6.sweep(wp4, multisection=0)
wp8 = wp7.translate([-146, 0, 0])
wp9 = wp2.intersect(wp8)
wp10 = cq.Workplane('YZ', origin=(-33, 0, 0))
wp11 = wp10.polyline([[22, -4], [22, 4], [49, 0]])
wp12 = wp11.close()
wp13 = wp12.extrude(133, combine=0)
wp14 = wp9.union(wp13)
wp15 = cq.Workplane('YZ', origin=(-33, 0, 0))
wp16 = wp15.polyline([[10, 19], [3, 22], [21, 65]])
wp17 = wp16.close()
wp18 = wp17.extrude(133, combine=0)
wp19 = wp14.union(wp18)
wp20 = cq.Workplane('YZ', origin=(-33, 0, 0))
wp21 = wp20.polyline([[-15, 16], [-20, 10], [-49, 35]])
wp22 = wp21.close()
wp23 = wp22.extrude(133, combine=0)
wp24 = wp19.union(wp23)
wp25 = cq.Workplane('YZ', origin=(-33, 0, 0))
wp26 = wp25.polyline([[-20, -10], [-15, -16], [-49, -35]])
wp27 = wp26.close()
wp28 = wp27.extrude(133, combine=0)
wp29 = wp24.union(wp28)
wp30 = cq.Workplane('YZ', origin=(-33, 0, 0))
wp31 = wp30.polyline([[3, -22], [10, -19], [21, -65]])
wp32 = wp31.close()
wp33 = wp32.extrude(133, combine=0)
wp34 = wp29.union(wp33)
result = wp34
```

Identify the target feature that satisfies all of these constraints:
- The target feature has centroid height equal to 0.0.
- The target feature has overall height.
- Among the remaining candidates, choose the one with the smallest overall height.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
We need to find the center of mass (centroid) height of each feature? Actually "centroid height equal to 0.0" likely means the centroid's z-coordinate is 0. Since all workplanes are XY, YZ, etc., but origin is (-33,0,0) for most. The script builds shapes by extruding polylines on YZ plane along X? Actually careful: The script uses various workplanes: wp1 is XY, then box(133,98,129) - that gives a box of dimensions 133 (x?) Actually box(length, width, height) by default: length along x, width along y, height along z. So box(133,98,129) gives a box centered at origin? Since wp1 origin is (-33,0,0) and workplane XY, the box is centered at that origin? Actually box() creates a box centered at the workplane's origin? In CadQuery, box() creates a box centered at the workplane's origin? The documentation: box(length, width, height) - the center of the box is at the origin? Actually I think it's centered on the workplane's origin. So the box's center is at (-33,0,0). So its centroid z=0? Yes, because it's in XY plane, so z coordinate of centroid is 0.

But then we have many subsequent operations: wp7 is a sweep of a circle along a line? Actually wp4 is a line from (0,0) to (293,0) on XY plane? But wp3 is XY workplane at (-33,0,0) so the line is in XY plane? Then wp5 is YZ plane at (-33,0,0) and circle of radius 22, then sweep along wp4? That would create a cylinder? But then wp7 is translated by [-146,0,0]. Then intersect with wp2? That gives an intersection of the box and the swept cylinder? Actually wp9 = wp2.intersect(wp8). Then many unions of extruded triangles on YZ plane. These are extruded along X? The extrude with combine=0, so they are separate solids. But then they are unioned with wp9. So the final result is a composite solid.

We need to identify the target feature that has centroid height equal to 0.0. "Centroid height" likely means the z-coordinate of the centroid. Since the overall coordinate system is global? The workplanes have origins at (-33,0,0). So the centroid of the box (wp2) is at (-33,0,0) because centered? Actually box dimensions: 133 length (x), 98 width (y), 129 height (z). The center is at wp1 origin? So centroid z = 0.

But then we have other features: the swept cylinder? Its centroid? The sweep is along a line from (0,0) to (293,0) in XY plane? Actually wp4 is a line from (0,0) to (293,0) on XY plane. But the workplane wp3 is XY with origin (-33,0,0). So the line is in the XY plane, but its start is at (0,0) relative to that origin? Actually line(x,y) draws from current point to (x,y) relative to current? In CadQuery, line(x,y) draws a line from current point to (x,y) in the workplane's coordinate system. Typically after creating a workplane, the current point is at (0,0) in that workplane's coordinate system. So wp4 is a line from (0,0) to (293,0) in the XY plane at origin (-33,0,0). So the line is along the x-direction? But the workplane is XY, so x and y axes? Actually XY plane: x and y are the horizontal axes, z is normal. So line(293,0) means a line from (0,0) to (293,0) in the XY plane, so it's along the x-axis (local x direction). Then the sweep: wp5 is YZ plane at (-33,0,0), so a circle of radius 22 in the YZ plane. Then sweep along the line wp4? But sweep expects a path. The path is a wire? Actually wp4 is a line? In CadQuery, you can use a wire as a path. But wp4 is a line? Actually wp4 is a Workplane object after line? It's a vector? The code: wp4 = wp3.line(293, 0) - this returns a Workplane with the line as the current wire? Actually line() returns a Workplane with the current wire being the line? Then sweep: wp7 = wp6.sweep(wp4, multisection=0) - this sweeps the circle along the line. The result is a cylinder? But the circle is in YZ plane, and the path is along the x-direction? Actually the path is in the XY plane? The sweep direction is along the path. So the resulting solid is a cylinder oriented along the local x-axis? But the circle is in YZ, so the cylinder's axis is along the x-direction. The centroid of that cylinder? It will be somewhere along the line. The line starts at (0,0) relative to the workplane origin? Actually the sweep's path starts at the origin of the workplane? The circle is on YZ plane at (-33,0,0). The line is drawn from the origin of wp3, which is also (-33,0,0). So the line starts at (-33,0,0) and goes to (293-33? Actually careful: The line is drawn in the coordinate system of the workplane. The workplane's local origin is (-33,0,0). So the line's start point in global coordinates is (-33,0,0), and end point is (-33+293, 0, 0) = (260,0,0). So the line is along the global x-axis. The circle is also at (-33,0,0) in the YZ plane. So the sweep creates a cylinder from x=-33 to x=260, radius 22, centered on the x-axis. Its centroid is at the midpoint of the line: x = ( -33 + 260)/2 = 113.5? Actually -33 + 293/2 = -33 + 146.5 = 113.5? Wait 293 length, so midpoint at -33 + 146.5 = 113.5. But then wp7 is translated by [-146,0,0], so new centroid x = 113.5 - 146 = -32.5. So centroid z = 0? The cylinder is axis along x, so its centroid z is 0 because it's symmetric about the x-axis? Actually the circle is centered at (0,0) in the YZ plane, so the cylinder's centroid is along the x-axis, and its y and z centroids are 0. So centroid z = 0 for the cylinder as well.

Now the other features: extrusions of polylines on YZ plane. These are extruded along the x-direction? The extrude(133) with combine=0 creates a solid extruded along the normal of the workplane? The workplane is YZ, so the normal is the x-axis. So each extrusion is a prismatic solid extending along the x-direction from the workplane's origin? Actually extrude(133) extrudes the face (the polyline) by 133 units in the direction normal to the workplane. Since the workplane is YZ, normal is along the x-axis. The workplane origin is (-33,0,0), so the extrusion starts at x=-33? But careful: The polyline is drawn on the YZ plane, so its coordinates are in the YZ plane local to that workplane. The workplane's origin is at (-33,0,0) in global coordinates. So the polyline points are given in the local YZ plane coordinates (y,z). The extrusion will go in the positive x direction? By default, extrude() extrudes in the direction of the workplane's normal? Actually in CadQuery, extrude(distance) extrudes the face in the direction of the workplane's normal (positive direction) by the given distance. So these extrusions will extend from x=-33 to x=-33+133 = 100? So they are blocks of height 133 in x.

Now, which of these features have centroid height (z-coordinate) equal to 0? The box and the cylinder have centroid z=0. The triangular extrusions? Their polylines are given in YZ plane, so their centroids in the YZ plane might not be at z=0. Let's compute approximate centroids of the triangles.

The triangles are closed polylines that form triangles. The extrude will create a prism with that triangle cross-section extruded along x. The centroid of the prism will be at the center of the triangle in the YZ plane, and at the midpoint in x (x=-33 + 66.5 = 33.5? Actually extrusion length 133, so midpoint x = -33 + 66.5 = 33.5). So the centroid's z-coordinate will be the z-coordinate of the triangle's centroid in the YZ plane.

We need to find which feature has centroid height = 0.0. So among the unioned parts, the ones that are extrusions, their centroid z might not be zero. Let's compute the centroids of the triangles:

First triangle: wp10-polyline([[22, -4], [22, 4], [49, 0]]) then close. That's a triangle with vertices: (22, -4), (22, 4), (49, 0). The centroid of a triangle is average of vertices: ( (22+22+49)/3, (-4+4+0)/3 ) = (93/3, 0/3) = (31, 0). So y=31, z=0. So centroid z=0.

Second triangle: wp15-polyline([[10,19], [3,22], [21,65]]) -> vertices: (10,19), (3,22), (21,65). Centroid: ( (10+3+21)/3, (19+22+65)/3 ) = (34/3, 106/3) ≈ (11.33, 35.33). So z=35.33, not 0.

Third triangle: wp20-polyline([[-15,16], [-20,10], [-49,35]]) -> vertices: (-15,16), (-20,10), (-49,35). Centroid: ( (-15-20-49)/3, (16+10+35)/3 ) = (-84/3, 61/3) = (-28, 20.33). z=20.33.

Fourth triangle: wp25-polyline([[-20,-10], [-15,-16], [-49,-35]]) -> vertices: (-20,-10), (-15,-16), (-49,-35). Centroid: ( (-20-15-49)/3, (-10-16-35)/3 ) = (-84/3, -61/3) = (-28, -20.33). z=-20.33.

Fifth triangle: wp30-polyline([[3,-22], [10,-19], [21,-65]]) -> vertices: (3,-22), (10,-19), (21,-65). Centroid: ( (3+10+21)/3, (-22-19-65)/3 ) = (34/3, -106/3) ≈ (11.33, -35.33). z=-35.33.

So only the first triangle (wp13) and the cylinder (wp7) and the box (wp2) have centroid z=0. Also the cylinder's centroid z=0 as argued. So multiple candidates.

Now the constraint: "Among the remaining candidates, choose the one with the smallest overall height." "Overall height" likely means the overall height in the z-direction? Or the total height of the feature? Usually "height" refers to the dimension along the z-axis. The box has height 129 (z dimension). The cylinder has diameter 44? Actually radius 22, so diameter 44, so its height in z is 44? But it's a cylinder, its extent in z is from -22 to 22, so height 44. The first triangle extrusion: its cross-section in YZ plane has a triangle with vertices at y=22, y=-4? Actually its vertices: y coordinates: 22, 22, 49? Wait the triangle's vertices in YZ: (y,z) = (22, -4), (22, 4), (49, 0). So the y-range is from 22 to 49, so width 27. The z-range is from -4 to 4, so height 8. So the extrusion's overall height in z-direction is 8 (since it's extruded along x, so its z extent is from min z to max z of the triangle). So the first triangle has overall height 8. The cylinder has overall height 44. The box has overall height 129. So the smallest overall height among these candidates is the triangle with height 8. But wait, we need to check if the cylinder's height is 44? Actually cylinder's radius 22, so it extends from z=-22 to z=22, so height 44. So the triangle is smaller.

Thus the target feature with centroid height 0 and smallest overall height is the first triangle extrusion, which is wp13? Actually wp13 = wp12.extrude(133, combine=0) - that is the extrusion of that triangle. But the variable name wp13 refers to the Workplane after extrusion? The question asks: "Return exactly one source variable name, for example `wp7`." So we need to output the variable name of the feature that satisfies the constraints. Which variable corresponds to that triangle? The triangle is created by wp10, then wp11, wp12, then wp13 is the extrusion. But the feature is the solid resulting from wp13. However, later it is unioned into wp14 etc. But the variable name wp13 is the result of extrusion. So we can output wp13.

But we must ensure that the centroid height is indeed 0.0. Yes, the triangle's centroid in z is 0. So wp13 is a candidate. Also wp2 (box) and wp7 (cylinder) have centroid z=0. Among these, the smallest overall height is wp13 (height 8). So answer is wp13.

But double-check: Are there any other features? The cylinder wp7 is translated, but its centroid z is 0. So yes.

Thus the answer is wp13.

But note: The triangle is extruded with combine=0, so it's a separate solid. The final result is a union of many solids. So the target feature is that individual solid.

Thus final answer: wp13.

The target feature must have centroid height 0.0. The box (wp2) has centroid z=0 and height 129. The cylinder (wp7) created by sweeping a circle along a line also has centroid z=0 and height 44. The first extruded triangle (wp13) has vertices (22,-4), (22,4), (49,0) giving centroid z=0 and overall height 8 (z-range -4 to 4). Among these, the smallest overall height is 8, so the answer is wp13.

```json
{"name": "submit_text", "arguments": {"text": "wp13"}}
```
```
