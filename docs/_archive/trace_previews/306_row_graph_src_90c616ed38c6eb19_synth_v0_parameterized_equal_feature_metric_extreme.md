# row:graph:src_90c616ed38c6eb19:synth:v0:parameterized_equal_feature_metric_extreme

- **source**: original-pool
- **hop**: 3  |  **format**: text  |  **tool**: submit_text
- **gold**: `wp8`
- **trace_tokens**: ?
- **compacted**: True

## Row prompt

```
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XZ')
wp2 = wp1.moveTo(75, 0)
wp3 = wp2.circle(25)
wp4 = wp3.revolve(360, [0, 0, 0], [0, 2, 0])
wp5 = cq.Workplane('XZ')
wp6 = wp5.polyline([[50, 16], [95, 30], [89, 46], [46, 24]])
wp7 = wp6.close()
wp8 = wp7.extrude(50)
wp9 = wp8.translate([0, -25, 0])
wp10 = wp4.cut(wp9)
wp11 = cq.Workplane('XZ')
wp12 = wp11.polyline([[37, 37], [70, 71], [57, 82], [30, 43]])
wp13 = wp12.close()
wp14 = wp13.extrude(50)
wp15 = wp14.translate([0, -25, 0])
wp16 = wp10.cut(wp15)
wp17 = cq.Workplane('XZ')
wp18 = wp17.polyline([[15, 50], [29, 96], [12, 99], [6, 52]])
wp19 = wp18.close()
wp20 = wp19.extrude(50)
wp21 = wp20.translate([0, -25, 0])
wp22 = wp16.cut(wp21)
wp23 = cq.Workplane('XZ')
wp24 = wp23.polyline([[-10, 52], [-19, 98], [-35, 94], [-19, 49]])
wp25 = wp24.close()
wp26 = wp25.extrude(50)
wp27 = wp26.translate([0, -25, 0])
wp28 = wp22.cut(wp27)
wp29 = cq.Workplane('XZ')
wp30 = wp29.polyline([[-33, 41], [-62, 78], [-75, 66], [-39, 35]])
wp31 = wp30.close()
wp32 = wp31.extrude(50)
wp33 = wp32.translate([0, -25, 0])
wp34 = wp28.cut(wp33)
wp35 = cq.Workplane('XZ')
wp36 = wp35.polyline([[-48, 21], [-91, 40], [-97, 24], [-51, 13]])
wp37 = wp36.close()
wp38 = wp37.extrude(50)
wp39 = wp38.translate([0, -25, 0])
wp40 = wp34.cut(wp39)
wp41 = cq.Workplane('XZ')
wp42 = wp41.polyline([[-52, -4], [-100, -7], [-97, -24], [-51, -13]])
wp43 = wp42.close()
wp44 = wp43.extrude(50)
wp45 = wp44.translate([0, -25, 0])
wp46 = wp40.cut(wp45)
wp47 = cq.Workplane('XZ')
wp48 = wp47.polyline([[-45, -27], [-85, -52], [-75, -66], [-39, -35]])
wp49 = wp48.close()
wp50 = wp49.extrude(50)
wp51 = wp50.translate([0, -25, 0])
wp52 = wp46.cut(wp51)
wp53 = cq.Workplane('XZ')
wp54 = wp53.polyline([[-27, -45], [-51, -86], [-35, -94], [-19, -49]])
wp55 = wp54.close()
wp56 = wp55.extrude(50)
wp57 = wp56.translate([0, -25, 0])
wp58 = wp52.cut(wp57)
wp59 = cq.Workplane('XZ')
wp60 = wp59.polyline([[-3, -52], [-5, -100], [12, -99], [6, -52]])
wp61 = wp60.close()
wp62 = wp61.extrude(50)
wp63 = wp62.translate([0, -25, 0])
wp64 = wp58.cut(wp63)
wp65 = cq.Workplane('XZ')
wp66 = wp65.polyline([[22, -48], [42, -91], [57, -82], [30, -43]])
wp67 = wp66.close()
wp68 = wp67.extrude(50)
wp69 = wp68.translate([0, -25, 0])
wp70 = wp64.cut(wp69)
wp71 = cq.Workplane('XZ')
wp72 = wp71.polyline([[42, -32], [79, -61], [89, -46], [46, -24]])
wp73 = wp72.close()
wp74 = wp73.extrude(50)
wp75 = wp74.translate([0, -25, 0])
wp76 = wp70.cut(wp75)
wp77 = cq.Workplane('XZ')
wp78 = wp77.polyline([[52, -9], [98, -17], [100, 0], [53, 0]])
wp79 = wp78.close()
wp80 = wp79.extrude(50)
wp81 = wp80.translate([0, -25, 0])
wp82 = wp76.cut(wp81)
result = wp82
```

