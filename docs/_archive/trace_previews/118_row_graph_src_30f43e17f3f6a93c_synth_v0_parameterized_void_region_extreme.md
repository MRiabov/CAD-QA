# row:graph:src_30f43e17f3f6a93c:synth:v0:parameterized_void_region_extreme

- **source**: original-pool
- **hop**: 3  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp7`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XZ', origin=(26, 61, 0))
wp2 = wp1.circle(100)
wp3 = wp2.extrude(122)
wp4 = cq.Workplane('XZ', origin=(26, 61, 0))
wp5 = wp4.circle(88)
wp6 = wp5.extrude(122)
wp7 = wp3.cut(wp6)
wp8 = cq.Workplane('XY', origin=(26, 61, 0))
wp9 = wp8.box(175, 244, 175)
wp10 = wp9.translate([88, 0, 0])
wp11 = wp7.cut(wp10)
wp12 = cq.Workplane('XZ', origin=(26, 61, 0))
wp13 = wp12.circle(88)
wp14 = wp13.extrude(122)
wp15 = wp14.cut(wp10)
wp16 = cq.Workplane('XZ', origin=(26, 61, 0))
wp17 = wp16.pushPoints([[0, -84], [0, -31], [0, 22], [0, 75]])
wp18 = wp17.rect(181, 6)
wp19 = wp18.extrude(122)
wp20 = wp19.intersect(wp15)
wp21 = cq.Workplane('XZ', origin=(26, 61, 0))
wp22 = wp21.pushPoints([[-84, 0], [-31, 0]])
wp23 = wp22.rect(6, 181)
wp24 = wp23.extrude(122)
wp25 = wp24.intersect(wp15)
wp26 = wp20.union(wp25)
wp27 = cq.Workplane('XZ', origin=(26, 61, 0))
wp28 = wp27.polyline([[4, -3], [-54, -69], [-61, -63], [-4, 3]])
wp29 = wp28.close()
wp30 = wp29.extrude(122)
wp31 = wp30.intersect(wp15)
wp32 = wp26.union(wp31)
wp33 = cq.Workplane('XZ', origin=(26, 61, 0))
wp34 = wp33.polyline([[-4, -3], [-61, 63], [-54, 69], [4, 3]])
wp35 = wp34.close()
wp36 = wp35.extrude(122)
wp37 = wp36.intersect(wp15)
wp38 = wp32.union(wp37)
wp39 = wp11.union(wp38, clean=1)
result = wp39
```

Identify the target removed-material region that satisfies all of these constraints:
- The target is a region of material removed by a cut.
- The target removed-material region can be described by its Y span of the changed envelope.
- Within the narrowed set, select the candidate with the maximum Y span of the changed envelope.
- For any remaining tie, keep the candidate with the minimum change in vertex count.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
The construction creates a thick cylindrical shell (wp7) by cutting a smaller cylinder from a larger one. Then a box (wp10) cuts through this shell, creating a rectangular notch.  

Inside that notch, various 2D profiles on XZ are extruded and intersected with the remaining thin wall (wp15), then unioned (wp38). Finally, wp39 = wp11.union(wp38) adds those internal shapes back into the main body.  

The “target removed-material region” refers to material cut away by one of the earlier cut operations. The cuts are:  
- wp7 = wp3 cut by wp6 (removes inner cylinder)  
- wp11 = wp7 cut by wp10 (removes box region)  

We need the cut that changes the **Y span** of the envelope. The initial envelope Y span is from the cylinder’s extrusion along Y (Y goes from -61 to 61? Actually the extrusion is along the normal of XZ, which is Y; length 122 from origin y=61 gives y range 0 to 122? Wait origin y=61, extrude 122 along Y → y from 61 to 183).  
After cutting with wp10 (box 175x244x175 translated by [88,0,0]), the box is aligned in XY, so its Y span is 244 (from y=-122 to 122 relative to origin? Let’s compute: origin (26,61,0), box dimensions 175,244,175 → center at origin + [88,0,0] → box extends y from 61-122=-61 to 61+122=183. That matches the cylinder’s Y range, so the cut does not change Y span.  
The earlier cut wp7 (inner cylinder) also has same Y span. Thus no cut changed Y span? But the question expects a candidate.  

Looking closer: the envelope change refers to **changed** envelope — meaning the cut modifies the bounding box. The box cut (wp10) removes a chunk, possibly reducing Y span? No, still full Y.  
However, later operations like wp20, wp25, wp31, wp37 are intersected with wp15, then unioned back. Those are additive, not cuts.  

The only two cuts are wp7 (inner cylinder removal) and wp11 (box removal). Both have the same Y span (0 to 122? Let’s recalc: origin y=61, extrude 122 → y from 61 to 183, span=122). So tie. Next tiebreaker: minimum change in vertex count.  

wp7 removes a cylinder — the vertex count change is small (inner cylinder adds vertices? Actually cut removes volume, but vertex count change in the resulting solid). wp10 cut (box) likely removes more complex shape, causing larger vertex change. So wp7 has smaller vertex count change.  

Thus answer: wp7.

```json
{"name": "submit_text", "arguments": {"text": "wp7"}}
```
```
