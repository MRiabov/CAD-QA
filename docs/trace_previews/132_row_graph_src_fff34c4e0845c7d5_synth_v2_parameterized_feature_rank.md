# row:graph:src_fff34c4e0845c7d5:synth:v2:parameterized_feature_rank

- **source**: original-pool
- **hop**: 2  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp6`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -86))
wp2 = wp1.splineApprox([[46, 0, 0], [24, 39, 6], [-19, 41, 13], [-45, 6, 19], [-29, -35, 26], [14, -43, 32], [44, -11, 39], [33, 31, 46], [-9, 45, 52], [-43, 17, 59], [-37, -27, 66], [3, -46, 73], [40, -22, 79], [40, 22, 86], [3, 46, 93], [-37, 27, 100], [-43, -17, 107], [-9, -45, 114], [33, -31, 121], [44, 11, 128], [14, 43, 135], [-29, 35, 142], [-45, -6, 150], [-19, -41, 157], [24, -39, 164], [46, 0, 171]], makeWire=True)
wp3 = cq.Workplane('XZ', origin=(0, 0, -86))
wp4 = wp3.moveTo(46, 0)
wp5 = wp4.circle(9)
wp6 = wp5.sweep(wp2, multisection=True)
wp7 = cq.Workplane('XZ', origin=(0, 0, -86))
wp8 = wp7.moveTo(46, 0)
wp9 = wp8.circle(14)
wp10 = wp9.revolve(360, (0, 0), (0, 3))
wp11 = cq.Workplane('XZ', origin=(0, 0, -86))
wp12 = wp11.moveTo(46, 171)
wp13 = wp12.circle(14)
wp14 = wp13.revolve(360, (0, 0), (0, 3))
wp15 = wp6.union(wp10)
wp16 = wp15.union(wp14)
result = wp16
```

Identify the target feature that satisfies all of these constraints:
- The target feature has face count.
- Among the remaining candidates, choose the 3rd candidate when ordered from smallest to greatest face count.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
The solids with face counts are wp6 (sweep), wp10 and wp14 (revolves), wp15 and wp16 (unions). wp10 and wp14 are tori with 1 face each. wp6 is a tube with 3 faces. Unions have more faces. Sorted smallest to greatest: 1,1,3,... so the 3rd candidate is wp6.

{"name": "submit_text", "arguments": {"text": "wp6"}}
```
