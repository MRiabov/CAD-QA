# row:graph:src_1e593fa3037ad99b:synth:v2:parameterized_path_point_rank

- **source**: original-pool
- **hop**: 3  |  **format**: coordinate  |  **tool**: submit_coordinate
- **gold**: `[5, 6, 0]`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(-5, -4, -100))
wp2 = wp1.lineTo(9, 0)
wp3 = wp2.spline([[7, 2], [5, 6], [5, 8]])
wp4 = wp3.close()
wp5 = wp4.extrude(200)
result = wp5
```

Identify the target path point that satisfies all of these constraints:
- The target point belongs to a path in the sketch.
- The target point has a value for Y coordinate.
- From the remaining candidates, choose the 2nd item after sorting by descending Y coordinate.

Return exactly one coordinate tuple of the path point, for example `(0, 1, 3)`.
```

## Model output (trace)

```
The sketch starts on the XY plane (z=-100 ignored as workplane offset does not affect sketch coordinates).  
Points added in order:  
- Start at (-5, -4) (implicit from origin).  
- lineTo(9,0) adds (9,0).  
- spline([[7,2],[5,6],[5,8]]) adds those three points in sequence.  
- close() adds line back to start (-5,-4).  

So the path vertices in order:  
1. (-5, -4)  
2. (9, 0)  
3. (7, 2)  
4. (5, 6)  
5. (5, 8)  
6. (-5, -4) (closing point, same as first, generally not considered separate)  

Collect distinct vertices excluding duplicate start/end: (-5,-4), (9,0), (7,2), (5,6), (5,8).  
Y coordinates: -4, 0, 2, 6, 8.  
Sorted descending by Y: (5,8), (5,6), (7,2), (9,0), (-5,-4).  
2nd item after sorting: (5,6).  
Sketch is 2D on XY plane, z=0.  
So coordinate is (5, 6, 0).

```json
{"name": "submit_coordinate", "arguments": {"value": [5, 6, 0]}}
```
```
