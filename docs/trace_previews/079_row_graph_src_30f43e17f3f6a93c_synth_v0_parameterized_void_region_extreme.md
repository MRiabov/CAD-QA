# row:graph:src_30f43e17f3f6a93c:synth:v0:parameterized_void_region_extreme

- **source**: original-pool
- **hop**: 3  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp7`
- **trace_tokens**: ?
- **compacted**: True

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
Identify cuts: wp3.cut(wp6) -> wp7, wp7.cut(wp10) -> wp11, wp14.cut(wp10) -> wp15. Removed-material regions: wp6 (cylinder r=88, Y 61-183, span=122), intersection of wp7 and wp10 (Y 61-183, span=122), intersection of wp14 and wp10 (Y 61-183, span=122). All Y spans equal 122. Tie-break: change in vertex count for first cut is 0 (cylinder to shell, no new vertices); other cuts create new vertices. Minimum change is first cut. Result variable is wp7.

{"name": "submit_text", "arguments": {"text": "wp7"}}

The target removed-material region is from the first cut (wp3.cut(wp6)), which removes the inner cylinder. All removed regions have the same Y span (122), but this cut results in zero change in vertex count, which is minimal. The result of this cut is wp7.

```json
{"name": "submit_text", "arguments": {"text": "wp7"}}
```