Identify the target feature that satisfies all of these constraints:
- The target feature has centroid height equal to 29.967638.
- The target feature has centroid Y coordinate.
- Among the remaining candidates, choose the one with the greatest centroid Y coordinate.

Return exactly one source variable name, for example `wp7`.
```

## Model output (trace)

```
Base torus centered at y=0. Cuts are prisms extruded along Y from y=0 to y=50 then translated by -25. First polygon A vertices: [50,16], [95,30], [89,46], [46,24]. Shoelace: area = 618, centroid z = 111120/(6×618) = 29.967638. This height matches only the first polygon. Its representations: wp7 (closed wire, y=0), wp8 (extrude +50, y=25), wp9 (translate -25, y=0). Among these, wp8 has greatest centroid Y coordinate (25).

{i+1} - z_i x_{i+1}). Centroid z = 1/(6A) sum((z_i + z_{i+1})(x_i z_{i+1} - z_i x_{i+1})) (or using x_i*z_{i+1} etc). Let's compute.

Let's label v1=(50,16), v2=(95,30), v3=(89,46), v4=(46,24). Back to v1.

Compute cross terms c_i = x_i z_{i+1} - z_i x_{i+1}:
v1->v2: 50*30 - 16*95 = 1500 - 1520 = -20
v2->v3: 95*46 - 30*89 = 4370 - 2670 = 1700
v3->v4: 89*24 - 46*46 = 2136 - 2116 = 20
v4->v1: 46*16 - 24*50 = 736 - 1200 = -464
Sum = -20+1700+20-464 = 1236. Area = 1/2*1236 = 618.

Centroid z = 1/(6A) sum (z_i + z_{i+1}) * c_i.
Compute:
i1: (16+30)*(-20)=46*(-20)=-920
i2: (30+46)*1700=76*1700=129200
i3: (46+24)*20=70*20=1400
i4: (24+16)*(-464)=40*(-464)=-18560
Sum = -920+129200+1400-18560 = 111120. 6A=3708. z_centroid = 111120 / 3708 = 29.967637... Let's divide: 3708*29.9676 = 111120? 3708*30=111240, minus 120 => 29.9676375. Yes! Exactly 29.967638. So A (polygon wp5) has centroid z = 29.967638. Great.

Now need target feature: first constraint says centroid height equal to 29.967638. That matches polygon A, i.e. wp5? But it says source variable example wp7. The source variable for first cut polygon is wp5 (Workplane) or wp6 polyline, wp7 close, wp8 extrude, wp9 translate. Which variable denotes feature? Need determine.

They ask "target feature has centroid height equal to 29.967638." The 2D polyline/wire wp5/wp6/wp7 has centroid height 29.967638? Wait wp5 is Workplane('XZ'), wp6 = polyline, wp7 = close. The 2D shape centroid height (z) is 29.967638. wp8 extruded 50 has centroid z same? Extruding along Y preserves z centroid, yes. wp9 translated only y, z centroid remains 29.967638. So many variables (wp5, wp6, wp7, wp8, wp9) all have same z centroid. Need choose among remaining candidates with greatest centroid Y coordinate. Now what are "remaining candidates" after filtering by height? Could be all features with height 29.967638. Among them choose greatest centroid Y coordinate. Which variable has greatest Y coordinate? Let's examine:
- wp5, wp6, wp7: Workplane/polyline/wire on XZ plane at y=0, so centroid y=0.
- wp8: extruded by 50. If extrusion direction is +Y, its y coordinate range from 0 to50, centroid y=25.
- wp9: translated by [0,-25,0], y centroid 0.
Thus among wp5, wp6, wp7, wp8, wp9, the greatest centroid Y coordinate is wp8 with y=25. If considering wp4? no. So answer likely wp8. But wait wp8 is the extrusion of first polygon before translation. It has centroid height 29.967638 and centroid Y coordinate 25 (greatest among these). But question says "The target feature has centroid Y coordinate." Maybe this means not a specific value, just has property; among remaining candidates choose greatest centroid Y. Then wp8 indeed.

