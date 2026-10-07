# row:graph:src_bf8ed1ccf42d99c3:synth:v4:parameterized_feature_rank

- **source**: original-pool
- **hop**: 3  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp8`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY')
wp2 = wp1.box(200, 76, 11)
wp3 = wp2.faces('>Z')
wp4 = wp3.workplane()
wp5 = wp4.pushPoints([[-67, -13], [-33, -13], [0, -13], [33, -13], [67, -13], [-67, 13], [-33, 13], [0, 13], [33, 13], [67, 13]])
wp6 = wp5.circle(5)
wp7 = wp6.cutThruAll()
wp8 = wp7.edges('|Z')
wp9 = wp8.fillet(1)
result = wp9
```

Identify the target feature that satisfies all of these constraints:
- The target feature satisfies overall height greater than 0.0.
- The target feature can be described by its edge count.
- Within the narrowed set, select the 2nd candidate in increasing edge count order.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
The box is 200×76×11, so the top face is at z=11.  
The circles are cut through the entire box, creating 10 through holes.  
Then `wp8 = wp7.edges('|Z')` selects only vertical edges (parallel to Z axis).  
These vertical edges come from the hole boundaries (each hole has a circular edge) and the outer box edges (four vertical edges at the corners).  

- Outer box vertical edges: 4  
- Each hole has one full circular edge, but a circle is a single closed edge, so 10 holes → 10 circular vertical edges.  

Total vertical edges: 4 + 10 = 14.  
Then `wp8.fillet(1)` fillets all those edges.  

The requirement:  
- Height > 0 (true for all).  
- Describe by edge count.  
- Among edges sets, pick 2nd in increasing edge count order.  

There is only one fillet operation here, on a set of 14 edges.  
The 2nd candidate in increasing edge count order from the list of possible edge sets?  
Actually the only candidate with edges is the set of 14 vertical edges before fillet (wp8). After fillet, the edges remain the same set (just filleted).  

The question is about "target feature" before fillet — the edge set `wp8` has edge count 14, height > 0.  
The only other possible feature is the whole solid (countless edges). So sorted: solid (infinite), then wp8 edges (14). 2nd candidate is wp8.

But note: the variable `wp8` refers to the `Workplane` object containing those edges, which is the target.

Answer: `wp8`

```json
{"name": "submit_text", "arguments": {"text": "wp8"}}
```
```
