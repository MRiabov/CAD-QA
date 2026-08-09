# row:graph:graph:src_3dac547343362b42:q1:argmax_origin_z_workplane

- **source**: center-fix
- **hop**: 1  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp16`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XZ')
wp2 = wp1.moveTo(100, 0)
wp3 = wp2.circle(25)
wp4 = wp3.revolve(360, [0, 0, 0], [0, 2, 0])
wp5 = cq.Workplane('XZ')
wp6 = wp5.moveTo(100, 0)
wp7 = wp6.circle(16)
wp8 = wp7.revolve(360, [0, 0, 0], [0, 2, 0])
wp9 = wp4.cut(wp8)
wp10 = cq.Workplane('XZ')
wp11 = wp10.center(80, 0)
wp12 = wp11.circle(8)
wp13 = wp12.extrude(49, both=True)
wp14 = wp9.cut(wp13)
wp15 = cq.Workplane('XZ')
wp16 = wp15.center(0, 80)
wp17 = wp16.circle(8)
wp18 = wp17.extrude(49, both=True)
wp19 = wp14.cut(wp18)
wp20 = cq.Workplane('XZ')
wp21 = wp20.center(-80, 0)
wp22 = wp21.circle(8)
wp23 = wp22.extrude(49, both=True)
wp24 = wp19.cut(wp23)
wp25 = cq.Workplane('XZ')
wp26 = wp25.center(0, -80)
wp27 = wp26.circle(8)
wp28 = wp27.extrude(49, both=True)
wp29 = wp24.cut(wp28)
wp30 = cq.Workplane('XY')
wp31 = wp30.workplane(offset=-25)
wp32 = wp31.polyline([[16, -1], [16, 1], [100, 5], [100, -5]])
wp33 = wp32.close()
wp34 = wp33.extrude(49)
wp35 = wp34.rotate([0, 0, 0], [0, 0, 2], 0)
wp36 = wp35.edges('|Z')
wp37 = wp36.fillet(1)
wp38 = wp29.union(wp37)
wp39 = cq.Workplane('XY')
wp40 = wp39.workplane(offset=-25)
wp41 = wp40.polyline([[16, -1], [16, 1], [100, 5], [100, -5]])
wp42 = wp41.close()
wp43 = wp42.extrude(49)
wp44 = wp43.rotate([0, 0, 0], [0, 0, 2], 90)
wp45 = wp44.edges('|Z')
wp46 = wp45.fillet(1)
wp47 = wp38.union(wp46)
wp48 = cq.Workplane('XY')
wp49 = wp48.workplane(offset=-25)
wp50 = wp49.polyline([[16, -1], [16, 1], [100, 5], [100, -5]])
wp51 = wp50.close()
wp52 = wp51.extrude(49)
wp53 = wp52.rotate([0, 0, 0], [0, 0, 2], 180)
wp54 = wp53.edges('|Z')
wp55 = wp54.fillet(1)
wp56 = wp47.union(wp55)
wp57 = cq.Workplane('XY')
wp58 = wp57.workplane(offset=-25)
wp59 = wp58.polyline([[16, -1], [16, 1], [100, 5], [100, -5]])
wp60 = wp59.close()
wp61 = wp60.extrude(49)
wp62 = wp61.rotate([0, 0, 0], [0, 0, 2], 270)
wp63 = wp62.edges('|Z')
wp64 = wp63.fillet(1)
wp65 = wp56.union(wp64)
result = wp65
```

Identify the target workplane that satisfies all of these constraints:
- Among the remaining candidates, choose the one with the greatest workplane origin height.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
Identify workplane origins. `wp16 = wp15.center(0,80)` sets origin to (0,0,80) in global coordinates (XZ plane: x=0, z=80). All other workplane origins have z ≤ 0, so wp16 has the greatest origin height.

{"name": "submit_text", "arguments": {"text": "wp16"}}
```
