# row:graph:src_97f0da8117bea982:synth:v4:parameterized_feature_rank

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
wp1 = cq.Workplane('XY', origin=(0, 0, -94))
wp2 = wp1.splineApprox([[51, 0, 0], [28, 43, 9], [-22, 47, 17], [-51, 6, 26], [-33, -40, 34], [16, -49, 42], [50, -13, 50], [38, 35, 59], [-10, 51, 67], [-48, 19, 74], [-42, -30, 82], [3, -51, 90], [45, -25, 98], [45, 25, 105], [3, 51, 113], [-42, 30, 120], [-48, -19, 127], [-10, -51, 134], [38, -35, 142], [50, 13, 149], [16, 49, 155], [-33, 40, 162], [-51, -6, 169], [-22, -47, 176], [28, -43, 182], [51, 0, 189]], makeWire=True)
wp3 = cq.Workplane('XZ', origin=(0, 0, -94))
wp4 = wp3.moveTo(51, 0)
wp5 = wp4.circle(6)
wp6 = wp5.sweep(wp2, multisection=True)
wp7 = cq.Workplane('XZ', origin=(0, 0, -94))
wp8 = wp7.moveTo(51, 0)
wp9 = wp8.circle(1)
wp10 = wp9.revolve(360, (0, 0), (0, 3))
wp11 = cq.Workplane('XZ', origin=(0, 0, -94))
wp12 = wp11.moveTo(-51, 0)
wp13 = wp12.circle(1)
wp14 = wp13.revolve(360, (0, 0), (0, 3))
wp15 = wp6.union(wp10)
wp16 = wp15.union(wp14)
result = wp16
```

Identify the target feature that satisfies all of these constraints:
- The target feature has a value for face count.
- From the remaining candidates, choose the 3rd item after sorting by ascending face count.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
Candidates with positive face count: wp10 (torus, 1), wp14 (torus, 1), wp6 (swept tube, 3), wp15 (union of tube and first torus, 3), wp16 (union with second torus, 4). Sorted ascending: wp10, wp14, wp6, wp15, wp16. 3rd item is wp6.

{"name": "submit_text", "arguments": {"text": "wp6"}}
```