But need be careful: There might be other extruded prisms before translation whose centroid z also 29.967638? Only first polygon A. But the extrusion wp8 has z centroid 29.967638. Its y centroid is 25. The translated wp9 has y=0. So wp8 is max. Is there any other variable with same z but y greater? No.

However, could "feature" refer to final resulting solid of cut wp10 after first cut? The target feature maybe a face? But no.

Let's verify if target "centroid height equal to 29.967638" might refer to a *face* centroid of torus? But first cut polygon centroid exactly 29.967638, so clearly.

Need consider if "centroid height" could mean centroid z-coordinate of a solid after extrusion? Yes, z centroid unchanged. So wp8 chosen if max y.

Need maybe answer "wp8" or maybe "wp7"? Let's reason with source variables. The script:
wp5 = cq.Workplane('XZ')
wp6 = wp5.polyline([...])
wp7 = wp6.close()
wp8 = wp7.extrude(50)
wp9 = wp8.translate([0,-25,0])

If asking "source variable name" for target feature, the feature of a polyline? Usually feature might be a Workplane or solid. In examples, they might ask "Return exactly one source variable name, for example `wp7`." If target feature has centroid height equal to polygon centroid, the object is the wire/polyline? The "centroid height" of a wire (closed polyline) may be average? Actually a closed wire has no area centroid? But in CadQuery, a Workplane containing a wire might have `val()`? Hmm.

Let's inspect CadQuery semantics. `wp5 = cq.Workplane('XZ')` empty plane. `wp6 = wp5.polyline(...)` creates edges/wire? `wp7 = wp6.close()` closes wire. It is a 2D wire. `wp8 = wp7.extrude(50)` creates a solid. "Feature" in output might be each of these objects? The script has variables all over. If you search for a feature by centroid height, what are the candidate features? Could be all variables (Workplane objects) in script. The target feature should be "source variable name", so likely they expect one of the variables whose associated shape (wire, solid) meets constraints. They specifically mention "wp7" as example. In many such questions from this dataset, they describe a CAD script that creates a sequence of shapes, then apply boolean cuts, then ask to identify a target feature among "candidate features" by properties (centroid, volume, etc.) and return source variable. The candidates are usually the shapes created before boolean operations (wp1, wp2, ... each variable). The constraints can be applied to each variable's shape (e.g., centroid of 2D wire? or 3D solid?).

Need infer dataset style. They often ask "Given CadQuery script, answer question by reasoning about CAD construction." The script has variables wp1, wp2, etc. They ask "Identify the target feature that satisfies all constraints: centroid height equal to ..., centroid Y coordinate ... Among remaining candidates choose greatest centroid Y coordinate." The "source variable name" likely refers to variable that generated a geometric object (wire or solid). The constraints refer to geometric properties of that object. For a 2D wire with area? A closed wire in CadQuery has center? If it's a wire, not a face, centroid might not be defined. But perhaps `wp7` (closed wire) as a Workplane object has selected vertices/edges? `wp7.val()` is a Wire; center of bounding box? Hmm.

Let's examine script. Each cut feature is created via polyline -> close -> extrude -> translate. If the "feature" is the shape used to cut, the stable geometric object is the solid (wp8) before translate, because it has volume and centroid. The 2D wire wp7 is just a cross-section; its "centroid height" as a collection of line segments may be different? Let's compute centroid of wire boundary? For a closed polyline, the average of vertices? Let's compute maybe 29.0? But target 29.967638 exactly matched area centroid of the polygon face, not boundary. Area centroid is a property of the face/solid cross-section. A closed wire alone does not have an area centroid in CadQuery; the Workplane with a closed wire may not represent a face until extruded. So likely they consider the extruded solid wp8/en. The extrude creates a solid whose centroid z equals area centroid of the polygon. So wp8 is the first solid with that centroid. Then `wp9` is translated: still same solid but y shifted. They ask among remaining candidates with height 29.967638 choose greatest centroid Y coordinate. For wp8, y centroid=25; for wp9, y=0; for wp4? no. So wp8.

