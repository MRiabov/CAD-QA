# row:graph:src_305fa36259177b48:synth:v1:parameterized_edge_reference_entity_distance

- **source**: original-pool
- **hop**: 5  |  **format**: candidate_label  |  **tool**: submit_label
- **gold**: `"C"`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(-14, 0, 0))
wp2 = wp1.box(173, 30, 77)
wp3 = cq.Workplane('XY', origin=(-14, 0, 0))
wp4 = wp3.box(130, 13, 68)
wp5 = wp4.translate([-13, 0, 4])
wp6 = wp2.cut(wp5)
wp7 = wp6.faces('>X')
wp8 = wp7.workplane()
wp9 = wp8.pushPoints([[16, 0], [-16, 0]])
wp10 = wp9.rect(2, 11)
wp11 = wp10.extrude(26, combine=0)
wp12 = wp8.rect(34, 2)
wp13 = wp12.center(0, 4)
wp14 = wp13.extrude(26, combine=0)
wp15 = wp11.union(wp14)
wp16 = wp6.union(wp15)
wp17 = wp15.faces('>X')
wp18 = wp17.workplane()
wp19 = wp18.rect(34, 34)
wp20 = wp19.extrude(2, combine=0)
wp21 = wp16.union(wp20)
result = wp21
```

Identify the target edge that satisfies all of these constraints:
- Consider edges from the constructed model.
- The target edge has edge length equal to 13.0.
- Use as the reference the endpoint at coordinates (72.5, -17.0, 5.5).
- The target edge exists and has a midpoint.
- Among the remaining candidates, choose the one whose midpoint is closest to the point location of the reference endpoint.

Candidate labels:
- A: endpoints (-92, -6.5, 38) to (-92, 6.5, 38); midpoint (-92, 0, 38); length 13; midpoint distance to origin 99.538937
- B: endpoints (-92, -6.5, -30) to (-92, 6.5, -30); midpoint (-92, 0, -30); length 13; midpoint distance to origin 96.767763
- C: endpoints (51, -6.5, 34) to (51, 6.5, 34); midpoint (51, 0, 34); length 13; midpoint distance to origin 61.294372
- D: endpoints (38, -6.5, -30) to (38, 6.5, -30); midpoint (38, 0, -30); length 13; midpoint distance to origin 48.414874
- E: endpoints (-79, -6.5, 34) to (-79, 6.5, 34); midpoint (-79, 0, 34); length 13; midpoint distance to origin 86.005814
- F: endpoints (-79, -6.5, -34) to (-79, 6.5, -34); midpoint (-79, 0, -34); length 13; midpoint distance to origin 86.005814
- G: endpoints (51, -6.5, -34) to (51, 6.5, -34); midpoint (51, 0, -34); length 13; midpoint distance to origin 61.294372

Return exactly one candidate label from the list above, for example `A`.
```

## Model output (trace)

```
We need the edge whose midpoint is closest to (72.5, -17.0, 5.5).  
Let’s compute squared distances for each candidate:

- A: (-92, 0, 38) → dx = -92 - 72.5 = -164.5, dy = 17, dz = 32.5  
  sq = 164.5² + 17² + 32.5² = 27060.25 + 289 + 1056.25 = 28405.5

- B: (-92, 0, -30) → dx = -164.5, dy = 17, dz = -35.5  
  sq = 27060.25 + 289 + 1260.25 = 28609.5

- C: (51, 0, 34) → dx = -21.5, dy = 17, dz = 28.5  
  sq = 462.25 + 289 + 812.25 = 1563.5

- D: (38, 0, -30) → dx = -34.5, dy = 17, dz = -35.5  
  sq = 1190.25 + 289 + 1260.25 = 2739.5

- E: (-79, 0, 34) → dx = -151.5, dy = 17, dz = 28.5  
  sq = 22952.25 + 289 + 812.25 = 24053.5

- F: (-79, 0, -34) → dx = -151.5, dy = 17, dz = -39.5  
  sq = 22952.25 + 289 + 1560.25 = 24801.5

- G: (51, 0, -34) → dx = -21.5, dy = 17, dz = -39.5  
  sq = 462.25 + 289 + 1560.25 = 2311.5

Smallest sq distance is C (1563.5).  

The target edge is the one with midpoint (51, 0, 34) — candidate C.

{"name": "submit_label", "arguments": {"label": "C"}}
```
