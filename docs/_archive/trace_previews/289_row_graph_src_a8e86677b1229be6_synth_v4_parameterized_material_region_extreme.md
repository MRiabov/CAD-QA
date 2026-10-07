# row:graph:src_a8e86677b1229be6:synth:v4:parameterized_material_region_extreme

- **source**: original-pool
- **hop**: 3  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp6`
- **trace_tokens**: ?
- **compacted**: False

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -1))
wp2 = wp1.box(200, 194, 4)
wp3 = wp2.faces('>Z')
wp4 = wp3.workplane()
wp5 = wp4.rect(85, 54)
wp6 = wp5.extrude(1)
wp7 = wp6.faces('>Z')
wp8 = wp7.workplane()
wp9 = wp8.rect(55, 25)
wp10 = wp9.cutBlind(-1)
wp11 = wp10.faces('>Z')
wp12 = wp11.workplane(offset=-1)
wp13 = wp12.rect(55, 25)
wp14 = wp13.extrude(1)
wp15 = wp14.faces('>Z')
wp16 = wp15.workplane()
wp17 = wp16.pushPoints([[91, 88], [91, -88], [-91, 88], [-91, -88]])
wp18 = wp17.cskHole(6, 19, 105)
result = wp18
```

Identify the target added-material region that satisfies all of these constraints:
- The target is a region of material added by an extrusion or sweep.
- The target added-material region can be described by its centroid height.
- Within the narrowed set, select the candidate with the maximum centroid height.
- For any remaining tie, keep the candidate with the maximum volume.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
We need to identify extruded (added material) regions and compare their centroid heights, breaking ties by volume.

1. **wp2**: box(200,194,4) added material. Centroid z = (-1 + 3) = 2? Wait: origin z = -1, height = 4, so bottom at z=-1, top at z=3 → centroid z = 1.
2. **wp6**: extrusions from wp5 (rect 85×54 extruded +1). Extrude starts on face ‘>Z’ of wp2 (z=3), goes to z=4: centroid z = 3.5, volume = 85*54*1.
3. **wp10**: cutBlind(-1) — this removes material, not add.
4. **wp14**: extrude(1) from wp12 (rect 55×25). Workplane offset=-1 from wp8’s face, we need to track z: wp8 is on face ‘>Z’ of wp6 at z=4. Then wp11.workplane(offset=-1) shifts down by 1 → starting plane at z=3. Then rect extrude +1 → top at z=4, so centroid z = 3.5 again. Same height as wp6.

Now compare volume:  
wp6 volume = 85*54 = 4590  
wp14 volume = 55*25 = 1375  

So wp6 larger volume → break tie.  

Target is wp6.

**Answer:**  
```json
{"name": "submit_text", "arguments": {"text": "wp6"}}
```
```