Need ensure "centroid Y coordinate" is greatest among candidates with same height. Could include wp8 and wp9? What about wp4 base torus? Its centroid height is 0? Not 29.967638. No.

Could there be other variables after cuts with z centroid 29.967638? The remaining base after first cut wp10 might have a solid feature with centroid y maybe nonzero? But source variable wp10 is the result of cut (a solid). Its centroid y=0 by symmetry; z maybe? Not likely exactly. But "remaining candidates" after first constraint could include final result or each intermediate result? Need consider all variables with centroid height 29.967638. Many variables after extrude of first polygon retain z centroid? Actually `wp10 = wp4.cut(wp9)` is the base torus minus first cut. Its centroid is not simply same as polygon; likely not 29.967638. So no.

Let's compute if the first cut prism before translation wp8 has centroid y=25. It is not actually used in final result directly (the translated version is used). But the question asks source variable name; source variable wp8 is the feature created by extruding the polygon. Does it satisfy "target feature has centroid height 29.967638" and "centroid Y coordinate"? Yes. They didn't require that the feature exists in final result? "target feature" might be one of the candidate features in the CAD script, not final result. So wp8.

Let's also examine if there is another extruded polygon with z centroid exactly 29.967638? Let's approximate F: maybe 24.5, not. So only first.

Need decide final answer format: JSON tool call with `text` containing "wp8". The final response must end with exactly one JSON tool call. They asked reason first then emit. Need include concise reasoning under 250 words. The answer should be exactly one JSON tool call. We can include reasoning before JSON. Ensure final message ends with JSON call.

Let's formulate reasoning:
- Base torus; cuts are prisms extruded along Y.
- The target height 29.967638 matches the first cut polygon's area centroid.
- Compute shoelace for first polygon A: area 618, z-centroid = 111120/(6*618)=29.967638.
- The first polygon produces wp7 (closed wire), wp8 (extrude), wp9 (translated). The extrusion before translation has Y centroid = 25 (since extrude 50 from y=0); the translated one has y=0. Therefore among candidates with matching height, greatest centroid Y coordinate is wp8's solid.
Actually wp6/wp5 y=0, wp7 y=0, wp8 y=25, wp9 y=0. So wp8.

Need be precise: wp7 is a closed wire, not a solid; if considered, its y=0. wp8 is the extrusion, y=25. So answer wp8.

