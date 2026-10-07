# row:graph:graph:src_c39a861dbf652d38:q1:argmin_origin_z_workplane

- **source**: original-pool
- **hop**: 1  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp1`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -2))
wp2 = wp1.box(200, 125, 18)
wp3 = wp2.faces('>Z')
wp4 = wp3.workplane()
wp5 = wp4.rect(200, 125)
wp6 = wp5.extrude(5)
wp7 = wp6.faces('>Z')
wp8 = wp7.workplane()
wp9 = wp8.rect(165, 90)
wp10 = wp9.cutBlind(-5)
wp11 = wp10.faces('>Z')
wp12 = wp11.workplane()
wp13 = wp12.rect(165, 90, forConstruction=1)
wp14 = wp13.vertices()
wp15 = wp14.cboreHole(8, 10, 2)
wp16 = wp15.faces('>Z')
wp17 = wp16.workplane(offset=-5)
wp18 = wp17.rect(162, 60)
wp19 = wp18.extrude(5)
wp20 = wp19.faces('>Z')
wp21 = wp20.workplane(centerOption='CenterOfBoundBox', offset=-5)
wp22 = wp21.pushPoints([[-72, -33], [-48, -33], [-22, -33], [2, -33], [28, -33], [52, -33], [-60, 33], [-35, 33], [-10, 33], [15, 33], [40, 33], [65, 33]])
wp23 = wp22.polygon(6, 20)
wp24 = wp23.cutThruAll()
wp25 = wp24.edges('((>X or <X or >Y or <Y) and |Z)')
wp26 = wp25.fillet(1)
result = wp26
```

Identify the target workplane that satisfies all of these constraints:
- Among the remaining candidates, choose the one with the smallest workplane origin height.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
wp1 origin=(0,0,-2) height=-2; all others have heights 7 or 12. Thus smallest is -2; among candidates (all workplanes), wp1 is the one with explicitly set negative origin.

{"name": "submit_text", "arguments": {"text": "wp1"}}
```
