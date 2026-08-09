# row:graph:src_5f1bce09365d2f9c:synth:v1:parameterized_feature_extreme

- **source**: original-pool
- **hop**: 2  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp12`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XZ')
wp2 = wp1.moveTo(71, 0)
wp3 = wp2.circle(29)
wp4 = wp3.revolve(360, [0, 0, 0], [0, 3, 0])
wp5 = cq.Workplane('XY')
wp6 = wp5.splineApprox([[96, 0, 0], [96, 2, 2], [95, 5, 3], [95, 7, 5], [94, 10, 6], [94, 12, 8], [93, 14, 9], [92, 16, 11], [91, 18, 12], [89, 21, 13], [88, 23, 15], [86, 25, 16], [85, 26, 17], [83, 28, 18], [81, 30, 19], [79, 31, 20], [77, 33, 21], [75, 34, 22], [73, 36, 23], [71, 37, 23], [69, 38, 24], [66, 39, 24], [64, 40, 25], [62, 40, 25], [59, 41, 25], [57, 41, 25], [55, 42, 25], [53, 42, 25], [50, 43, 25], [48, 43, 24], [46, 43, 24], [44, 43, 23], [42, 43, 23], [40, 43, 22], [38, 43, 21], [36, 43, 20], [34, 43, 19], [32, 43, 18], [30, 43, 17], [29, 43, 16], [27, 43, 15], [25, 42, 13], [24, 42, 12], [23, 42, 11], [21, 42, 9], [20, 42, 8], [19, 42, 6], [17, 43, 5], [16, 43, 3], [15, 43, 2], [14, 43, 0], [13, 44, -2], [12, 44, -3], [11, 45, -5], [10, 45, -6], [9, 46, -8], [8, 47, -9], [7, 48, -11], [5, 48, -12], [4, 49, -13], [3, 50, -15], [2, 51, -16], [1, 52, -17], [-1, 53, -18], [-2, 55, -19], [-4, 56, -20], [-5, 57, -21], [-7, 58, -22], [-8, 59, -23], [-10, 61, -23], [-12, 62, -24], [-14, 63, -24], [-16, 64, -25], [-18, 65, -25], [-20, 66, -25], [-22, 67, -25], [-24, 68, -25], [-26, 69, -25], [-29, 70, -25], [-31, 70, -24], [-33, 71, -24], [-36, 71, -23], [-38, 72, -23], [-41, 72, -22], [-43, 72, -21], [-46, 72, -20], [-48, 72, -19], [-51, 72, -18], [-53, 71, -17], [-56, 71, -16], [-58, 70, -15], [-60, 69, -13], [-62, 68, -12], [-65, 67, -11], [-67, 66, -9], [-69, 65, -8], [-71, 63, -6], [-73, 62, -5], [-74, 60, -3], [-76, 58, -2], [-77, 56, 0]], makeWire=True)
wp7 = wp6.wires()
wp8 = wp7.val()
wp9 = cq.Workplane('XZ')
wp10 = wp9.moveTo(96, 0)
wp11 = wp10.rect(9, 29)
wp12 = wp11.sweep(wp8, isFrenet=True)
wp13 = wp4.cut(wp12)
result = wp13
```

Identify the target feature that satisfies all of these constraints:
- The target feature has centroid Y coordinate.
- Among the remaining candidates, choose the one with the greatest centroid Y coordinate.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
We are asked: "Identify the target feature that satisfies all of these constraints: - The target feature has centroid Y coordinate. - Among the remaining candidates, choose the one with the greatest centroid Y coordinate." Wait, need to parse the question exactly. The problem statement: "Identify the target feature that satisfies all of these constraints: - The target feature has centroid Y coordinate. - Among the remaining candidates, choose the one with the greatest centroid Y coordinate." This seems incomplete. Possibly it's a multiple choice? But the instruction says: "Return exactly one source variable name, for example `wp7`." So we need to output a variable name indicating which feature is the target. The likely meaning: Among the features created in the script (maybe the resulting solids?), find the one with the greatest centroid Y coordinate? But there are many intermediate objects. The script builds a revolve (wp4) from a circle, then a sweep (wp12) on a spline, then cuts wp4 with wp12 to get result. So result is a solid after cut. The question: "Identify the target feature that satisfies all of these constraints: - The target feature has centroid Y coordinate. - Among the remaining candidates, choose the one with the greatest centroid Y coordinate." This is ambiguous. Possibly it's a test from a multiple-choice where we need to pick the feature (like a face or edge) that has the highest Y centroid? But the script only produces one final solid (result) and perhaps intermediate shapes like wp4, wp12. The phrase "target feature" likely refers to a specific geometric entity (like a face or a solid) that is a candidate among a set. But the script only creates a few solids: wp4 (revolved solid), wp12 (swept solid), and result (cut). There might be multiple features (faces) on the result. However, the answer format expects a variable name like wp7. That suggests the target is a Workplane or a Wire? wp7 is a wire (wp8 is the actual wire). Possibly we are to pick the wire that was used for the sweep? But the constraints involve centroid Y coordinate. Let's read the script carefully.

