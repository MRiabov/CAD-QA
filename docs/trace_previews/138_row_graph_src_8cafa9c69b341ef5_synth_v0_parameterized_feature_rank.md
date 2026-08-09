# row:graph:src_8cafa9c69b341ef5:synth:v0:parameterized_feature_rank

- **source**: original-pool
- **hop**: 2  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp2`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY')
wp2 = wp1.box(200, 33, 42)
wp3 = wp2.faces('>Z')
wp4 = wp3.workplane()
wp5 = wp4.pushPoints([[-38, 0], [-23, 0], [-8, 0], [8, 0], [23, 0], [38, 0]])
wp6 = wp5.rect(15, 15)
wp7 = wp6.cutThruAll()
result = wp7
```

Identify the target feature that satisfies all of these constraints:
- The target feature has a value for face count.
- From the remaining candidates, choose the 2nd item after sorting by descending face count.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
Let's trace the construction step by step:

1. `wp1` — XY workplane.
2. `wp2` — adds a box of dimensions 200×33×42. This solid has 6 faces.
3. `wp3` — selects the top face (`>Z`).
4. `wp4` — creates a new workplane on that top face.
5. `wp5` — pushes the center of that workplane to six points along X: -38, -23, -8, 8, 23, 38 (Y=0).
6. `wp6` — draws a 15×15 rectangle at each point (six separate sketches).
7. `wp7` — cuts those six rectangles through the entire solid.

Now, each rectangle cut creates a through hole. The initial solid has 6 faces; cutting through adds 6 holes, each  
adding 4 vertical faces inside the hole, but also removes the top and bottom face area covered by the hole.  
Resulting face count:  

Original box: 6 faces.  
Each through hole adds 4 internal cylindrical-side-like faces (here rectangular profile: 4 sides).  
So 6 holes × 4 = 24 new faces, but also removes 2 faces × 6 holes = 12 faces from top and bottom? Actually each cut removes area but doesn't reduce face count if it's a hole through — the original top and bottom become faces with holes, still counted as faces. Net increase: each hole adds 4 interior faces, so total faces = 6 + 24 = 30.

Among all variables, each is a workplane, not a solid, except `wp2` (a box solid → 6 faces).  
But "face count" refers to the solid produced.  

Candidates from the script:  
- `wp2`: 6 faces  
- `wp7`: 30 faces  

Sort by descending face count: wp7 (30), wp2 (6).  
2nd item after sorting = wp2 (6 faces).

Therefore the target feature (2nd after sorting descending face count) is `wp2`.  

```json
{"name": "submit_text", "arguments": {"text": "wp2"}}
```
```
