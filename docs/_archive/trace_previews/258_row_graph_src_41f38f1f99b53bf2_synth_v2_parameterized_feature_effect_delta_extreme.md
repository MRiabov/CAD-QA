# row:graph:src_41f38f1f99b53bf2:synth:v2:parameterized_feature_effect_delta_extreme

- **source**: original-pool
- **hop**: 3  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp27`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY')
wp2 = wp1.box(200, 148, 151)
wp3 = cq.Workplane('XY')
wp4 = wp3.box(181, 129, 132)
wp5 = wp2.cut(wp4)
wp6 = wp5.faces('>X')
wp7 = wp6.workplane()
wp8 = wp7.pushPoints([[-41, -31], [-41, 31], [0, -31], [0, 31], [41, -31], [41, 31]])
wp9 = wp8.rect(18, 34)
wp10 = wp9.cutBlind(-10)
wp11 = wp10.faces('<X')
wp12 = wp11.workplane()
wp13 = wp12.pushPoints([[-41, -31], [-41, 31], [0, -31], [0, 31], [41, -31], [41, 31]])
wp14 = wp13.rect(18, 34)
wp15 = wp14.cutBlind(-10)
wp16 = wp15.faces('>Y')
wp17 = wp16.workplane()
wp18 = wp17.pushPoints([[-54, -31], [-54, 31], [0, -31], [0, 31], [54, -31], [54, 31]])
wp19 = wp18.rect(18, 34)
wp20 = wp19.cutBlind(-10)
wp21 = wp20.faces('<Y')
wp22 = wp21.workplane()
wp23 = wp22.pushPoints([[-54, -31], [-54, 31], [0, -31], [0, 31], [54, -31], [54, 31]])
wp24 = wp23.rect(18, 34)
wp25 = wp24.cutBlind(-10)
wp26 = wp25.edges('|Z and (>X or <X or >Y or <Y)')
wp27 = wp26.chamfer(2)
result = wp27
```

Identify the target feature that satisfies all of these constraints:
- The target feature's increase in edge count is greater than 0.0.
- The target feature has a value for face count.
- From the remaining candidates, choose the one with the largest face count.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
Identify all solid-modifying operations: wp2, wp4, wp5, wp10, wp15, wp20, wp25, wp27. Each has edge count increase >0. All have face count. Among these, wp27 has the largest face count because it accumulates all previous faces plus chamfer faces.

{"name":"submit_text","arguments":{"text":"wp27"}}
```