Steps:
- wp1 = Workplane('XZ')
- wp2 = wp1.moveTo(71,0)
- wp3 = wp2.circle(29) -> creates a circle of radius 29 centered at (71,0) on XZ plane.
- wp4 = wp3.revolve(360, [0,0,0], [0,3,0]) -> revolves the circle around axis from (0,0,0) to (0,3,0) i.e., y-axis? Actually [0,3,0] direction, so axis is Y-axis. So it creates a torus-like shape? Actually a circle revolved around an axis not through its center gives a torus. The circle is centered at (71,0) on XZ plane, revolve around Y-axis, so it's a torus with major radius 71? Wait: The circle is in XZ plane, center at (71,0) relative to origin? Actually XZ plane: (x,z) coordinates. moveTo(71,0) sets starting point, then circle(29) creates a circle centered at that point? In CadQuery, circle(radius) draws a circle centered at current point? Typically, circle(radius) draws a circle with center at current point. So center at (71,0) in XZ plane. Then revolve around Y-axis (axis from (0,0,0) to (0,3,0) which is y-axis direction). So the circle is offset from axis by 71 units in x-direction, radius 29. So it's a torus with minor radius 29, major radius 71? Actually major radius is distance from axis to circle center = 71, minor radius = 29. So wp4 is a torus.

- Then wp5 = cq.Workplane('XY') -> new workplane on XY plane.
- wp6 = wp5.splineApprox(list of 3D points, makeWire=True) -> creates a spline wire through those points. The points list seems to be a 3D curve. The points are given as triplets (x,y,z). Many points. It's a spline through them.
- wp7 = wp6.wires() -> extracts wires from the splineApprox? Actually wp6 is a Workplane object after splineApprox, which contains a wire? Then wp7 = wp6.wires() returns a Wire object? Actually wires() returns a list of wires? In CadQuery, wires() on a Workplane returns a list of wires. Then wp8 = wp7.val() takes the first wire. So wp8 is a single wire.
- Then wp9 = cq.Workplane('XZ') again.
- wp10 = wp9.moveTo(96,0)
- wp11 = wp10.rect(9,29) -> creates a rectangle centered? Actually rect(width, height) draws a rectangle centered at current point? In CadQuery, rect(w,h) draws a rectangle with lower-left? Actually rect(width, height, centered=True by default) draws centered at current point. So center at (96,0) in XZ plane, width 9 (x-direction?), height 29 (z-direction?). So a rectangle of size 9x29.
- wp12 = wp11.sweep(wp8, isFrenet=True) -> sweeps the rectangle along the wire wp8 (the spline). This creates a swept solid.
- wp13 = wp4.cut(wp12) -> subtracts the swept solid from the torus.
- result = wp13 -> final solid.

So the final result is a torus with a cutout along the spline path.

Now the question: "Identify the target feature that satisfies all of these constraints: - The target feature has centroid Y coordinate. - Among the remaining candidates, choose the one with the greatest centroid Y coordinate." This is cryptic. Possibly there is a list of candidate features (like faces) and we need to find the one with the highest centroid Y? But the answer expects a variable name like wp7. That suggests that wp7 is a candidate. Or maybe we need to output the name of the variable that holds the feature? But there are many variables: wp1..wp13, result. Which ones are "features"? Likely the ones that are Workplane objects? But they are not features; they are workplanes. Perhaps the "target feature" refers to the resulting solid after cut? But that is result. However, the constraints mention "centroid Y coordinate" and "greatest centroid Y coordinate among remaining candidates". Possibly the script creates multiple objects? Actually only one final solid. Could it be that we need to consider the faces of the result? But the answer expects a variable name.

