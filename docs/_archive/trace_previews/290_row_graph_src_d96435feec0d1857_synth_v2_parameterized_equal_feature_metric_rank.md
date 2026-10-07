# row:graph:src_d96435feec0d1857:synth:v2:parameterized_equal_feature_metric_rank

- **source**: original-pool
- **hop**: 3  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp4`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, -45, 0))
wp2 = wp1.box(141, 106, 200)
wp3 = cq.Workplane('XY', origin=(0, -45, 0))
wp4 = wp3.box(133, 99, 193)
wp5 = wp2.cut(wp4)
wp6 = wp5.faces('>X')
wp7 = wp6.workplane()
wp8 = wp7.pushPoints([[-27, 0], [27, 0]])
wp9 = wp8.rect(56, 34)
wp10 = wp9.cutThruAll()
wp11 = wp10.faces('<X')
wp12 = wp11.workplane()
wp13 = wp12.pushPoints([[-27, 0], [27, 0]])
wp14 = wp13.rect(56, 34)
wp15 = wp14.cutThruAll()
wp16 = wp15.faces('>Y')
wp17 = wp16.workplane()
wp18 = wp17.pushPoints([[-33, 0], [33, 0]])
wp19 = wp18.rect(56, 34)
wp20 = wp19.cutThruAll()
wp21 = wp20.faces('<Y')
wp22 = wp21.workplane()
wp23 = wp22.pushPoints([[-33, 0], [33, 0]])
wp24 = wp23.rect(56, 34)
wp25 = wp24.cutThruAll()
wp26 = cq.Workplane('front', origin=(0, -45, 0))
wp27 = wp26.rect(133, 193)
wp28 = wp27.extrude(4)
wp29 = wp28.faces('>Y')
wp30 = wp29.workplane()
wp31 = wp30.pushPoints([[-67, 0], [-44, 3], [-22, 3], [0, 0], [22, -3], [44, -3], [67, 0]])
wp32 = wp31.circle(1)
wp33 = wp32.cutThruAll()
wp34 = wp33.translate([0, 46, 0])
wp35 = wp25.union(wp34)
wp36 = wp35.edges('>X and |Z')
wp37 = wp36.fillet(2)
wp38 = wp37.edges('<X and |Z')
wp39 = wp38.fillet(2)
result = wp39
```

Identify the target feature that satisfies all of these constraints:
- The target feature's centroid Y coordinate is -45.0.
- The target feature has a value for volume.
- From the remaining candidates, choose the 2nd item after sorting by descending volume.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
1) Solids with centroid Y=-45.0 are those symmetric about the origin (0,-45,0): wp2 (box 141x106x200), wp4 (box 133x99x193), wp5 (wp2.cut(wp4)), and subsequent symmetrically cut solids wp10, wp15, wp20, wp25. The plate wp28 etc. have centroid Y≠-45. 2) Volumes: wp2=2,989,200; wp4=2,541,231; wp5=447,969; wp10=417,505; wp15=387,041; wp20=360,385; wp25=333,729 (computed from dimensions and cut removals: each cutThruAll on X faces removes 2*56*34*4=15,232; each on Y faces removes 2*56*34*3.5=13,328). 3) Sorted descending by volume: wp2, wp4, wp5, wp10, wp15, wp20, wp25. The 2nd item is wp4.

{"name": "submit_text", "arguments": {"text": "wp4"}}

The feature with centroid Y = -45.0 and volume > 0 are the symmetric solids: wp2, wp4, wp5, wp10, wp15, wp20, wp25. Sorting by descending volume: wp2, wp4, wp5, ... The 2nd item is wp4.

```json
{"name": "submit_text", "arguments": {"text": "wp4"}}
```