Let's verify if extrude direction from Workplane 'XZ' might be negative Y, making y centroid -25? Need know CadQuery extrude direction. Workplane('XZ') has normal in which direction? In CadQuery, plane `XZ` is defined by xDir=(1,0,0), normal=(0,-1,0)? Actually let's recall. CadQuery's plane class: Plane.XZ is normal (0, -1, 0)? Let's check memory: `cq.Plane.XZ` has xDir=(1,0,0), normal=(0,1,0)? Not sure. The default extrusion direction is along the normal of the workplane. If normal is negative Y, extrusion from 0 to -50, centroid y=-25. The later translate [0,-25,0] would then put centroid y=-50? But the script translates by -25 after extrude. If the extrusion went from 0 to -50, translation -25 would put range -25 to -75, not symmetric around torus. But the cut solids need span y=-25 to25 to cut torus fully. Therefore the extrusion is likely from 0 to +50 and translate -25 to get (-25,25). So normal is +Y. Good. Workplane('XZ') in CadQuery likely normal is +Y? Wait coordinate axes: XZ plane has x right, z vertical? In CAD, Y axis is normal to XZ plane, but could be +Y or -Y depending handedness. CadQuery maybe uses right-handed coordinate system: XY plane normal +Z, YZ plane normal +X, ZX plane normal +Y? Let's verify: Plane `XZ`: xDirection=(1,0,0), normal=(0,1,0)? Actually if you take X and Z axes, their cross product X × Z = (1,0,0) × (0,0,1) = (0,-1,0). But CadQuery may choose normal such that xDir and yDir? Hmm. In CadQuery, `Workplane("XZ")` means the workplane contains X and Z axes; its normal is Y. The direction of Y? For plane normal, positive side might be +Y? Let's recall from common usage: `Workplane("XZ").circle(10).extrude(5)` extrudes in positive Y? Many examples use Workplane("XY").circle(...).extrude(5) extrudes in +Z. So Workplane("XZ") extrudes in +Y? I think yes, because the plane's normal is the third axis according to "XZ" maybe +Y. In CadQuery source: `Plane.XZ = Plane(origin=(0,0,0), xDir=(1,0,0), normal=(0,1,0))`? Wait if xDir is (1,0,0) and normal (0,1,0), then yDir = normal.cross(xDir) = (0,1,0)x(1,0,0)=(0,0,-1). That would make local y opposite Z. But that might be okay. For plane "XZ", local coordinates: x = X, y = Z? Actually the two in-plane axes are X and Z. The normal is Y. The local y direction should be Z maybe. If xDir=(1,0,0), normal=(0,1,0), then local yDir = cross(normal, xDir)? Let's derive: In CadQuery, Plane has xDir and normal; yDir = normal.cross(xDir)? I think yDir = normal.cross(xDir) gives (0,1,0)x(1,0,0)=(0,0,-1). So local coordinates (u,v) map to x=xDir*u + yDir*v. For a point at local (0,1), v=1 gives yDir=(0,0,-1), so it maps to z negative. But Workplane('XZ') should map local y to global Z. So they might use yDir = xDir.cross(normal)? Let's check. If xDir=(1,0,0), normal=(0,1,0), xDir.cross(normal)=(0,0,-1). Not good. If normal=(0,-1,0), xDir.cross(normal)=(0,0,1), so local y=Z. So Plane.XZ likely normal=(0,-1,0). Then extrude along normal = -Y, not +Y. Hmm.

But in CadQuery, `Workplane("XZ")` examples: Drawing a circle in XZ and extruding might extrude in -Y? Let's recall from CadQuery docs: The normal for `Workplane("XZ")` is (0, -1, 0)? Actually from source code: `Plane.XZ = Plane(origin=(0,0,0), xDir=(1,0,0), normal=(0,-1,0))` because `XZ` means two axes X and Z, normal is Y but negative to maintain right-handed? Let me check memory: In CadQuery, `Plane.XY`: xDir=(1,0,0), normal=(0,0,1); yDir=(0,1,0). For `Plane.YZ`: xDir=(0,1,0), normal=(1,0,0)? Hmm.

Let's not rely. The script explicitly translates by [0,-25,0] after extrusion. If the natural extrusion was along -Y, translating by -25 would make it more negative, not centered. But maybe the cut solids are intended to cut from y=-? Let's determine actual final use. The base torus has y extent? The torus centered at y=0 extends y from -25 to +25. The cut prisms need span y min/max covering torus. If extrude length 50 along +Y from 0 to50, translate -25 -> -25..25. If extrude along -Y from 0 to -50, translate -25 -> -25.. -75, which would miss most of torus and not intersect? Wait if translate [0,-25,0] and original extrusion along -Y goes y=0 to -50, resulting y=-25 to -75. That is completely outside torus (y range -25..25), no cut! So the script would be nonsense. Therefore for the script to work as intended, extrusion must be along +Y. So Workplane('XZ') normal is +Y? Or maybe extruding (-Y) from 0 to -50 then translate +25 would center, but it's -25 not. So yes, normal +Y. Thus y centroid of wp8 is 25.

Need maybe check: The first polygon is translated with [0,-25,0] before cutting. If wp8 extrude +Y from 0 to 50, wp9 centroid y=0, correct.

Thus answer wp8.

Let's produce final with reasoning and JSON call. Keep reasoning under 250 words. Use final.

The target height 29.967638 matches the first polyline feature. Computing its centroid: area = 618, z-centroid = 111120 / 3708 = 29.967638.

That feature corresponds to the first polygon:
- `wp7` is the closed wire on XZ (y = 0).
- `wp8` is the extrusion along +Y, so its centroid Y = 25.
- `wp9` is translated down, returning centroid Y = 0.

Among heights matching 29.967638, `wp8` has the greatest centroid Y coordinate.

```json
{"name": "submit_text", "arguments": {"text": "wp8"}}
```