Alternatively, maybe the problem is that we need to identify which of the workplanes (like wp4, wp12, etc.) has the highest centroid Y coordinate? But wp4 is a solid, wp12 is a solid, result is a solid. Their centroids? Let's compute approximate: wp4 is a torus centered at origin? Actually torus revolves around Y axis, so its centroid is at origin? Not exactly, because a torus symmetric about axis, centroid is on axis, so centroid Y=0? Possibly. wp12 is a swept solid along a spline that goes from near (96,0,0) to (-77,56,0) (last point). The spline points have varying y values from 0 to 56, so the swept solid will have a centroid with some positive Y. The cut result will have a hole, but centroid might shift. But we need to compare "among the remaining candidates". Perhaps we have multiple features like "the face that is the cut surface"? Not clear.

Given the instruction: "Return exactly one source variable name, for example `wp7`." That indicates the answer is a variable name from the script. Which variable is likely? The question mentions "target feature" and "centroid Y coordinate". Perhaps the script is part of a larger problem where we have to identify a specific face or edge. But the answer format is a variable name. Maybe we need to output the variable that holds the wire that is used for the sweep? That wire (wp8) is a spline. Its centroid Y coordinate? But a wire is not a solid; centroid of a wire is not well-defined as a volume centroid. However, CadQuery might have centroid for a wire as the average of points? Possibly.

Let's think differently: The question might be from a test where the task is to find which workplane (or intermediate object) has the greatest centroid Y coordinate among a set of objects that are "candidates". But the script only has a few solids: wp4 (torus), wp12 (swept solid), result (cut). Among these, which has the greatest centroid Y? The torus is symmetric about the Y axis, so its centroid Y is likely 0 (since revolve around Y-axis, volume symmetric). The swept solid goes from y=0 to y=56, so its centroid Y is positive. The result is the torus with a cut, so its centroid Y might be slightly negative or near zero? Actually the cut removes some volume from the torus. The swept solid is mostly in the region where y>0 (spline points have y from 0 to 56, but note some later points have negative y? Actually look at the list: first points: (96,0,0), then (96,2,2), etc. up to (0,? Actually later points: (13,44,-2), (12,44,-3) ... (-77,56,0). So the spline goes from (96,0,0) to (-77,56,0). The y values increase to 56, then at the end is 56? Actually last point: (-77,56,0). So y is non-negative throughout? Check: there are points like (15,43,2) etc. All y are positive until near the end? Actually there is (14,43,0) y=43, then (13,44,-2) y=44, ... (-4,56,-20) y=56, etc. All y positive. So the spline is entirely in y>=0. So the swept solid is entirely in y>=0 (since the sweep profile is a rectangle in XZ plane at y=0 initially? Actually the profile is on XY? Wait: The sweep: wp10.moveTo(96,0) on XZ plane? Actually wp9 = Workplane('XZ'), then moveTo(96,0) so point (x=96, z=0) in XZ plane. Then rect(9,29) creates a rectangle centered at (96,0) with width along x? Actually on XZ plane, rect(width=9, height=29) means width along x, height along z. So the profile is a rectangle in the XZ plane, centered at (96,0,0) with extents: x from (96-4.5) to (96+4.5), z from -14.5 to 14.5. This rectangle is then swept along the wire wp8. Since the wire starts at (96,0,0) (first point of spline list), the sweep will start at that rectangle. The wire goes to points with y>0, so the swept solid will be entirely in y>=0 (since the wire's first point has y=0). So the swept solid's centroid Y is positive, likely around some average. The torus (wp4) is symmetric, so its centroid Y=0. The cut (result) removes that swept solid from the torus, so the resulting solid has a hole where the swept solid was. The torus originally had volume both above and below y=0 (since it's symmetric), but the swept solid only existed in y>=0. So the cut removes some material from the upper part of the torus, making the resulting centroid Y shift negative (since more material remains below). So the result's centroid Y is negative. Therefore, among wp4, wp12, result, the one with the greatest centroid Y is wp12 (the swept solid). But wp12 is a solid, not a "feature"? Could be.

But the question says "target feature". Possibly they mean the result of the cut? But then "among the remaining candidates" suggests there are multiple features (like faces or edges) and we need to pick one that has the greatest centroid Y. Perhaps the script creates multiple solids? Actually only one final solid. However, note that there are intermediate workplanes that are not solids: wp4 is a Workplane that contains a solid, wp12 is a Workplane that contains a solid. In CadQuery, a Workplane object can represent a solid. So we could consider wp4, wp12, and result (which is wp13) as candidate solids. Their centroids: wp4 centroid Y=0, wp12 centroid Y positive, result centroid Y negative. So the greatest Y centroid is wp12. So answer would be `wp12`. But the example answer given is `wp7`. So maybe it's not that.

Alternatively, maybe we need to consider the wires? wp7 and wp8 are wires. The spline wire has points with y from 0 to 56, so its centroid Y (average of points) is positive. But which variable? wp7 is a list of wires? Actually wp7 = wp6.wires() returns a list. Then wp8 = wp7.val() is the first wire. Among these, the wire itself has a centroid? The centroid of a wire might be the average of its vertices. Not sure.

But the phrase "target feature" might refer to a specific face on the final solid. Could be that we need to identify which face (e.g., the face that was cut) has the greatest centroid Y? But then we'd need to output a variable name like "wp13"? Not.

Let's read the original problem statement again: "Identify the target feature that satisfies all of these constraints: - The target feature has centroid Y coordinate. - Among the remaining candidates, choose the one with the greatest centroid Y coordinate." This seems like a typical multiple-choice question where you have to pick from a list of features. Perhaps the features are the different objects created in the script, and we need to pick the one with the largest Y centroid. The "remaining candidates" might be all the features that have a centroid Y coordinate (i.e., not degenerate). So we need to compute or reason which one has the greatest centroid Y. Without actual numeric computation, we can reason that the torus has centroid at origin (Y=0). The swept solid has positive Y centroid. The cut result has negative Y centroid. So the swept solid (wp12) has the greatest. But why would the answer be wp7? Unless wp7 is the wire? But wire has no volume centroid.

Maybe "centroid Y coordinate" refers to the Y coordinate of the centroid of the shape's bounding box? Or perhaps the problem expects us to consider the workplane objects themselves, not the solids. For instance, wp1 is a workplane on XZ, its centroid? That doesn't make sense.

Another possibility: The script defines multiple "features" via intermediate variables. The final result is a solid. But the question might be from a test where they ask: "Which of these variables refers to a feature that has the greatest centroid Y?" And among the variables that represent features (i.e., solids or faces), we pick one. The variables that hold solids: wp4, wp12, wp13. Possibly also wp3 is just a circle (wire) before revolve, but not solid. So candidate solids: wp4, wp12, wp13 (result). Their centroids: wp4 has Y=0, wp12 has Y>0, wp13 has Y<0. So wp12 is greatest. So answer wp12. But the example says "for example wp7". That is just an example of the format, not a hint.

Given the instruction: "Return exactly one source variable name", and the answer contract expects a string like "wp7", I think the answer should be one of the variable names from the script. I'll go with wp12 as the most plausible. However, let's double-check: The wire wp8 is a spline. Could it be that the "feature" is the wire itself? The centroid of a wire (average of points) would have a Y coordinate around maybe 30? But then among wires, there is only one wire? Actually there is also the circle from wp3, but that's a circle, its centroid (center) is at (71,0,0) in XZ plane, but that's in 3D? Actually circle is in XZ plane so Y=0. So its centroid Y=0. The spline wire has points with Y up to 56, so its centroid Y is positive. So if we consider wires, wp8 (the spline) has the greatest Y centroid among wires? But wp3 is a circle wire? wp3 is a Workplane after circle, but that might contain a wire. However, wp8 is explicitly a wire. And wp7 is a list of wires? Actually wp7 = wp6.wires() returns a list, so wp7 is a list, not a wire. The example says "for example wp7", but wp7 is a list. So maybe they want the variable that represents the wire that is later used? That would be wp8. But the example gave wp7, which is a collection. Not sure.

Maybe the "target feature" is the final solid after cut, and we need to find among its faces the one with greatest centroid Y. But then we'd need to parse the script to deduce which face that is. Without executing the code, it's hard.

Given the limited information, I think the most straightforward interpretation is: Among the solids created, the one with the greatest centroid Y is the swept solid (wp12). So answer: wp12.

But let's see if the problem asks for "source variable name". The variables are all defined. So I'll answer wp12.

The script creates three solid objects: wp4 (torus), wp12 (swept solid), and wp13 (cut result). The torus is symmetric about the Y-axis, so its centroid Y is 0. The swept solid lies entirely in the region y ≥ 0, giving it a positive centroid Y. The cut removes material from the upper part of the torus, shifting the result’s centroid Y negative. Thus, wp12 has the greatest centroid Y among these solids.

{"name": "submit_text", "arguments": {"text": "wp12"}}
```
