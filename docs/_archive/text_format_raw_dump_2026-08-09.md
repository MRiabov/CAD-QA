# CAD-QA `text`-format raw dump (v3_curriculum + SFT traces)

- Source: HF `MRiabov/cadqa-rl-2000` config `v3_curriculum` (local datasets cache arrow, 1445 rows) + `runs/gemma_bench/rl/sft_traces_final.jsonl` (275 traces).
- `text` format rows: **949**. All golds are flat strings; **no colon-joined (`wp1:abc:def`) answers exist anywhere** — the conventions are: unquoted `wpN`, quoted `"wpN"`, `wpN_center`, full `cq.Plane(...)` strings, plane-selector tokens (`XY`/`XZ`/...), membership tokens (`outside`).
- This dump exists to pick the tool-per-shape mapping. Generated 2026-08-09 (regenerated: 6a now shows the ACTUAL final submission — last valid JSON object per trace).

## 1. All formats in v3_curriculum (overview)

| format | rows | tool today | gold example |
|---|---|---|---|
| candidate_label | 295 | submit_label | 'wp9' |
| text | 949 | submit_text | 'wp1' |
| coordinate | 135 | submit_coordinate | '[-98.5, 42.5, 90]' |
| bbox | 17 | submit_bbox | '{"max": [-16.26, 95.58, -46.0], "min": [-25.74, 92.42, -56.0]}' |
| number | 16 | submit_number | '374900' |
| integer | 17 | submit_integer | '1' |
| json | 16 | submit_workplane | '{"base": "cq", "coordinate_frame": "cq.Plane(origin=cq.Vector(28, 85, ' |

## 2. `text`-format shapes

| shape | rows | gold pattern | options in prompt today |
|---|---|---|---|
| wp | 677 | `wpN` | 0 |
| quoted_wp | 233 | `"wpN"` | 0 |
| wp_center | 22 | `wpN_center` | 0 |
| plane | 11 | `cq.Plane(...)` | 11 |
| other | 6 | `XY`/`XZ`/`outside` | 3 |

Per-shape row_id question families (from row_id suffix):
- **wp**: {'parameterized_feature_extreme': 226, 'argmin_origin_z_workplane': 188, 'argmax_origin_z_workplane': 132, 'parameterized_feature_rank': 131}
- **quoted_wp**: {'parameterized_feature_rank': 42, 'parameterized_equal_feature_metric_rank': 36, 'parameterized_equal_feature_metric_extreme': 36, 'parameterized_feature_extreme': 26, 'parameterized_void_region_rank': 21, 'parameterized_feature_effect_delta_extreme': 19, 'parameterized_material_region_extreme': 16, 'parameterized_material_region_rank': 13, 'parameterized_void_region_extreme': 13, 'row:graph:src_2198a027ed1a6245:synth:parameterized_feature_effect_delta_extreme': 1, 'row:graph:src_965d6cf1e63f032e:synth:parameterized_feature_effect_delta_extreme': 1, 'parameterized_material_region_reference_entity_distance': 1}
- **wp_center**: {'argmax_origin_z_workplane': 11, 'argmin_origin_z_workplane': 11}
- **plane**: {'cadqa_coordinate_frame_255f68d7d652d955': 1, 'cadqa_coordinate_frame_34066716c9cd26d1': 1, 'cadqa_coordinate_frame_9136c3fa41790f62': 1, 'cadqa_coordinate_frame_84dbfb4a2e3c199a': 1, 'cadqa_coordinate_frame_58520e8997a498d8': 1, 'cadqa_coordinate_frame_ded7f8b14a4214ce': 1, 'cadqa_coordinate_frame_6b8031b00f5caafb': 1, 'cadqa_coordinate_frame_771ddff402c042f4': 1, 'cadqa_coordinate_frame_16755945735e8dfd': 1, 'cadqa_coordinate_frame_34be2d2cb6dbfd6b': 1, 'cadqa_coordinate_frame_6fc5fec0e50f913d': 1}
- **other**: {'cadqa_coordinate_frame_5ee53d30742db479': 1, 'cadqa_coordinate_frame_3fc34533f867475e': 1, 'cadqa_point_membership_73d613a36eb7ba7d': 1, 'cadqa_point_membership_f739492a566df045': 1, 'cadqa_point_membership_45983b175c10d33a': 1, 'cadqa_coordinate_frame_fa0f30cb24e9b0b7': 1}

## 3. Distinct gold values per shape

### wp — 677 rows, 45 distinct values

Most common: `wp1` ×180, `wp6` ×71, `wp10` ×59, `wp18` ×41, `wp9` ×35, `wp5` ×34, `wp11` ×28, `wp13` ×26, `wp7` ×25, `wp15` ×23, `wp8` ×22, `wp4` ×17, `wp14` ×13, `wp16` ×12, `wp12` ×12, `wp17` ×11, `wp2` ×10, `wp3` ×8, `wp30` ×6, `wp20` ×6, `wp27` ×3, `wp58` ×3, `wp28` ×3, `wp19` ×2, `wp26` ×2
Full list: wp1, wp10, wp11, wp12, wp13, wp14, wp15, wp16, wp17, wp18, wp19, wp2, wp20, wp21, wp22, wp23, wp26, wp27, wp28, wp29, wp3, wp30, wp31, wp32, wp34, wp37, wp39, wp4, wp40, wp48, wp5, wp51, wp52, wp58, wp59, wp6, wp60, wp62, wp63, wp64, wp7, wp73, wp8, wp84, wp9

### quoted_wp — 233 rows, 48 distinct values

Most common: `"wp6"` ×19, `"wp3"` ×18, `"wp7"` ×14, `"wp2"` ×14, `"wp11"` ×12, `"wp14"` ×11, `"wp4"` ×11, `"wp5"` ×11, `"wp15"` ×10, `"wp12"` ×9, `"wp16"` ×8, `"wp8"` ×8, `"wp9"` ×7, `"wp13"` ×6, `"wp20"` ×6, `"wp17"` ×6, `"wp21"` ×5, `"wp19"` ×4, `"wp10"` ×4, `"wp23"` ×4, `"wp40"` ×3, `"wp32"` ×3, `"wp18"` ×3, `"wp27"` ×3, `"wp25"` ×3
Full list: "wp10", "wp11", "wp12", "wp13", "wp14", "wp15", "wp16", "wp17", "wp18", "wp19", "wp2", "wp20", "wp21", "wp22", "wp23", "wp24", "wp25", "wp26", "wp27", "wp28", "wp3", "wp30", "wp31", "wp32", "wp33", "wp34", "wp35", "wp36", "wp37", "wp38", "wp4", "wp40", "wp42", "wp43", "wp44", "wp45", "wp47", "wp5", "wp54", "wp56", "wp6", "wp60", "wp62", "wp7", "wp71", "wp8", "wp88", "wp9"

### wp_center — 22 rows, 6 distinct values

- `wp14_center` (×1)
- `wp16_center` (×9)
- `wp26_center` (×9)
- `wp27_center` (×1)
- `wp34_center` (×1)
- `wp42_center` (×1)

### plane — 11 rows, 10 distinct values

- `cq.Plane(origin=cq.Vector(-21, -94, -21), xDir=cq.Vector(-3, 1, 0), normal=cq.Vector(-1, -3, 0))` (×1)
- `cq.Plane(origin=cq.Vector(-21, 94, 21), xDir=cq.Vector(3, 1, 0), normal=cq.Vector(-1, 3, 0))` (×1)
- `cq.Plane(origin=cq.Vector(-72, 53, -53), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(-2, 2, 0))` (×1)
- `cq.Plane(origin=cq.Vector(-72, 53, 36), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(-2, 2, 0))` (×1)
- `cq.Plane(origin=cq.Vector(-87, -42, -31), xDir=cq.Vector(1, -2, 0), normal=cq.Vector(-2, -1, 0))` (×1)
- `cq.Plane(origin=cq.Vector(-87, 42, -41), xDir=cq.Vector(-1, -2, 0), normal=cq.Vector(-2, 1, 0))` (×1)
- `cq.Plane(origin=cq.Vector(28, -85, -18), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0))` (×1)
- `cq.Plane(origin=cq.Vector(28, -85, 72), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0))` (×1)
- `cq.Plane(origin=cq.Vector(28, 85, -71), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))` (×2)
- `cq.Plane(origin=cq.Vector(28, 85, 18), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))` (×1)

### other — 6 rows, 3 distinct values

- `XY` (×2)
- `XZ` (×1)
- `outside` (×3)

## 4. Full example prompts per shape

### wp (showing 3 of 677)

**row_id:** `row:graph:graph:src_1e593fa3037ad99b:q1:argmax_origin_z_workplane` | **hop:** 1 | **gold:** `wp1`

```text
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

Identify the target workplane that satisfies all of these constraints:
- Among the remaining candidates, choose the one with the greatest workplane origin height.

Return exactly one source variable name, for example `wp7`.
```

**row_id:** `row:graph:graph:src_1e593fa3037ad99b:q1:argmin_origin_z_workplane` | **hop:** 1 | **gold:** `wp1`

```text
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

Identify the target workplane that satisfies all of these constraints:
- Among the remaining candidates, choose the one with the smallest workplane origin height.

Return exactly one source variable name, for example `wp7`.
```

**row_id:** `row:graph:graph:src_96bc0eb5f4e91f44:q1:argmax_origin_z_workplane` | **hop:** 1 | **gold:** `wp14`

```text
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -43))
wp2 = wp1.circle(37)
wp3 = wp2.workplane(offset=100)
wp4 = wp3.circle(43)
wp5 = wp4.loft(combine=True)
wp6 = cq.Workplane('XY', origin=(0, 0, -43))
wp7 = wp6.circle(29)
wp8 = wp7.workplane(offset=100)
wp9 = wp8.circle(35)
wp10 = wp9.loft(combine=True)
wp11 = wp5.cut(wp10)
wp12 = cq.Workplane('XY', origin=(0, 0, -43))
wp13 = wp12.splineApprox([[27, 0, 0], [17, 21, 4], [-5, 27, 8], [-24, 13, 12], [-26, -10, 16], [-9, -26, 20], [15, -24, 24], [28, -4, 28], [21, 20, 32], [-2, 29, 36], [-24, 17, 40], [-28, -7, 44], [-13, -27, 48], [13, -27, 52], [29, -7, 56], [24, 18, 60], [2, 30, 64], [-22, 21, 68], [-31, -4, 72], [-17, -26, 76], [10, -30, 80], [30, -12, 84], [28, 15, 88], [6, 32, 92], [-21, 25, 96], [-33, 0, 100]], makeWire=True)
wp14 = cq.Workplane(cq.Plane(origin=cq.Vector(27, 0, 7), xDir=cq.Vector(2, 0, 0), normal=cq.Vector(0, -2, 0)))
wp15 = wp14.rect(4, 100)
wp16 = wp15.sweep(wp13, isFrenet=True, multisection=True)
wp17 = wp11.union(wp16, clean=True)
result = wp17
```

Identify the target workplane that satisfies all of these constraints:
- Among the remaining candidates, choose the one with the greatest workplane origin height.

Return exactly one source variable name, for example `wp7`.
```

### quoted_wp (showing 3 of 233)

**row_id:** `row:graph:src_2fcfebe03ee4bafe:synth:v3:parameterized_equal_feature_metric_rank` | **hop:** 3 | **gold:** `"wp19"`

```text
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY')
wp2 = wp1.sphere(633)
wp3 = cq.Workplane(cq.Plane(origin=cq.Vector(100, 0, 0), xDir=cq.Vector(0, 0, 3), normal=cq.Vector(3, 0, 0)))
wp4 = wp3.box(1267, 1267, 1267, centered=[1, 1, 0])
wp5 = wp2.cut(wp4)
wp6 = cq.Workplane(cq.Plane(origin=cq.Vector(-100, 0, 0), xDir=cq.Vector(0, 0, -3), normal=cq.Vector(-3, 0, 0)))
wp7 = wp6.box(1267, 1267, 1267, centered=[1, 1, 0])
wp8 = wp5.cut(wp7)
wp9 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 100, 0), xDir=cq.Vector(0, 0, 3), normal=cq.Vector(0, 3, 0)))
wp10 = wp9.box(1267, 1267, 1267, centered=[1, 1, 0])
wp11 = wp8.cut(wp10)
wp12 = cq.Workplane(cq.Plane(origin=cq.Vector(0, -100, 0), xDir=cq.Vector(0, 0, -3), normal=cq.Vector(0, -3, 0)))
wp13 = wp12.box(1267, 1267, 1267, centered=[1, 1, 0])
wp14 = wp11.cut(wp13)
wp15 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 0, 100), xDir=cq.Vector(3, 0, 0), normal=cq.Vector(0, 0, 3)))
wp16 = wp15.box(1267, 1267, 1267, centered=[1, 1, 0])
wp17 = wp14.cut(wp16)
wp18 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 0, -100), xDir=cq.Vector(-3, 0, 0), normal=cq.Vector(0, 0, -3)))
wp19 = wp18.box(1267, 1267, 1267, centered=[1, 1, 0])
wp20 = wp17.cut(wp19)
result = wp20
```

Identify the target feature that satisfies all of these constraints:
- The target feature matches the overall height value 1267.0.
- The target feature can be described by its centroid height.
- Within the narrowed set, select the 6th candidate in decreasing centroid height order.

Return exactly one source variable name, for example `wp7`.
```

**row_id:** `row:graph:src_7964d0e318f03e1f:synth:v1:parameterized_void_region_rank` | **hop:** 3 | **gold:** `"wp7"`

```md
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -100))
wp2 = wp1.polygon(10, 42)
wp3 = wp2.extrude(135)
wp4 = cq.Workplane('XY', origin=(0, 0, -100))
wp5 = wp4.polygon(10, 35)
wp6 = wp5.extrude(135)
wp7 = wp3.cut(wp6)
wp8 = cq.Workplane('XY', origin=(0, 0, -100))
wp9 = wp8.center(0, 68)
wp10 = wp9.rect(32, 13)
wp11 = wp10.extrude(129)
wp12 = wp7.cut(wp11)
wp13 = cq.Workplane('XY', origin=(0, 0, -100))
wp14 = wp13.center(0, 100)
wp15 = wp14.rect(32, 13)
wp16 = wp15.extrude(129)
wp17 = wp12.cut(wp16)
wp18 = cq.Workplane('XY', origin=(0, 0, -100))
wp19 = wp18.center(0, 132)
wp20 = wp19.rect(32, 13)
wp21 = wp20.extrude(129)
wp22 = wp17.cut(wp21)
wp23 = cq.Workplane('XY', origin=(0, 0, -100))
wp24 = wp23.center(0, 164)
wp25 = wp24.rect(32, 13)
wp26 = wp25.extrude(129)
wp27 = wp22.cut(wp26)
wp28 = cq.Workplane('XY', origin=(0, 0, -100))
wp29 = wp28.center(0, 196)
wp30 = wp29.rect(32, 13)
wp31 = wp30.extrude(129)
wp32 = wp27.cut(wp31)
wp33 = cq.Workplane(cq.Plane(origin=cq.Vector(20, 6, 96), xDir=cq.Vector(-1, 3, 0), normal=cq.Vector(3, 1, 0)))
wp34 = wp33.circle(4)
wp35 = wp34.extrude(4)
wp36 = wp32.union(wp35)
wp37 = cq.Workplane(cq.Plane(origin=cq.Vector(12, 17, 96), xDir=cq.Vector(-3, 2, 0), normal=cq.Vector(2, 3, 0)))
wp38 = wp37.circle(4)
wp39 = wp38.extrude(4)
wp40 = wp36.union(wp39)
wp41 = cq.Workplane(cq.Plane(origin=cq.Vector(0, 21, 96), xDir=cq.Vector(-3, 0, 0), normal=cq.Vector(0, 3, 0)))
wp42 = wp41.circle(4)
wp43 = wp42.extrude(4)
wp44 = wp40.union(wp43)
wp45 = cq.Workplane(cq.Plane(origin=cq.Vector(-12, 17, 96), xDir=cq.Vector(-3, -2, 0), normal=cq.Vector(-2, 3, 0)))
wp46 = wp45.circle(4)
wp47 = wp46.extrude(4)
wp48 = wp44.union(wp47)
wp49 = cq.Workplane(cq.Plane(origin=cq.Vector(-20, 6, 96), xDir=cq.Vector(-1, -3, 0), normal=cq.Vector(-3, 1, 0)))
wp50 = wp49.circle(4)
wp51 = wp50.extrude(4)
wp52 = wp48.union(wp51)
wp53 = cq.Workplane(cq.Plane(origin=cq.Vector(-20, -6, 96), xDir=cq.Vector(1, -3, 0), normal=cq.Vector(-3, -1, 0)))
wp54 = wp53.circle(4)
wp55 = wp54.extrude(4)
wp56 = wp52.union(wp55)
wp57 = cq.Workplane(cq.Plane(origin=cq.Vector(-12, -17, 96), xDir=cq.Vector(3, -2, 0), normal=cq.Vector(-2, -3, 0)))
wp58 = wp57.circle(4)
wp59 = wp58.extrude(4)
wp60 = wp56.union(wp59)
wp61 = cq.Workplane(cq.Plane(origin=cq.Vector(0, -21, 96), xDir=cq.Vector(3, 0, 0), normal=cq.Vector(0, -3, 0)))
wp62 = wp61.circle(4)
wp63 = wp62.extrude(4)
wp64 = wp60.union(wp63)
wp65 = cq.Workplane(cq.Plane(origin=cq.Vector(12, -17, 96), xDir=cq.Vector(3, 2, 0), normal=cq.Vector(2, -3, 0)))
wp66 = wp65.circle(4)
wp67 = wp66.extrude(4)
wp68 = wp64.union(wp67)
wp69 = cq.Workplane(cq.Plane(origin=cq.Vector(20, -6, 96), xDir=cq.Vector(1, 3, 0), normal=cq.Vector(3, -1, 0)))
wp70 = wp69.circle(4)
wp71 = wp70.extrude(4)
wp72 = wp68.union(wp71)
wp73 = wp72.edges('|Z')
wp74 = wp73.fillet(1)
result = wp74
```

Identify the target removed-material region that satisfies all of these constraints:
- The target is a region of material removed by a cut.
- The target removed-material region has increase in edge count.
- Among the remaining candidates, choose the 6th candidate when ordered from greatest to smallest increase in edge count.

Return exactly one source variable name, for example `wp7`.
```

**row_id:** `row:graph:src_bb0e01f49805670f:synth:v4:parameterized_equal_feature_metric_extreme` | **hop:** 3 | **gold:** `"wp3"`

```text
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('XY')
wp2 = wp1.box(200, 76, 11)
wp3 = wp2.edges()
wp4 = wp3.fillet(2)
wp5 = wp4.faces('>Z')
wp6 = wp5.workplane()
wp7 = wp6.pushPoints([[-93, -28], [-93, -9], [-93, 9], [-93, 28], [-74, -28], [-74, -9], [-74, 9], [-74, 28], [-56, -28], [-56, -9], [-56, 9], [-56, 28], [-37, -28], [-37, -9], [-37, 9], [-37, 28], [-19, -28], [-19, -9], [-19, 9], [-19, 28], [0, -28], [0, -9], [0, 9], [0, 28], [19, -28], [19, -9], [19, 9], [19, 28], [37, -28], [37, -9], [37, 9], [37, 28], [56, -28], [56, -9], [56, 9], [56, 28], [74, -28], [74, -9], [74, 9], [74, 28], [93, -28], [93, -9], [93, 9], [93, 28]])
wp8 = wp7.circle(7)
wp9 = wp8.cutThruAll()
wp10 = wp9.faces('<Z')
wp11 = wp10.workplane()
wp12 = wp11.pushPoints([[-93, -28], [-93, -9], [-93, 9], [-93, 28], [-74, -28], [-74, -9], [-74, 9], [-74, 28], [-56, -28], [-56, -9], [-56, 9], [-56, 28], [-37, -28], [-37, -9], [-37, 9], [-37, 28], [-19, -28], [-19, -9], [-19, 9], [-19, 28], [0, -28], [0, -9], [0, 9], [0, 28], [19, -28], [19, -9], [19, 9], [19, 28], [37, -28], [37, -9], [37, 9], [37, 28], [56, -28], [56, -9], [56, 9], [56, 28], [74, -28], [74, -9], [74, 9], [74, 28], [93, -28], [93, -9], [93, 9], [93, 28]])
wp13 = wp12.circle(7)
wp14 = wp13.cutThruAll()
wp15 = wp14.faces('>Y')
wp16 = wp15.workplane()
wp17 = wp16.pushPoints([[-93, 0], [-74, 0], [-56, 0], [-37, 0], [-19, 0], [0, 0], [19, 0], [37, 0], [56, 0], [74, 0], [93, 0]])
wp18 = wp17.polygon(4, 14)
wp19 = wp18.cutThruAll()
wp20 = wp19.faces('<Y')
wp21 = wp20.workplane()
wp22 = wp21.pushPoints([[-93, 0], [-74, 0], [-56, 0], [-37, 0], [-19, 0], [0, 0], [19, 0], [37, 0], [56, 0], [74, 0], [93, 0]])
wp23 = wp22.polygon(4, 14)
wp24 = wp23.cutThruAll()
wp25 = wp24.faces('>X')
wp26 = wp25.workplane()
wp27 = wp26.pushPoints([[-28, 0], [-9, 0], [9, 0], [28, 0]])
wp28 = wp27.polygon(4, 14)
wp29 = wp28.cutThruAll()
wp30 = wp29.faces('<X')
wp31 = wp30.workplane()
wp32 = wp31.pushPoints([[-28, 0], [-9, 0], [9, 0], [28, 0]])
wp33 = wp32.polygon(4, 14)
wp34 = wp33.cutThruAll()
result = wp34
```

Identify the target feature that satisfies all of these constraints:
- The target feature has centroid X coordinate equal to 0.0.
- The target feature has volume.
- Among the remaining candidates, choose the one with the smallest volume.

Return exactly one source variable name, for example `wp7`.
```

### wp_center (showing 3 of 22)

**row_id:** `row:graph:graph:src_3dac547343362b42:q1:argmax_origin_z_workplane` | **hop:** 1 | **gold:** `wp16_center`

```text
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

**row_id:** `row:graph:graph:src_3dac547343362b42:q1:argmin_origin_z_workplane` | **hop:** 1 | **gold:** `wp26_center`

```text
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
- Among the remaining candidates, choose the one with the smallest workplane origin height.

Return exactly one source variable name, for example `wp7`.
```

**row_id:** `row:graph:graph:src_7f805e6088e4c466:q1:argmax_origin_z_workplane` | **hop:** 1 | **gold:** `wp27_center`

```text
Given the CadQuery script below, answer the question by reasoning about the CAD construction.

```python
import cadquery as cq
wp1 = cq.Workplane('YZ', origin=(-100, 0, 0))
wp2 = wp1.circle(42)
wp3 = wp2.extrude(131)
wp4 = cq.Workplane(cq.Plane(origin=cq.Vector(-34, 0, 42), xDir=cq.Vector(0, 3, 0), normal=cq.Vector(3, 0, 0)))
wp5 = wp4.circle(42)
wp6 = wp5.extrude(134)
wp7 = cq.Workplane(cq.Plane(origin=cq.Vector(-34, 0, -42), xDir=cq.Vector(0, 3, 0), normal=cq.Vector(3, 0, 0)))
wp8 = wp7.circle(42)
wp9 = wp8.extrude(134)
wp10 = cq.Workplane(cq.Plane(origin=cq.Vector(-34, 0, 0), xDir=cq.Vector(0, 3, 0), normal=cq.Vector(3, 0, 0)))
wp11 = wp10.circle(57)
wp12 = wp11.extrude(-21)
wp13 = cq.Workplane(cq.Plane(origin=cq.Vector(-34, 0, 0), xDir=cq.Vector(0, 3, 0), normal=cq.Vector(3, 0, 0)))
wp14 = wp13.center(0, 42)
wp15 = wp14.circle(42)
wp16 = wp15.extrude(-21)
wp17 = cq.Workplane(cq.Plane(origin=cq.Vector(-34, 0, 0), xDir=cq.Vector(0, 3, 0), normal=cq.Vector(3, 0, 0)))
wp18 = wp17.center(0, -42)
wp19 = wp18.circle(42)
wp20 = wp19.extrude(-21)
wp21 = wp3.union(wp6)
wp22 = wp21.union(wp9)
wp23 = wp16.union(wp20)
wp24 = wp12.cut(wp23)
wp25 = wp22.union(wp24)
wp26 = cq.Workplane(cq.Plane(origin=cq.Vector(-34, 0, 42), xDir=cq.Vector(0, 3, 0), normal=cq.Vector(3, 0, 0)))
wp27 = wp26.center(0, 42)
wp28 = wp27.circle(3)
wp29 = wp28.extrude(-2)
wp30 = wp25.cut(wp29)
wp31 = cq.Workplane(cq.Plane(origin=cq.Vector(-34, 0, 42), xDir=cq.Vector(0, 3, 0), normal=cq.Vector(3, 0, 0)))
wp32 = wp31.center(0, -42)
wp33 = wp32.circle(3)
wp34 = wp33.extrude(-2)
wp35 = wp30.cut(wp34)
wp36 = cq.Workplane(cq.Plane(origin=cq.Vector(-34, 0, -42), xDir=cq.Vector(0, 3, 0), normal=cq.Vector(3, 0, 0)))
wp37 = wp36.center(0, 42)
wp38 = wp37.circle(3)
wp39 = wp38.extrude(-2)
wp40 = wp35.cut(wp39)
wp41 = cq.Workplane(cq.Plane(origin=cq.Vector(-34, 0, -42), xDir=cq.Vector(0, 3, 0), normal=cq.Vector(3, 0, 0)))
wp42 = wp41.center(0, -42)
wp43 = wp42.circle(3)
wp44 = wp43.extrude(-2)
wp45 = wp40.cut(wp44)
result = wp45
```

Identify the target workplane that satisfies all of these constraints:
- Among the remaining candidates, choose the one with the greatest workplane origin height.

Return exactly one source variable name, for example `wp7`.
```

### plane (showing 3 of 11)

**row_id:** `cadqa_coordinate_frame_255f68d7d652d955` | **hop:** 0 | **gold:** `cq.Plane(origin=cq.Vector(-72, 53, 36), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(-2, 2, 0))`

```text
Given the CadQuery script below, what coordinate frame or workplane name is established by feature `wp27`? Answer with exactly one listed token.

Choices: XY, YZ, XZ, front, back, left, right, top, bottom, inherited, unknown, cq.Plane(origin=cq.Vector(-72, 53, 36), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(-2, 2, 0))

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -89))
wp2 = wp1.splineApprox([[79, 0, 0], [76, 20, 4], [69, 38, 7], [57, 54, 11], [42, 66, 14], [24, 75, 18], [5, 78, 21], [-15, 77, 25], [-33, 71, 29], [-50, 61, 32], [-64, 46, 36], [-73, 29, 39], [-78, 10, 43], [-78, -10, 46], [-73, -29, 50], [-64, -46, 54], [-50, -61, 57], [-33, -71, 61], [-15, -77, 64], [5, -78, 68], [24, -75, 72], [42, -66, 75], [57, -54, 79], [69, -38, 82], [76, -20, 86], [79, 0, 89], [76, 20, 93], [69, 38, 97], [57, 54, 100], [42, 66, 104], [24, 75, 107], [5, 78, 111], [-15, 77, 114], [-33, 71, 118], [-50, 61, 122], [-64, 46, 125], [-73, 29, 129], [-78, 10, 132], [-78, -10, 136], [-73, -29, 139], [-64, -46, 143], [-50, -61, 147], [-33, -71, 150], [-15, -77, 154], [5, -78, 157], [24, -75, 161], [42, -66, 164], [57, -54, 168], [69, -38, 172], [76, -20, 175], [79, 0, 179]], makeWire=1)
wp3 = cq.Workplane('XZ', origin=(0, 0, -89))
wp4 = wp3.moveTo(79, 0)
wp5 = wp4.circle(11)
wp6 = wp5.sweep(wp2)
wp7 = cq.Workplane(cq.Plane(origin=cq.Vector(28, 85, -71), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0)))
wp8 = wp7.circle(5)
wp9 = wp8.extrude(8)
wp10 = wp6.union(wp9)
wp11 = cq.Workplane(cq.Plane(origin=cq.Vector(-72, 53, -53), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(-2, 2, 0)))
wp12 = wp11.circle(5)
wp13 = wp12.extrude(8)
wp14 = wp10.union(wp13)
wp15 = cq.Workplane(cq.Plane(origin=cq.Vector(-72, -53, -36), xDir=cq.Vector(2, -2, 0), normal=cq.Vector(-2, -2, 0)))
wp16 = wp15.circle(5)
wp17 = wp16.extrude(8)
wp18 = wp14.union(wp17)
wp19 = cq.Workplane(cq.Plane(origin=cq.Vector(28, -85, -18), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0)))
wp20 = wp19.circle(5)
wp21 = wp20.extrude(8)
wp22 = wp18.union(wp21)
wp23 = cq.Workplane(cq.Plane(origin=cq.Vector(28, 85, 18), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0)))
wp24 = wp23.circle(5)
wp25 = wp24.extrude(8)
wp26 = wp22.union(wp25)
wp27 = cq.Workplane(cq.Plane(origin=cq.Vector(-72, 53, 36), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(-2, 2, 0)))
wp28 = wp27.circle(5)
wp29 = wp28.extrude(8)
wp30 = wp26.union(wp29)
wp31 = cq.Workplane(cq.Plane(origin=cq.Vector(-72, -53, 54), xDir=cq.Vector(2, -2, 0), normal=cq.Vector(-2, -2, 0)))
wp32 = wp31.circle(5)
wp33 = wp32.extrude(8)
wp34 = wp30.union(wp33)
wp35 = cq.Workplane(cq.Plane(origin=cq.Vector(28, -85, 72), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0)))
wp36 = wp35.circle(5)
wp37 = wp36.extrude(8)
wp38 = wp34.union(wp37)
result = wp38
```
```

**row_id:** `cadqa_coordinate_frame_34066716c9cd26d1` | **hop:** 0 | **gold:** `cq.Plane(origin=cq.Vector(-21, -94, -21), xDir=cq.Vector(-3, 1, 0), normal=cq.Vector(-1, -3, 0))`

```text
Given the CadQuery script below, what coordinate frame or workplane name is established by feature `wp23`? Answer with exactly one listed token.

Choices: XY, YZ, XZ, front, back, left, right, top, bottom, inherited, unknown, cq.Plane(origin=cq.Vector(-21, -94, -21), xDir=cq.Vector(-3, 1, 0), normal=cq.Vector(-1, -3, 0))

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -72))
wp2 = wp1.splineApprox([[88, 0, 0], [77, 42, 6], [47, 74, 12], [6, 88, 17], [-37, 80, 23], [-71, 52, 29], [-87, 11, 35], [-82, -32, 40], [-56, -68, 46], [-16, -86, 52], [27, -84, 58], [64, -60, 63], [85, -22, 69], [85, 22, 75], [64, 60, 81], [27, 84, 86], [-16, 86, 92], [-56, 68, 98], [-82, 32, 104], [-87, -11, 109], [-71, -52, 115], [-37, -80, 121], [6, -88, 127], [47, -74, 133], [77, -42, 138], [88, 0, 144]], makeWire=1)
wp3 = cq.Workplane('XZ', origin=(0, 0, -72))
wp4 = wp3.moveTo(88, 0)
wp5 = wp4.circle(8)
wp6 = wp5.sweep(wp2)
wp7 = cq.Workplane(cq.Plane(origin=cq.Vector(60, 75, -62), xDir=cq.Vector(2, -2, 0), normal=cq.Vector(2, 2, 0)))
wp8 = wp7.circle(5)
wp9 = wp8.extrude(5)
wp10 = wp6.union(wp9)
wp11 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, 94, -51), xDir=cq.Vector(3, 1, 0), normal=cq.Vector(-1, 3, 0)))
wp12 = wp11.circle(5)
wp13 = wp12.extrude(5)
wp14 = wp10.union(wp13)
wp15 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, 42, -41), xDir=cq.Vector(-1, -2, 0), normal=cq.Vector(-2, 1, 0)))
wp16 = wp15.circle(5)
wp17 = wp16.extrude(5)
wp18 = wp14.union(wp17)
wp19 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, -42, -31), xDir=cq.Vector(1, -2, 0), normal=cq.Vector(-2, -1, 0)))
wp20 = wp19.circle(5)
wp21 = wp20.extrude(5)
wp22 = wp18.union(wp21)
wp23 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, -94, -21), xDir=cq.Vector(-3, 1, 0), normal=cq.Vector(-1, -3, 0)))
wp24 = wp23.circle(5)
wp25 = wp24.extrude(5)
wp26 = wp22.union(wp25)
wp27 = cq.Workplane(cq.Plane(origin=cq.Vector(60, -75, -10), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(2, -2, 0)))
wp28 = wp27.circle(5)
wp29 = wp28.extrude(5)
wp30 = wp26.union(wp29)
wp31 = cq.Workplane(cq.Plane(origin=cq.Vector(60, 75, 10), xDir=cq.Vector(2, -2, 0), normal=cq.Vector(2, 2, 0)))
wp32 = wp31.circle(5)
wp33 = wp32.extrude(5)
wp34 = wp30.union(wp33)
wp35 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, 94, 21), xDir=cq.Vector(3, 1, 0), normal=cq.Vector(-1, 3, 0)))
wp36 = wp35.circle(5)
wp37 = wp36.extrude(5)
wp38 = wp34.union(wp37)
wp39 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, 42, 31), xDir=cq.Vector(-1, -2, 0), normal=cq.Vector(-2, 1, 0)))
wp40 = wp39.circle(5)
wp41 = wp40.extrude(5)
wp42 = wp38.union(wp41)
wp43 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, -42, 41), xDir=cq.Vector(1, -2, 0), normal=cq.Vector(-2, -1, 0)))
wp44 = wp43.circle(5)
wp45 = wp44.extrude(5)
wp46 = wp42.union(wp45)
wp47 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, -94, 51), xDir=cq.Vector(-3, 1, 0), normal=cq.Vector(-1, -3, 0)))
wp48 = wp47.circle(5)
wp49 = wp48.extrude(5)
wp50 = wp46.union(wp49)
wp51 = cq.Workplane(cq.Plane(origin=cq.Vector(60, -75, 62), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(2, -2, 0)))
wp52 = wp51.circle(5)
wp53 = wp52.extrude(5)
wp54 = wp50.union(wp53)
result = wp54
```
```

**row_id:** `cadqa_coordinate_frame_9136c3fa41790f62` | **hop:** 0 | **gold:** `cq.Plane(origin=cq.Vector(-87, 42, -41), xDir=cq.Vector(-1, -2, 0), normal=cq.Vector(-2, 1, 0))`

```text
Given the CadQuery script below, what coordinate frame or workplane name is established by feature `wp15`? Answer with exactly one listed token.

Choices: XY, YZ, XZ, front, back, left, right, top, bottom, inherited, unknown, cq.Plane(origin=cq.Vector(-87, 42, -41), xDir=cq.Vector(-1, -2, 0), normal=cq.Vector(-2, 1, 0))

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -72))
wp2 = wp1.splineApprox([[88, 0, 0], [77, 42, 6], [47, 74, 12], [6, 88, 17], [-37, 80, 23], [-71, 52, 29], [-87, 11, 35], [-82, -32, 40], [-56, -68, 46], [-16, -86, 52], [27, -84, 58], [64, -60, 63], [85, -22, 69], [85, 22, 75], [64, 60, 81], [27, 84, 86], [-16, 86, 92], [-56, 68, 98], [-82, 32, 104], [-87, -11, 109], [-71, -52, 115], [-37, -80, 121], [6, -88, 127], [47, -74, 133], [77, -42, 138], [88, 0, 144]], makeWire=1)
wp3 = cq.Workplane('XZ', origin=(0, 0, -72))
wp4 = wp3.moveTo(88, 0)
wp5 = wp4.circle(8)
wp6 = wp5.sweep(wp2)
wp7 = cq.Workplane(cq.Plane(origin=cq.Vector(60, 75, -62), xDir=cq.Vector(2, -2, 0), normal=cq.Vector(2, 2, 0)))
wp8 = wp7.circle(5)
wp9 = wp8.extrude(5)
wp10 = wp6.union(wp9)
wp11 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, 94, -51), xDir=cq.Vector(3, 1, 0), normal=cq.Vector(-1, 3, 0)))
wp12 = wp11.circle(5)
wp13 = wp12.extrude(5)
wp14 = wp10.union(wp13)
wp15 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, 42, -41), xDir=cq.Vector(-1, -2, 0), normal=cq.Vector(-2, 1, 0)))
wp16 = wp15.circle(5)
wp17 = wp16.extrude(5)
wp18 = wp14.union(wp17)
wp19 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, -42, -31), xDir=cq.Vector(1, -2, 0), normal=cq.Vector(-2, -1, 0)))
wp20 = wp19.circle(5)
wp21 = wp20.extrude(5)
wp22 = wp18.union(wp21)
wp23 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, -94, -21), xDir=cq.Vector(-3, 1, 0), normal=cq.Vector(-1, -3, 0)))
wp24 = wp23.circle(5)
wp25 = wp24.extrude(5)
wp26 = wp22.union(wp25)
wp27 = cq.Workplane(cq.Plane(origin=cq.Vector(60, -75, -10), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(2, -2, 0)))
wp28 = wp27.circle(5)
wp29 = wp28.extrude(5)
wp30 = wp26.union(wp29)
wp31 = cq.Workplane(cq.Plane(origin=cq.Vector(60, 75, 10), xDir=cq.Vector(2, -2, 0), normal=cq.Vector(2, 2, 0)))
wp32 = wp31.circle(5)
wp33 = wp32.extrude(5)
wp34 = wp30.union(wp33)
wp35 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, 94, 21), xDir=cq.Vector(3, 1, 0), normal=cq.Vector(-1, 3, 0)))
wp36 = wp35.circle(5)
wp37 = wp36.extrude(5)
wp38 = wp34.union(wp37)
wp39 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, 42, 31), xDir=cq.Vector(-1, -2, 0), normal=cq.Vector(-2, 1, 0)))
wp40 = wp39.circle(5)
wp41 = wp40.extrude(5)
wp42 = wp38.union(wp41)
wp43 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, -42, 41), xDir=cq.Vector(1, -2, 0), normal=cq.Vector(-2, -1, 0)))
wp44 = wp43.circle(5)
wp45 = wp44.extrude(5)
wp46 = wp42.union(wp45)
wp47 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, -94, 51), xDir=cq.Vector(-3, 1, 0), normal=cq.Vector(-1, -3, 0)))
wp48 = wp47.circle(5)
wp49 = wp48.extrude(5)
wp50 = wp46.union(wp49)
wp51 = cq.Workplane(cq.Plane(origin=cq.Vector(60, -75, 62), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(2, -2, 0)))
wp52 = wp51.circle(5)
wp53 = wp52.extrude(5)
wp54 = wp50.union(wp53)
result = wp54
```
```

### other (showing 3 of 6)

**row_id:** `cadqa_coordinate_frame_5ee53d30742db479` | **hop:** 0 | **gold:** `XY`

```text
Given the CadQuery script below, what coordinate frame or workplane name is established by feature `wp1`? Answer with exactly one listed token.

Choices: XY, YZ, XZ, front, back, left, right, top, bottom, inherited, unknown

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -72))
wp2 = wp1.splineApprox([[88, 0, 0], [77, 42, 6], [47, 74, 12], [6, 88, 17], [-37, 80, 23], [-71, 52, 29], [-87, 11, 35], [-82, -32, 40], [-56, -68, 46], [-16, -86, 52], [27, -84, 58], [64, -60, 63], [85, -22, 69], [85, 22, 75], [64, 60, 81], [27, 84, 86], [-16, 86, 92], [-56, 68, 98], [-82, 32, 104], [-87, -11, 109], [-71, -52, 115], [-37, -80, 121], [6, -88, 127], [47, -74, 133], [77, -42, 138], [88, 0, 144]], makeWire=1)
wp3 = cq.Workplane('XZ', origin=(0, 0, -72))
wp4 = wp3.moveTo(88, 0)
wp5 = wp4.circle(8)
wp6 = wp5.sweep(wp2)
wp7 = cq.Workplane(cq.Plane(origin=cq.Vector(60, 75, -62), xDir=cq.Vector(2, -2, 0), normal=cq.Vector(2, 2, 0)))
wp8 = wp7.circle(5)
wp9 = wp8.extrude(5)
wp10 = wp6.union(wp9)
wp11 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, 94, -51), xDir=cq.Vector(3, 1, 0), normal=cq.Vector(-1, 3, 0)))
wp12 = wp11.circle(5)
wp13 = wp12.extrude(5)
wp14 = wp10.union(wp13)
wp15 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, 42, -41), xDir=cq.Vector(-1, -2, 0), normal=cq.Vector(-2, 1, 0)))
wp16 = wp15.circle(5)
wp17 = wp16.extrude(5)
wp18 = wp14.union(wp17)
wp19 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, -42, -31), xDir=cq.Vector(1, -2, 0), normal=cq.Vector(-2, -1, 0)))
wp20 = wp19.circle(5)
wp21 = wp20.extrude(5)
wp22 = wp18.union(wp21)
wp23 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, -94, -21), xDir=cq.Vector(-3, 1, 0), normal=cq.Vector(-1, -3, 0)))
wp24 = wp23.circle(5)
wp25 = wp24.extrude(5)
wp26 = wp22.union(wp25)
wp27 = cq.Workplane(cq.Plane(origin=cq.Vector(60, -75, -10), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(2, -2, 0)))
wp28 = wp27.circle(5)
wp29 = wp28.extrude(5)
wp30 = wp26.union(wp29)
wp31 = cq.Workplane(cq.Plane(origin=cq.Vector(60, 75, 10), xDir=cq.Vector(2, -2, 0), normal=cq.Vector(2, 2, 0)))
wp32 = wp31.circle(5)
wp33 = wp32.extrude(5)
wp34 = wp30.union(wp33)
wp35 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, 94, 21), xDir=cq.Vector(3, 1, 0), normal=cq.Vector(-1, 3, 0)))
wp36 = wp35.circle(5)
wp37 = wp36.extrude(5)
wp38 = wp34.union(wp37)
wp39 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, 42, 31), xDir=cq.Vector(-1, -2, 0), normal=cq.Vector(-2, 1, 0)))
wp40 = wp39.circle(5)
wp41 = wp40.extrude(5)
wp42 = wp38.union(wp41)
wp43 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, -42, 41), xDir=cq.Vector(1, -2, 0), normal=cq.Vector(-2, -1, 0)))
wp44 = wp43.circle(5)
wp45 = wp44.extrude(5)
wp46 = wp42.union(wp45)
wp47 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, -94, 51), xDir=cq.Vector(-3, 1, 0), normal=cq.Vector(-1, -3, 0)))
wp48 = wp47.circle(5)
wp49 = wp48.extrude(5)
wp50 = wp46.union(wp49)
wp51 = cq.Workplane(cq.Plane(origin=cq.Vector(60, -75, 62), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(2, -2, 0)))
wp52 = wp51.circle(5)
wp53 = wp52.extrude(5)
wp54 = wp50.union(wp53)
result = wp54
```
```

**row_id:** `cadqa_coordinate_frame_3fc34533f867475e` | **hop:** 0 | **gold:** `XY`

```text
Given the CadQuery script below, what coordinate frame or workplane name is established by feature `body__chain_00`? Answer with exactly one listed token.

Choices: XY, YZ, XZ, front, back, left, right, top, bottom, inherited, unknown

```python
import cadquery as cq
L=70; W=27; H=24
tW=6; tH=6; tD=3
off = L/4
zc = H/2 - tH/2
body = cq.Workplane("XY").box(L, W, H)
# use functional union
tabs = [ body.faces(f).workplane().center(x, zc).rect(tW, tH).extrude(tD, combine=False).edges("|Z").fillet(0.6)
         for f in ("+Y","-Y") for x in (-off, off) ]
from functools import reduce
result = reduce(lambda a,b: a.union(b), tabs, body)
```
```

**row_id:** `cadqa_point_membership_73d613a36eb7ba7d` | **hop:** 0 | **gold:** `outside`

```text
Given the CadQuery script below, classify point `[146.1622778101684, 0.0, -0.08248006601032642]` as one of inside, outside, on_boundary, or ambiguous at the target state. Answer with exactly one allowed token.

```python
import cadquery as cq
wp1 = cq.Workplane('XY', origin=(0, 0, -72))
wp2 = wp1.splineApprox([[88, 0, 0], [77, 42, 6], [47, 74, 12], [6, 88, 17], [-37, 80, 23], [-71, 52, 29], [-87, 11, 35], [-82, -32, 40], [-56, -68, 46], [-16, -86, 52], [27, -84, 58], [64, -60, 63], [85, -22, 69], [85, 22, 75], [64, 60, 81], [27, 84, 86], [-16, 86, 92], [-56, 68, 98], [-82, 32, 104], [-87, -11, 109], [-71, -52, 115], [-37, -80, 121], [6, -88, 127], [47, -74, 133], [77, -42, 138], [88, 0, 144]], makeWire=1)
wp3 = cq.Workplane('XZ', origin=(0, 0, -72))
wp4 = wp3.moveTo(88, 0)
wp5 = wp4.circle(8)
wp6 = wp5.sweep(wp2)
wp7 = cq.Workplane(cq.Plane(origin=cq.Vector(60, 75, -62), xDir=cq.Vector(2, -2, 0), normal=cq.Vector(2, 2, 0)))
wp8 = wp7.circle(5)
wp9 = wp8.extrude(5)
wp10 = wp6.union(wp9)
wp11 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, 94, -51), xDir=cq.Vector(3, 1, 0), normal=cq.Vector(-1, 3, 0)))
wp12 = wp11.circle(5)
wp13 = wp12.extrude(5)
wp14 = wp10.union(wp13)
wp15 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, 42, -41), xDir=cq.Vector(-1, -2, 0), normal=cq.Vector(-2, 1, 0)))
wp16 = wp15.circle(5)
wp17 = wp16.extrude(5)
wp18 = wp14.union(wp17)
wp19 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, -42, -31), xDir=cq.Vector(1, -2, 0), normal=cq.Vector(-2, -1, 0)))
wp20 = wp19.circle(5)
wp21 = wp20.extrude(5)
wp22 = wp18.union(wp21)
wp23 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, -94, -21), xDir=cq.Vector(-3, 1, 0), normal=cq.Vector(-1, -3, 0)))
wp24 = wp23.circle(5)
wp25 = wp24.extrude(5)
wp26 = wp22.union(wp25)
wp27 = cq.Workplane(cq.Plane(origin=cq.Vector(60, -75, -10), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(2, -2, 0)))
wp28 = wp27.circle(5)
wp29 = wp28.extrude(5)
wp30 = wp26.union(wp29)
wp31 = cq.Workplane(cq.Plane(origin=cq.Vector(60, 75, 10), xDir=cq.Vector(2, -2, 0), normal=cq.Vector(2, 2, 0)))
wp32 = wp31.circle(5)
wp33 = wp32.extrude(5)
wp34 = wp30.union(wp33)
wp35 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, 94, 21), xDir=cq.Vector(3, 1, 0), normal=cq.Vector(-1, 3, 0)))
wp36 = wp35.circle(5)
wp37 = wp36.extrude(5)
wp38 = wp34.union(wp37)
wp39 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, 42, 31), xDir=cq.Vector(-1, -2, 0), normal=cq.Vector(-2, 1, 0)))
wp40 = wp39.circle(5)
wp41 = wp40.extrude(5)
wp42 = wp38.union(wp41)
wp43 = cq.Workplane(cq.Plane(origin=cq.Vector(-87, -42, 41), xDir=cq.Vector(1, -2, 0), normal=cq.Vector(-2, -1, 0)))
wp44 = wp43.circle(5)
wp45 = wp44.extrude(5)
wp46 = wp42.union(wp45)
wp47 = cq.Workplane(cq.Plane(origin=cq.Vector(-21, -94, 51), xDir=cq.Vector(-3, 1, 0), normal=cq.Vector(-1, -3, 0)))
wp48 = wp47.circle(5)
wp49 = wp48.extrude(5)
wp50 = wp46.union(wp49)
wp51 = cq.Workplane(cq.Plane(origin=cq.Vector(60, -75, 62), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(2, -2, 0)))
wp52 = wp51.circle(5)
wp53 = wp52.extrude(5)
wp54 = wp50.union(wp53)
result = wp54
```
```

## 5. Small shapes — ALL rows (compact)

### wp_center — 22 rows

- `row:graph:graph:src_3dac547343362b42:q1:argmax_origin_z_workplane` | hop 1 | gold `wp16_center` | family `argmax_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the greatest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_3dac547343362b42:q1:argmin_origin_z_workplane` | hop 1 | gold `wp26_center` | family `argmin_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the smallest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_7f805e6088e4c466:q1:argmax_origin_z_workplane` | hop 1 | gold `wp27_center` | family `argmax_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the greatest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_7f805e6088e4c466:q1:argmin_origin_z_workplane` | hop 1 | gold `wp42_center` | family `argmin_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the smallest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_3cbce23163879930:q1:argmax_origin_z_workplane` | hop 1 | gold `wp26_center` | family `argmax_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the greatest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_3cbce23163879930:q1:argmin_origin_z_workplane` | hop 1 | gold `wp16_center` | family `argmin_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the smallest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_72deb204448950c5:q1:argmax_origin_z_workplane` | hop 1 | gold `wp26_center` | family `argmax_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the greatest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_72deb204448950c5:q1:argmin_origin_z_workplane` | hop 1 | gold `wp16_center` | family `argmin_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the smallest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_2c491af066c68df8:q1:argmax_origin_z_workplane` | hop 1 | gold `wp26_center` | family `argmax_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the greatest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_2c491af066c68df8:q1:argmin_origin_z_workplane` | hop 1 | gold `wp16_center` | family `argmin_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the smallest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_33806dac2401d929:q1:argmax_origin_z_workplane` | hop 1 | gold `wp26_center` | family `argmax_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the greatest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_33806dac2401d929:q1:argmin_origin_z_workplane` | hop 1 | gold `wp16_center` | family `argmin_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the smallest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_2c2f5faf819cc714:q1:argmax_origin_z_workplane` | hop 1 | gold `wp26_center` | family `argmax_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the greatest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_2c2f5faf819cc714:q1:argmin_origin_z_workplane` | hop 1 | gold `wp16_center` | family `argmin_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the smallest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_6e78359d2d52f77f:q1:argmax_origin_z_workplane` | hop 1 | gold `wp26_center` | family `argmax_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the greatest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_6e78359d2d52f77f:q1:argmin_origin_z_workplane` | hop 1 | gold `wp16_center` | family `argmin_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the smallest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_36629229b5ba4373:q1:argmax_origin_z_workplane` | hop 1 | gold `wp26_center` | family `argmax_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the greatest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_36629229b5ba4373:q1:argmin_origin_z_workplane` | hop 1 | gold `wp16_center` | family `argmin_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the smallest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_a5c68d8a5dbb5254:q1:argmax_origin_z_workplane` | hop 1 | gold `wp26_center` | family `argmax_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the greatest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_a5c68d8a5dbb5254:q1:argmin_origin_z_workplane` | hop 1 | gold `wp16_center` | family `argmin_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the smallest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_0e9e2eded60c5714:q1:argmax_origin_z_workplane` | hop 1 | gold `wp14_center` | family `argmax_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the greatest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp
- `row:graph:graph:src_0e9e2eded60c5714:q1:argmin_origin_z_workplane` | hop 1 | gold `wp34_center` | family `argmin_origin_z_workplane`
  - question: Identify the target workplane that satisfies all of these constraints: ⏎ - Among the remaining candidates, choose the one with the smallest workplane origin height. ⏎  ⏎ Return exactly one source variable name, for examp

### plane — 11 rows

- `cadqa_coordinate_frame_255f68d7d652d955` | hop 0 | gold `cq.Plane(origin=cq.Vector(-72, 53, 36), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(-2, 2, 0))` | family `cadqa_coordinate_frame_255f68d7d652d955`
  - question: 35 = cq.Workplane(cq.Plane(origin=cq.Vector(28, -85, 72), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0))) ⏎ wp36 = wp35.circle(5) ⏎ wp37 = wp36.extrude(8) ⏎ wp38 = wp34.union(wp37) ⏎ result = wp38 ⏎ ```
- `cadqa_coordinate_frame_34066716c9cd26d1` | hop 0 | gold `cq.Plane(origin=cq.Vector(-21, -94, -21), xDir=cq.Vector(-3, 1, 0), normal=cq.Vector(-1, -3, 0))` | family `cadqa_coordinate_frame_34066716c9cd26d1`
  - question: 51 = cq.Workplane(cq.Plane(origin=cq.Vector(60, -75, 62), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(2, -2, 0))) ⏎ wp52 = wp51.circle(5) ⏎ wp53 = wp52.extrude(5) ⏎ wp54 = wp50.union(wp53) ⏎ result = wp54 ⏎ ```
- `cadqa_coordinate_frame_9136c3fa41790f62` | hop 0 | gold `cq.Plane(origin=cq.Vector(-87, 42, -41), xDir=cq.Vector(-1, -2, 0), normal=cq.Vector(-2, 1, 0))` | family `cadqa_coordinate_frame_9136c3fa41790f62`
  - question: 51 = cq.Workplane(cq.Plane(origin=cq.Vector(60, -75, 62), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(2, -2, 0))) ⏎ wp52 = wp51.circle(5) ⏎ wp53 = wp52.extrude(5) ⏎ wp54 = wp50.union(wp53) ⏎ result = wp54 ⏎ ```
- `cadqa_coordinate_frame_84dbfb4a2e3c199a` | hop 0 | gold `cq.Plane(origin=cq.Vector(-21, 94, 21), xDir=cq.Vector(3, 1, 0), normal=cq.Vector(-1, 3, 0))` | family `cadqa_coordinate_frame_84dbfb4a2e3c199a`
  - question: 51 = cq.Workplane(cq.Plane(origin=cq.Vector(60, -75, 62), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(2, -2, 0))) ⏎ wp52 = wp51.circle(5) ⏎ wp53 = wp52.extrude(5) ⏎ wp54 = wp50.union(wp53) ⏎ result = wp54 ⏎ ```
- `cadqa_coordinate_frame_58520e8997a498d8` | hop 0 | gold `cq.Plane(origin=cq.Vector(28, -85, 72), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0))` | family `cadqa_coordinate_frame_58520e8997a498d8`
  - question: 35 = cq.Workplane(cq.Plane(origin=cq.Vector(28, -85, 72), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0))) ⏎ wp36 = wp35.circle(5) ⏎ wp37 = wp36.extrude(8) ⏎ wp38 = wp34.union(wp37) ⏎ result = wp38 ⏎ ```
- `cadqa_coordinate_frame_ded7f8b14a4214ce` | hop 0 | gold `cq.Plane(origin=cq.Vector(-72, 53, -53), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(-2, 2, 0))` | family `cadqa_coordinate_frame_ded7f8b14a4214ce`
  - question: 35 = cq.Workplane(cq.Plane(origin=cq.Vector(28, -85, 72), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0))) ⏎ wp36 = wp35.circle(5) ⏎ wp37 = wp36.extrude(8) ⏎ wp38 = wp34.union(wp37) ⏎ result = wp38 ⏎ ```
- `cadqa_coordinate_frame_6b8031b00f5caafb` | hop 0 | gold `cq.Plane(origin=cq.Vector(28, -85, -18), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0))` | family `cadqa_coordinate_frame_6b8031b00f5caafb`
  - question: 35 = cq.Workplane(cq.Plane(origin=cq.Vector(28, -85, 72), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0))) ⏎ wp36 = wp35.circle(5) ⏎ wp37 = wp36.extrude(8) ⏎ wp38 = wp34.union(wp37) ⏎ result = wp38 ⏎ ```
- `cadqa_coordinate_frame_771ddff402c042f4` | hop 0 | gold `cq.Plane(origin=cq.Vector(28, 85, -71), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))` | family `cadqa_coordinate_frame_771ddff402c042f4`
  - question: 35 = cq.Workplane(cq.Plane(origin=cq.Vector(28, -85, 72), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0))) ⏎ wp36 = wp35.circle(5) ⏎ wp37 = wp36.extrude(8) ⏎ wp38 = wp34.union(wp37) ⏎ result = wp38 ⏎ ```
- `cadqa_coordinate_frame_16755945735e8dfd` | hop 0 | gold `cq.Plane(origin=cq.Vector(-87, -42, -31), xDir=cq.Vector(1, -2, 0), normal=cq.Vector(-2, -1, 0))` | family `cadqa_coordinate_frame_16755945735e8dfd`
  - question: 51 = cq.Workplane(cq.Plane(origin=cq.Vector(60, -75, 62), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(2, -2, 0))) ⏎ wp52 = wp51.circle(5) ⏎ wp53 = wp52.extrude(5) ⏎ wp54 = wp50.union(wp53) ⏎ result = wp54 ⏎ ```
- `cadqa_coordinate_frame_34be2d2cb6dbfd6b` | hop 0 | gold `cq.Plane(origin=cq.Vector(28, 85, -71), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))` | family `cadqa_coordinate_frame_34be2d2cb6dbfd6b`
  - question: 35 = cq.Workplane(cq.Plane(origin=cq.Vector(28, -85, 72), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0))) ⏎ wp36 = wp35.circle(5) ⏎ wp37 = wp36.extrude(8) ⏎ wp38 = wp34.union(wp37) ⏎ result = wp38 ⏎ ```
- `cadqa_coordinate_frame_6fc5fec0e50f913d` | hop 0 | gold `cq.Plane(origin=cq.Vector(28, 85, 18), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))` | family `cadqa_coordinate_frame_6fc5fec0e50f913d`
  - question: 35 = cq.Workplane(cq.Plane(origin=cq.Vector(28, -85, 72), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0))) ⏎ wp36 = wp35.circle(5) ⏎ wp37 = wp36.extrude(8) ⏎ wp38 = wp34.union(wp37) ⏎ result = wp38 ⏎ ```

### other — 6 rows

- `cadqa_coordinate_frame_5ee53d30742db479` | hop 0 | gold `XY` | family `cadqa_coordinate_frame_5ee53d30742db479`
  - question: 51 = cq.Workplane(cq.Plane(origin=cq.Vector(60, -75, 62), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(2, -2, 0))) ⏎ wp52 = wp51.circle(5) ⏎ wp53 = wp52.extrude(5) ⏎ wp54 = wp50.union(wp53) ⏎ result = wp54 ⏎ ```
- `cadqa_coordinate_frame_3fc34533f867475e` | hop 0 | gold `XY` | family `cadqa_coordinate_frame_3fc34533f867475e`
  - question: ect(tW, tH).extrude(tD, combine=False).edges("|Z").fillet(0.6) ⏎          for f in ("+Y","-Y") for x in (-off, off) ] ⏎ from functools import reduce ⏎ result = reduce(lambda a,b: a.union(b), tabs, body) ⏎ ```
- `cadqa_point_membership_73d613a36eb7ba7d` | hop 0 | gold `outside` | family `cadqa_point_membership_73d613a36eb7ba7d`
  - question: 51 = cq.Workplane(cq.Plane(origin=cq.Vector(60, -75, 62), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(2, -2, 0))) ⏎ wp52 = wp51.circle(5) ⏎ wp53 = wp52.extrude(5) ⏎ wp54 = wp50.union(wp53) ⏎ result = wp54 ⏎ ```
- `cadqa_point_membership_f739492a566df045` | hop 0 | gold `outside` | family `cadqa_point_membership_f739492a566df045`
  - question: 51 = cq.Workplane(cq.Plane(origin=cq.Vector(60, -75, 62), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(2, -2, 0))) ⏎ wp52 = wp51.circle(5) ⏎ wp53 = wp52.extrude(5) ⏎ wp54 = wp50.union(wp53) ⏎ result = wp54 ⏎ ```
- `cadqa_point_membership_45983b175c10d33a` | hop 0 | gold `outside` | family `cadqa_point_membership_45983b175c10d33a`
  - question: 35 = cq.Workplane(cq.Plane(origin=cq.Vector(28, -85, 72), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0))) ⏎ wp36 = wp35.circle(5) ⏎ wp37 = wp36.extrude(8) ⏎ wp38 = wp34.union(wp37) ⏎ result = wp38 ⏎ ```
- `cadqa_coordinate_frame_fa0f30cb24e9b0b7` | hop 0 | gold `XZ` | family `cadqa_coordinate_frame_fa0f30cb24e9b0b7`
  - question: 35 = cq.Workplane(cq.Plane(origin=cq.Vector(28, -85, 72), xDir=cq.Vector(-3, -1, 0), normal=cq.Vector(1, -3, 0))) ⏎ wp36 = wp35.circle(5) ⏎ wp37 = wp36.extrude(8) ⏎ wp38 = wp34.union(wp37) ⏎ result = wp38 ⏎ ```

## 6. SFT traces (`submit_text`, 158 of 275) — ACTUAL submissions

Trace gold shapes: {'wp': 98, 'other': 6, 'quoted_wp': 47, 'plane': 7}

### 6a. Compact listing — row_id | shape | gold | ACTUAL final submission (last JSON in trace)

- `row:graph:graph:src_761577fa6538e2ed:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:src_f8d598a7cae260b8:synth:v2:parameterized_feature_rank` | wp | gold `wp11` | sub `{"text":"wp11"}`
- `row:graph:src_f8d598a7cae260b8:synth:v2:parameterized_feature_rank` | wp | gold `wp11` | sub `{"text":"wp11"}`
- `row:graph:graph:src_761577fa6538e2ed:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:graph:src_5a76c86945d5f757:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `cadqa_point_membership_73d613a36eb7ba7d` | other | gold `outside` | sub `{"text":"outside"}`
- `row:graph:graph:src_445c19cac5db338d:q1:argmin_origin_z_workplane` | wp | gold `wp11` | sub `{"text":"wp11"}`
- `row:graph:graph:src_c39a861dbf652d38:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:src_cac1d4a39cbe829e:synth:v1:parameterized_feature_rank` | wp | gold `wp5` | sub `{"text":"wp5"}`
- `row:graph:graph:src_7fe7c16131f2b4ef:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:src_e0877e953bfb1632:synth:v0:parameterized_void_region_rank` | quoted_wp | gold `"wp40"` | sub `{"text":"wp40"}`
- `row:graph:src_a9645b50d0f33d97:synth:v0:parameterized_feature_extreme` | wp | gold `wp5` | sub `{"text":"wp5"}`
- `row:graph:graph:src_b966c1e81b88b84b:q1:argmax_origin_z_workplane` | wp | gold `wp9` | sub `{"text":"wp9"}`
- `row:graph:graph:src_52502a9d163c189b:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:src_4f329454f966c395:synth:v4:parameterized_feature_extreme` | wp | gold `wp9` | sub `{"text":"wp9"}`
- `row:graph:src_ba0cbaa3a36f33a8:synth:v2:parameterized_material_region_extreme` | quoted_wp | gold `"wp14"` | sub `{"text":"wp14"}`
- `row:graph:graph:src_c652e441e8a12433:q1:argmax_origin_z_workplane` | wp | gold `wp8` | sub `{"text":"wp8"}`
- `row:graph:src_965d6cf1e63f032e:synth:parameterized_feature_effect_delta_extrem` | quoted_wp | gold `"wp88"` | sub `{"text":"wp88"}`
- `row:graph:src_5f1bce09365d2f9c:synth:v1:parameterized_feature_extreme` | wp | gold `wp12` | sub `{"text":"wp12"}`
- `row:graph:graph:src_09b8d8412ad88a86:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:src_d42a84549ea74920:synth:v2:parameterized_feature_rank` | wp | gold `wp6` | sub `{"text":"wp6"}`
- `row:graph:src_5372470d0d60b21b:synth:v4:parameterized_equal_feature_metric_ext` | quoted_wp | gold `"wp34"` | sub `{"text":"wp34"}`
- `row:graph:src_5f1bce09365d2f9c:synth:v3:parameterized_feature_extreme` | wp | gold `wp12` | sub `{"text":"wp12"}`
- `row:graph:src_312095f6cdb5b792:synth:v1:parameterized_feature_extreme` | quoted_wp | gold `"wp40"` | sub `{"text":"wp40"}`
- `row:graph:graph:src_ca2337b1a3e41549:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `cadqa_coordinate_frame_34be2d2cb6dbfd6b` | plane | gold `cq.Plane(origin=cq.Vector(28, 85, -71), xDir=cq.Vector(3, -1` | sub `{"text":"cq.Plane(origin=cq.Vector(28, 85, -71), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))"}`
- `row:graph:graph:src_36312c330886e941:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:graph:src_bc0b45221d8f26d5:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:src_076afe82034b0268:synth:v3:parameterized_feature_extreme` | wp | gold `wp16` | sub `{"text":"wp16"}`
- `row:graph:src_30f43e17f3f6a93c:synth:v0:parameterized_void_region_extreme` | quoted_wp | gold `"wp7"` | sub `{"text":"wp7"}`
- `cadqa_point_membership_73d613a36eb7ba7d` | other | gold `outside` | sub `{"text":"outside"}`
- `row:graph:src_cac1d4a39cbe829e:synth:v1:parameterized_feature_rank` | wp | gold `wp5` | sub `{"text":"wp5"}`
- `row:graph:src_a9645b50d0f33d97:synth:v0:parameterized_feature_extreme` | wp | gold `wp5` | sub `{"text":"wp5"}`
- `row:graph:graph:src_445c19cac5db338d:q1:argmin_origin_z_workplane` | wp | gold `wp11` | sub `{"text":"wp11"}`
- `row:graph:graph:src_7fe7c16131f2b4ef:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:graph:src_b966c1e81b88b84b:q1:argmax_origin_z_workplane` | wp | gold `wp9` | sub `{"text":"wp9"}`
- `row:graph:graph:src_c39a861dbf652d38:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:src_fc647ebe204a8cae:synth:v1:parameterized_feature_effect_delta_ext` | quoted_wp | gold `"wp6"` | sub `{"text":"wp6"}`
- `row:graph:src_d42a84549ea74920:synth:v5:parameterized_feature_rank` | wp | gold `wp6` | sub `{"text":"wp6"}`
- `row:graph:graph:src_761577fa6538e2ed:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:src_ba0cbaa3a36f33a8:synth:v2:parameterized_material_region_extreme` | quoted_wp | gold `"wp14"` | sub `{"text":"wp14"}`
- `row:graph:src_4f329454f966c395:synth:v4:parameterized_feature_extreme` | wp | gold `wp9` | sub `{"text":"wp9"}`
- `row:graph:graph:src_52502a9d163c189b:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:graph:src_c652e441e8a12433:q1:argmax_origin_z_workplane` | wp | gold `wp8` | sub `{"text":"wp8"}`
- `row:graph:src_965d6cf1e63f032e:synth:parameterized_feature_effect_delta_extrem` | quoted_wp | gold `"wp88"` | sub `{"text":"wp88"}`
- `row:graph:src_f8d598a7cae260b8:synth:v2:parameterized_feature_rank` | wp | gold `wp11` | sub `{"text":"wp11"}`
- `row:graph:src_5f1bce09365d2f9c:synth:v1:parameterized_feature_extreme` | wp | gold `wp12` | sub `{"text":"wp12"}`
- `row:graph:src_5372470d0d60b21b:synth:v4:parameterized_equal_feature_metric_ext` | quoted_wp | gold `"wp34"` | sub `{"text":"wp34"}`
- `row:graph:graph:src_5a76c86945d5f757:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:graph:src_09b8d8412ad88a86:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:graph:src_ca2337b1a3e41549:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `cadqa_coordinate_frame_34be2d2cb6dbfd6b` | plane | gold `cq.Plane(origin=cq.Vector(28, 85, -71), xDir=cq.Vector(3, -1` | sub `{"text":"cq.Plane(origin=cq.Vector(28, 85, -71), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))"}`
- `row:graph:graph:src_36312c330886e941:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:graph:src_bc0b45221d8f26d5:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:src_30f43e17f3f6a93c:synth:v0:parameterized_void_region_extreme` | quoted_wp | gold `"wp7"` | sub `{"text":"wp7"}`
- `row:graph:src_312095f6cdb5b792:synth:v1:parameterized_feature_extreme` | quoted_wp | gold `"wp40"` | sub `{"text":"wp40"}`
- `row:graph:src_d42a84549ea74920:synth:v2:parameterized_feature_rank` | wp | gold `wp6` | sub `{"text":"wp6"}`
- `row:graph:graph:src_fb4914e26978c152:q1:argmax_origin_z_workplane` | wp | gold `wp58` | sub `{"text":"wp58"}`
- `row:graph:graph:src_01c11226b429ee19:q1:argmin_origin_z_workplane` | wp | gold `wp8` | sub `{"text":"wp8"}`
- `row:graph:graph:src_c506fa5d2a4c300e:q1:argmax_origin_z_workplane` | wp | gold `wp15` | sub `{"text":"wp15"}`
- `row:graph:src_199f9fbf5deeeccc:synth:v3:parameterized_feature_extreme` | quoted_wp | gold `"wp8"` | sub `{"text":"wp8"}`
- `row:graph:src_fff34c4e0845c7d5:synth:v2:parameterized_feature_rank` | wp | gold `wp6` | sub `{"text":"wp6"}`
- `row:graph:src_bf8ed1ccf42d99c3:synth:v4:parameterized_feature_rank` | quoted_wp | gold `"wp8"` | sub `{"text":"wp8"}`
- `row:graph:graph:src_2093036ba9d6ad16:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:graph:src_45e918a473b0b968:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:src_8cafa9c69b341ef5:synth:v0:parameterized_feature_rank` | quoted_wp | gold `"wp2"` | sub `{"text":"wp2"}`
- `row:graph:graph:src_ef76c3ead2acd74c:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:src_f4b77085698cf5e9:synth:v2:parameterized_feature_rank` | quoted_wp | gold `"wp3"` | sub `{"text":"wp3"}`
- `row:graph:src_076afe82034b0268:synth:v3:parameterized_feature_extreme` | wp | gold `wp16` | sub `{"text":"wp16"}`
- `row:graph:src_2567a3d79e3e7bb7:synth:v3:parameterized_feature_extreme` | wp | gold `wp9` | sub `{"text":"wp9"}`
- `row:graph:src_5721f17b41ba3d02:synth:v6:parameterized_feature_rank` | wp | gold `wp11` | sub `{"text":"wp11"}`
- `row:graph:graph:src_1a40408933c7e404:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:src_97f0da8117bea982:synth:v4:parameterized_feature_rank` | wp | gold `wp6` | sub `{"text":"wp6"}`
- `row:graph:graph:src_71d0b11eb1003c71:q1:argmax_origin_z_workplane` | wp | gold `wp11` | sub `{"text":"wp11"}`
- `row:graph:src_1fd9001060cfafdc:synth:v1:parameterized_feature_extreme` | wp | gold `wp18` | sub `{"text":"wp18"}`
- `row:graph:src_0bb71a18d5caede7:synth:v2:parameterized_feature_extreme` | quoted_wp | gold `"wp9"` | sub `{"text":"wp9"}`
- `cadqa_coordinate_frame_fa0f30cb24e9b0b7` | other | gold `XZ` | sub `{"text":"XZ"}`
- `row:graph:graph:src_6599baa5190ac687:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:graph:src_ffce9e501f2990b6:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:src_5177f88909d9bc07:synth:v4:parameterized_feature_rank` | quoted_wp | gold `"wp24"` | sub `{"text":"wp24"}`
- `cadqa_point_membership_45983b175c10d33a` | other | gold `outside` | sub `{"text":"outside"}`
- `row:graph:src_10a0d99433f681dd:synth:v6:parameterized_feature_extreme` | wp | gold `wp13` | sub `{"text":"wp13"}`
- `row:graph:graph:src_96244e33e98986c9:q1:argmax_origin_z_workplane` | wp | gold `wp15` | sub `{"text":"wp15"}`
- `row:graph:graph:src_8c991c83d6889e31:q1:argmax_origin_z_workplane` | wp | gold `wp9` | sub `{"text":"wp9"}`
- `row:graph:src_5f1bce09365d2f9c:synth:v5:parameterized_feature_extreme` | wp | gold `wp4` | sub `{"text":"wp4"}`
- `row:graph:graph:src_792574c1eb0a85ac:q1:argmin_origin_z_workplane` | wp | gold `wp37` | sub `{"text":"wp37"}`
- `row:graph:graph:src_5d0aef385602f7b8:q1:argmin_origin_z_workplane` | wp | gold `wp7` | sub `{"text":"wp7"}`
- `row:graph:graph:src_498a150dd91703c8:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:src_45411243056a83aa:synth:v4:parameterized_feature_extreme` | quoted_wp | gold `"wp9"` | sub `{"text":"wp9"}`
- `row:graph:src_912f1e9bba23e9c2:synth:v3:parameterized_material_region_rank` | quoted_wp | gold `"wp27"` | sub `{"text":"wp27"}`
- `row:graph:graph:src_2fcfebe03ee4bafe:q1:argmax_origin_z_workplane` | wp | gold `wp15` | sub `{"text":"wp15"}`
- `row:graph:src_a9645b50d0f33d97:synth:v5:parameterized_feature_rank` | wp | gold `wp10` | sub `{"text":"wp10"}`
- `row:graph:src_49b4e19335c94de4:synth:v4:parameterized_equal_feature_metric_ext` | quoted_wp | gold `"wp4"` | sub `{"text":"wp4"}`
- `row:graph:src_fff34c4e0845c7d5:synth:v5:parameterized_feature_extreme` | wp | gold `wp6` | sub `{"text":"wp6"}`
- `row:graph:src_f8d598a7cae260b8:synth:v0:parameterized_feature_extreme` | wp | gold `wp11` | sub `{"text":"wp11"}`
- `row:graph:graph:src_11ba889dc68f5860:q1:argmin_origin_z_workplane` | wp | gold `wp18` | sub `{"text":"wp18"}`
- `row:graph:src_448c4ee6d20dbd71:synth:v0:parameterized_feature_extreme` | wp | gold `wp5` | sub `{"text":"wp5"}`
- `row:graph:src_10a0d99433f681dd:synth:v2:parameterized_feature_rank` | wp | gold `wp5` | sub `{"text":"wp5"}`
- `row:graph:graph:src_4cfb753ecf36ca8d:q1:argmax_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:src_d593f529e4ece0ed:synth:v1:parameterized_equal_feature_metric_ext` | quoted_wp | gold `"wp13"` | sub `{"text":"wp13"}`
- `row:graph:src_1fd9001060cfafdc:synth:v6:parameterized_feature_extreme` | wp | gold `wp18` | sub `{"text":"wp18"}`
- `row:graph:src_a9645b50d0f33d97:synth:v1:parameterized_feature_extreme` | wp | gold `wp10` | sub `{"text":"wp10"}`
- `cadqa_coordinate_frame_3fc34533f867475e` | other | gold `XY` | sub `{"text":"XY"}`
- `row:graph:graph:src_63920ba56647ad9b:q1:argmax_origin_z_workplane` | wp | gold `wp7` | sub `{"text":"wp7"}`
- `cadqa_coordinate_frame_255f68d7d652d955` | plane | gold `cq.Plane(origin=cq.Vector(-72, 53, 36), xDir=cq.Vector(-2, -` | sub `{"text":"cq.Plane(origin=cq.Vector(-72, 53, 36), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(-2, 2, 0))"}`
- `row:graph:graph:src_5c4c502dda30f91e:q1:argmax_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:src_ae75bdf1f46f2e97:synth:v2:parameterized_equal_feature_metric_ext` | quoted_wp | gold `"wp7"` | sub `{"text":"wp7"}`
- `row:graph:graph:src_c96f1465b0b434d5:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:graph:src_2c7ab7e12c203437:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:graph:src_b282ae8b3a703a7c:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:graph:src_6d32ccf39ec26016:q1:argmax_origin_z_workplane` | wp | gold `wp8` | sub `{"text":"wp8"}`
- `row:graph:src_e75edeac3a3125f2:synth:v2:parameterized_feature_rank` | wp | gold `wp5` | sub `{"text":"wp5"}`
- `row:graph:src_9395d21214e13847:synth:v0:parameterized_feature_extreme` | wp | gold `wp8` | sub `{"text":"wp8"}`
- `row:graph:src_fff34c4e0845c7d5:synth:v5:parameterized_feature_rank` | wp | gold `wp6` | sub `{"text":"wp6"}`
- `cadqa_coordinate_frame_84dbfb4a2e3c199a` | plane | gold `cq.Plane(origin=cq.Vector(-21, 94, 21), xDir=cq.Vector(3, 1,` | sub `{"text":"cq.Plane(origin=cq.Vector(-21, 94, 21), xDir=cq.Vector(3, 1, 0), normal=cq.Vector(-1, 3, 0))"}`
- `row:graph:src_cac1d4a39cbe829e:synth:v0:parameterized_feature_extreme` | wp | gold `wp10` | sub `{"text":"wp10"}`
- `row:graph:src_ec27c2c6c3c4874c:synth:v1:parameterized_feature_extreme` | wp | gold `wp16` | sub `{"text":"wp16"}`
- `row:graph:graph:src_657f2343a89a88b6:q1:argmin_origin_z_workplane` | wp | gold `wp1` | sub `{"text":"wp1"}`
- `row:graph:src_fff34c4e0845c7d5:synth:v6:parameterized_feature_rank` | wp | gold `wp6` | sub `{"text":"wp6"}`
- `row:graph:src_e9b6195afa5f9fd8:synth:v3:parameterized_feature_rank` | quoted_wp | gold `"wp2"` | sub `{"text":"wp2"}`
- `cadqa_coordinate_frame_6fc5fec0e50f913d` | plane | gold `cq.Plane(origin=cq.Vector(28, 85, 18), xDir=cq.Vector(3, -1,` | sub `{"text":"cq.Plane(origin=cq.Vector(28, 85, 18), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))"}`
- `row:graph:src_f8d598a7cae260b8:synth:v4:parameterized_feature_rank` | wp | gold `wp17` | sub `{"text":"wp17"}`
- `row:graph:src_f26a873793182b86:synth:v0:parameterized_feature_rank` | wp | gold `wp7` | sub `{"text":"wp7"}`
- `row:graph:src_e70d18a16c5d74c9:synth:v0:parameterized_material_region_extreme` | quoted_wp | gold `"wp32"` | sub `{"text":"wp32"}`
- `row:graph:src_ec27c2c6c3c4874c:synth:v0:parameterized_feature_rank` | wp | gold `wp11` | sub `{"text":"wp11"}`
- `row:graph:src_418323d094b238ea:synth:v0:parameterized_equal_feature_metric_ext` | quoted_wp | gold `"wp4"` | sub `{"text":"wp4"}`
- `row:graph:src_962a96132d3c97fb:synth:v2:parameterized_feature_extreme` | wp | gold `wp2` | sub `{"text":"wp2"}`
- `row:graph:src_f4b704cae821ea18:synth:v2:parameterized_equal_feature_metric_ran` | quoted_wp | gold `"wp16"` | sub `{"text":"wp16"}`
- `row:graph:src_d42a84549ea74920:synth:v3:parameterized_feature_rank` | wp | gold `wp6` | sub `{"text":"wp6"}`
- `row:graph:src_a9645b50d0f33d97:synth:v3:parameterized_feature_rank` | wp | gold `wp5` | sub `{"text":"wp5"}`
- `row:graph:src_41f38f1f99b53bf2:synth:v2:parameterized_feature_effect_delta_ext` | quoted_wp | gold `"wp27"` | sub `{"text":"wp27"}`
- `row:graph:src_d42a84549ea74920:synth:v6:parameterized_feature_rank` | wp | gold `wp6` | sub `{"text":"wp6"}`
- `row:graph:src_28bbaee6a238a3dd:synth:v1:parameterized_feature_extreme` | wp | gold `wp6` | sub `{"text":"wp6"}`
- `row:graph:src_cdb3d79dad35eb0e:synth:v3:parameterized_equal_feature_metric_ext` | quoted_wp | gold `"wp3"` | sub `{"text":"wp3"}`
- `cadqa_coordinate_frame_771ddff402c042f4` | plane | gold `cq.Plane(origin=cq.Vector(28, 85, -71), xDir=cq.Vector(3, -1` | sub `{"text":"cq.Plane(origin=cq.Vector(28, 85, -71), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))"}`
- `row:graph:src_448c4ee6d20dbd71:synth:v2:parameterized_feature_rank` | wp | gold `wp11` | sub `{"text":"wp11"}`
- `row:graph:src_448c4ee6d20dbd71:synth:v2:parameterized_feature_extreme` | wp | gold `wp5` | sub `{"text":"wp5"}`
- `row:graph:src_60104e08ce206114:synth:v3:parameterized_void_region_extreme` | quoted_wp | gold `"wp11"` | sub `{"text":"wp11"}`
- `row:graph:src_1fd9001060cfafdc:synth:v6:parameterized_feature_rank` | wp | gold `wp18` | sub `{"text":"wp18"}`
- `row:graph:src_5a4cb92eccd9464d:synth:v0:parameterized_equal_feature_metric_ext` | quoted_wp | gold `"wp15"` | sub `{"text":"wp15"}`
- `cadqa_coordinate_frame_34066716c9cd26d1` | plane | gold `cq.Plane(origin=cq.Vector(-21, -94, -21), xDir=cq.Vector(-3,` | sub `{"text":"cq.Plane(origin=cq.Vector(-21, -94, -21), xDir=cq.Vector(-3, 1, 0), normal=cq.Vector(-1, -3, 0))"}`
- `cadqa_coordinate_frame_5ee53d30742db479` | other | gold `XY` | sub `{"text":"XY"}`
- `row:graph:src_2f7164378ebc1070:synth:v4:parameterized_equal_feature_metric_ext` | quoted_wp | gold `"wp7"` | sub `{"text":"wp7"}`
- `row:graph:src_45d78af91b095c0b:synth:v3:parameterized_feature_effect_delta_ext` | quoted_wp | gold `"wp24"` | sub `{"text":"wp24"}`
- `row:graph:src_a8e86677b1229be6:synth:v4:parameterized_material_region_extreme` | quoted_wp | gold `"wp6"` | sub `{"text":"wp6"}`
- `row:graph:src_d96435feec0d1857:synth:v2:parameterized_equal_feature_metric_ran` | quoted_wp | gold `"wp4"` | sub `{"text":"wp4"}`
- `row:graph:src_a7cbffac392f370d:synth:v4:parameterized_equal_feature_metric_ran` | quoted_wp | gold `"wp20"` | sub `{"text":"wp20"}`
- `row:graph:src_66f7d69e9876eb33:synth:v4:parameterized_feature_rank` | quoted_wp | gold `"wp40"` | sub `{"text":"wp40"}`
- `row:graph:src_93c5c43d89c9c119:synth:v4:parameterized_equal_feature_metric_ext` | quoted_wp | gold `"wp13"` | sub `{"text":"wp13"}`
- `row:graph:src_7358a92e08fb679a:synth:v0:parameterized_equal_feature_metric_ran` | quoted_wp | gold `"wp7"` | sub `{"text":"wp7"}`
- `row:graph:src_a9645b50d0f33d97:synth:v1:parameterized_material_region_rank` | quoted_wp | gold `"wp5"` | sub `{"text":"wp5"}`
- `row:graph:src_ac7a3c4224a74dc8:synth:v0:parameterized_equal_feature_metric_ext` | quoted_wp | gold `"wp5"` | sub `{"text":"wp5"}`
- `row:graph:src_2e6a054d4e4c7dbf:synth:v1:parameterized_material_region_extreme` | quoted_wp | gold `"wp3"` | sub `{"text":"wp3"}`
- `row:graph:src_39f9120cba7a64ed:synth:v2:parameterized_equal_feature_metric_ext` | quoted_wp | gold `"wp5"` | sub `{"text":"wp5"}`
- `row:graph:src_2654282f90eba4e2:synth:v2:parameterized_void_region_rank` | quoted_wp | gold `"wp15"` | sub `{"text":"wp15"}`
- `row:graph:src_b4d3ba4fc7b2f407:synth:v2:parameterized_feature_extreme` | quoted_wp | gold `"wp7"` | sub `{"text":"wp7"}`
- `row:graph:src_90c616ed38c6eb19:synth:v0:parameterized_equal_feature_metric_ext` | quoted_wp | gold `"wp8"` | sub `{"text":"wp8"}`
- `row:graph:src_5b820ae8cb16edbc:synth:v0:parameterized_void_region_rank` | quoted_wp | gold `"wp15"` | sub `{"text":"wp15"}`

### 6b. Full traces (first 8) — submission is the last block


**row_id:** `row:graph:graph:src_761577fa6538e2ed:q1:argmin_origin_z_workplane` | **gold:** `wp1`
```text
We are given a CadQuery script and asked to identify the target workplane that satisfies: "Among the remaining candidates, choose the one with the smallest workplane origin height." The script defines wp1 through wp5. We need to output the variable name of the workplane that meets the constraint. The script:

wp1 = cq.Workplane('XY', origin=(0,0,-41))
wp2 = wp1.circle(100)
wp3 = wp2.extrude(81)
wp4 = wp3.edges()
wp5 = wp4.fillet(2)
result = wp5

We need to interpret the workplanes. wp1 is a workplane in XY plane with origin at (0,0,-41). So its origin height (z-coordinate) is -41. wp2 is a circle on that workplane, so it's still on the same workplane? Actually, wp2 is the result of circle, which creates a 2D geometry on the workplane. The workplane itself remains? In CadQuery, operations like circle return a new workplane object that has the same plane but with the added geometry. So wp2's workplane origin is still (0,0,-41) presumably. Then wp3 is extrusion of that circle by 81 in the positive z direction? The default extrusion direction is along the workplane normal, which for XY plane is positive z. So the extrusion creates a solid from z=-41 to z=-41+81=40. So wp3 is a solid. Then wp4 = wp3.edges() - this selects the edges of the solid. The resulting workplane? Actually, edges() returns a Workplane object that contains the edges as objects, but the workplane itself might be the same as the parent? In CadQuery, .edges() returns a Workplane that is the same as the parent but with the selection of edges. So wp4 is still a workplane but with selected edges. Then wp5 = wp4.fillet(2) applies fillet to those edges. The result is a solid with fillets. So all these are workplanes or solids? Actually, the variable names are workplanes, but the result of extruding is a solid, but it's still a Workplane object. So we have multiple workplanes: wp1, wp2, wp3, wp4, wp5. The question: "Identify the target workplane that satisfies all of these constraints: - Among the remaining candidates, choose the one with the smallest workplane origin height." It says "remaining candidates", implying we need to consider which workplanes? Possibly the ones that are "remaining" after some selection? But the problem statement doesn't give any other constraints. Perhaps it's a trick: we need to find the workplane with the smallest origin height among all defined workplanes. Let's compute origin heights:

wp1: origin (0,0,-41) -> z = -41
wp2: derived from wp1, same origin? Typically, circle doesn't change the workplane origin. So wp2 origin is also (0,0,-41).
wp3: extrusion creates a solid, but the workplane after extrusion? The workplane is likely still the same planar workplane? Actually, in CadQuery, after extrusion, the workplane is still the same? I think the workplane is the same as the base workplane (the one used for the profile). But the extrusion adds a solid, but the workplane remains. So wp3 origin is still (0,0,-41)? However, note that the extrusion is along the normal, so the resulting solid extends from z=-41 to z=40. The workplane itself is still the original plane. So wp3 origin is still -41.
wp4: edges() returns a workplane that is the same as the parent? The parent is wp3, so origin is still -41.
wp5: fillet returns a workplane with the solid, origin still -41.

So all have the same origin height? That would be trivial. But maybe the workplane after extrusion changes? Actually, in CadQuery, the workplane is defined by a plane and a position. When you create a workplane with origin, that sets the location. When you do operations like circle, extrude, etc., the resulting workplane might have a different origin? Let's think: In CadQuery, the Workplane object carries a "plane" (the coordinate system) and a "context" (the current set of objects). The origin of the plane is the location of the plane's origin. For a workplane created with `cq.Workplane('XY', origin=(0,0,-41))`, the plane is an XY plane with its origin at (0,0,-41). So the plane's Z=0 is at world z=-41. Then subsequent operations like circle draw on that plane. After extrusion, the resulting solid is in 3D, but the workplane still has the same plane? Actually, the extrusion operation returns a new Workplane object that holds the solid. The plane of that workplane? I think it remains the same as the original plane. So all workplanes have the same plane origin. Thus all have the same origin height = -41. So the smallest among them is -41, but they are all equal. That would mean any of them qualifies, but the question says "choose the one with the smallest workplane origin height" implying there might be a difference. Perhaps the "remaining candidates" refers to something else? Maybe the question is incomplete? Alternatively, maybe the workplane after extrusion has a different origin? Let's look at CadQuery documentation: The Workplane object after extrusion typically has its plane set to the top face of the extrusion? Actually, after extrusion, the workplane might be set to the top face? No, that's not typical. There is a method `end()` that moves to the top face. But here, no such method. So the workplane remains the same.

Wait: The script defines wp1, then wp2, wp3, wp4, wp5. The result is wp5. The question: "Identify the target workplane that satisfies all of these constraints: - Among the remaining candidates, choose the one with the smallest workplane origin height." Possibly the "remaining candidates" are the workplanes that are defined in the script? Or maybe we need to consider that after some operations, the workplane's origin might change? For instance, after extruding, the workplane might be set to the top face? Actually, in CadQuery, when you extrude, the resulting workplane is still the same as the original workplane. But there is a method `faces()` that selects faces. The workplane's plane can be changed if you select a face. However, here we have `edges()` and `fillet()`. The fillet operation returns a new workplane, but the plane is still the same? I think the plane remains the same as the parent.

Let's test with a simple mental model: In CadQuery, the Workplane object is essentially a stack of operations. The plane is a property. When you call `circle`, it adds a 2D circle, but the plane doesn't change. When you extrude, it creates a 3D solid, but the plane remains the same. So all workplanes have the same origin. So they all have the same height. So the smallest is all of them. But the question expects a single variable name. Perhaps we need to consider that wp1 is the base workplane, and wp2, wp3, wp4, wp5 are derived. But they all have the same origin. So maybe the answer is wp1 because it has the smallest origin height? But they are equal. Alternatively, maybe the "origin height" is the z-coordinate of the workplane's origin, and for wp1 it's -41. For wp2, it's still -41. For wp3, the extrusion might shift the workplane? Actually, there is a nuance: In CadQuery, when you extrude a profile, the resulting solid is created, but the workplane does not change. However, the workplane's origin is the plane's origin. So it's the same.

Perhaps the question is about the "workplane" that is the result of the script? The result is wp5, but we need to choose among the remaining candidates? The phrasing "remaining candidates" suggests there might be a selection process. Maybe the problem is from a larger context where we have to reason about which workplane is the "target" given some constraints. Since we only have this script, perhaps we need to output the variable name of the workplane that has the smallest origin height. Since all are equal, we might choose the first one, wp1. But let's check if any operation changes the workplane's origin. For instance, the `edges()` method selects edges, but the workplane's plane remains the same. The `fillet` operation also doesn't change the plane. So all have the same plane.

Another possibility: The workplane origin of wp1 is (0,0,-41). After circle, wp2 is still on that plane. After extrusion, the solid exists from z=-41 to z=40. The workplane of wp3 is still the same plane. However, the "workplane" object might have a different representation after extrusion? Actually, the Workplane object holds a "plane" attribute. That plane has an origin. So yes, it's the same.

Thus, the smallest origin height is -41, and all have that. So perhaps the answer is simply wp1? But the question says "Among the remaining candidates", which might imply that we are to consider only the workplanes that are "remaining" after some operation? Perhaps we need to consider that the workplane after extrusion might have a different origin if we consider the "top" of the solid? But no.

Alternatively, maybe the script is incomplete? Let's read the problem statement: "Given the CadQuery script below, answer the question by reasoning about the CAD construction." Then the script. Then "Identify the target workplane that satisfies all of these constraints: - Among the remaining candidates, choose the one with the smallest workplane origin height." It doesn't mention any other constraints. So it's ambiguous. Possibly the "remaining candidates" are the workplanes that are defined in the script? That is wp1, wp2, wp3, wp4, wp5. And we need to choose the one with the smallest origin height. Since all are equal, we need to choose one. But perhaps the answer is wp1 because it's the only one that has an explicitly set origin? Or maybe the origin of wp2, wp3, etc. might be considered as the origin of the workplane after the operation, but they are the same.

Wait, could it be that the origin of the workplane after extrusion is actually the center of the top face? In some CAD systems, after extrusion, the workplane might be moved to the top face. But in CadQuery, that is not automatic. You have to explicitly use `end()` or `faces()` to move to a face. So no.

Given the typical usage, the script creates a cylinder from z=-41 to z=40, then fillets edges. The result is a cylinder with filleted edges. The workplanes are all on the same plane. So we need to output the variable name of the workplane with the smallest origin height. Since all are equal, we could output any. But the instruction says "Return exactly one source variable name, for example `wp7`." So we need to pick one. Perhaps the answer is wp1 because it's the first? Or maybe the "remaining candidates" are those that are not the result? The result is wp5, so maybe we consider wp1 to wp4? The constraint says "Among the remaining candidates", which might imply that we have a set of candidates, and we need to choose the one with smallest origin height. I think the most straightforward interpretation is that we need to find the workplane with the smallest z-coordinate of its origin. Since all are -41, we can choose any. But the problem expects a specific answer. Possibly the answer is "wp1" because it's the only one that explicitly sets the origin. However, let's double-check: In CadQuery, the workplane's origin is the location of the plane's origin. For wp1, it's set to (0,0,-41). For wp2, it's inherited. So they all have the same. So the smallest is -41, and all have it. So the answer could be any, but likely the intended answer is wp1 because it's the base.

Alternatively, maybe the workplane origin changes after extrusion because the extrusion adds a solid and the workplane is now the "new" workplane? Actually, there is a subtlety: After extrusion, the workplane's "plane" might be redefined to the top face? I recall that in CadQuery, when you extrude, the resulting workplane is the same as the original, but the object is a solid. However, if you then call `faces()`, it selects faces. But edges() is different. I think it's safe to assume all have same origin.

Given the lack of further constraints, I'll answer with wp1. But let's think: The question says "Among the remaining candidates", which might imply that we have to consider the workplanes that are "remaining" after some selection process. Perhaps the script is part of a larger problem where we are asked to identify a target workplane based on constraints, and the "remaining candidates" are those that are not eliminated by previous constraints. Since only one constraint is given, we just need to pick the one with smallest origin height. So all have the same, so we can pick any. But to be safe, we should output the one with the smallest origin height, which is -41. Since all are -41, we can output wp1. However, maybe the origin of wp2, wp3, etc. is not defined? Actually, they are defined as the result of operations, so they have origins.

Another thought: The "workplane origin height" might refer to the z-coordinate of the workplane's origin relative to the world. For wp1, it's -41. For wp2, it's still -41. But what about wp3? The extrusion creates a solid, but the workplane is still the same. So -41. So all equal.

Thus, I'll answer with "wp1". But let's see if there is any trick: The script ends with "result = wp5". So the final result is wp5. Perhaps the question expects us to return the variable name of the workplane that is the result? No, it says "target workplane that satisfies all of these constraints". The constraint is smallest origin height. So we need to choose among the candidates. Since all have same, maybe the answer is wp1 because it's the only one that directly sets the origin? Or maybe the answer is wp5 because it's the final? But the constraint says smallest, so if all are equal, any is smallest. But the problem likely expects a specific one.

I recall that in some CadQuery scripts, the workplane after extrusion might have its origin at the center of the top face? Actually, no. Let's check the CadQuery documentation: The `Workplane` object has a `plane` attribute which is a `cq.Plane` object. The `Plane` has an `origin` which is a Vector. When you create a workplane with `cq.Workplane('XY', origin=(0,0,-41))`, the plane's origin is at (0,0,-41). After doing `circle`, the workplane's plane remains the same. After `extrude`, the workplane's plane remains the same. So all have the same origin.

Thus, the answer is any of them. But the problem says "Return exactly one source variable name", so we need to output one. I'll output "wp1". However, we should ensure that the answer is in the correct format. The final response must end with a JSON tool call. So we need to produce a JSON object with "name": "submit_text" and arguments containing "text" with the variable name. For example: {"name": "submit_text", "arguments": {"text": "wp1"}}.

But let's reason step by step as requested. I'll write a reasoning first, then the tool call.

The reasoning: All workplanes (wp1 through wp5) have the same origin height of -41 because the origin is set only once and not changed by subsequent operations. Therefore, they all have the same smallest origin height. However, among the candidates, wp1 is the first and has the explicitly set origin. Since the constraint is to choose the one with the smallest origin height, and all are equal, we can choose wp1. (Alternatively, any would work, but the problem likely expects wp1.)

Thus, answer: wp1.

The workplane origins are all identical because the initial origin is set at (0, 0, -41) and subsequent operations (circle, extrude, edges, fillet) do not change the workplane's plane. Therefore, all workplanes have the same origin height of -41. Among them, the smallest origin height is -41, and any workplane qualifies. Since the problem asks for one variable name, the first workplane `wp1` is a valid choice.

```json
{"name": "submit_text", "arguments": {"text": "wp1"}}
```
```

**row_id:** `row:graph:src_f8d598a7cae260b8:synth:v2:parameterized_feature_rank` | **gold:** `wp11`
```text
The solid features are wp5 (frustum, 3 faces), wp10 (frustum, 3 faces), wp11 (hollow frustum, 4 faces), wp16 (sweep of rectangle, 6 faces), wp17 (union, 10 faces). Ordering by face count ascending: wp5 (3), wp10 (3), wp11 (4), wp16 (6), wp17 (10). The 3rd candidate is wp11.

{"name": "submit_text", "arguments": {"text": "wp11"}}

Let's produce that.

The script creates several solid features: wp5, wp10, wp11, wp16, and wp17. Their face counts are 3, 3, 4, 6, and 10 respectively. Ordering from smallest to greatest face count gives wp5 (3), wp10 (3), wp11 (4), wp16 (6), wp17 (10). The third candidate in this order is wp11.

```json
{"name": "submit_text", "arguments": {"text": "wp11"}}
```

**row_id:** `row:graph:src_f8d598a7cae260b8:synth:v2:parameterized_feature_rank` | **gold:** `wp11`
```text
We need to analyze the script to determine face counts for the various workplane objects and find the one that meets the constraint.

The problem requires:
- Identify target feature with a specific **face count** property.
- Among candidates, choose the 3rd from smallest to greatest face count.

Let's trace each workplane.

---

**wp1** = Workplane 'XY', origin (0,0,-67). No shape yet (just a plane).  
**wp2** = wp1.circle(27) → a 2D circle on XY, moved.  
**wp3** = wp2.workplane(offset=100) → new plane offset.  
**wp4** = wp3.circle(57) → circle radius 57.  
**wp5** = wp4.loft(combine=True) → creates a solid by lofting between the two circles.  
- This is a **frustum-like** solid: top circle radius 57, bottom radius 27, height 100.  
- Face count: 3 (bottom flat face, top flat face, lateral face).

**wp6** = new Workplane XY, origin (0,0,-67).  
**wp7** = wp6.circle(18).  
**wp8** = wp7.workplane(offset=100).  
**wp9** = wp8.circle(49).  
**wp10** = wp9.loft(combine=True): solid, radius 18 → 49 over height 100. Face count: 3 again.  

**wp11** = wp5.cut(wp10) → subtracts inner cone from outer cone, producing a **hollow frustum** (like a tube with conical walls).  
- Face count for a hollow solid: outer lateral face, inner lateral face, top annular face, bottom annular face → 4 faces.

**wp12** = new Workplane XY origin (0,0,-67).  
**wp13** = wp12.splineApprox(... makeWire=True): This creates a 3D **wire** (not a solid) from the given points. Wires have no face count (or 0).  
**wp14** = Workplane defined by custom plane origin and normal.  
**wp15** = wp14.rect(4, 100) → a 2D rectangle.  
**wp16** = wp15.sweep(wp13, isFrenet=True, multisection=True): Sweeps the rectangle along that 3D wire path, producing a **swept solid**. That swept solid’s face count: A rectangular sweep will likely have faces: start cap, end cap, and 4 side faces → 6 faces.  
**wp17** = wp11.union(wp16, clean=True) → combines the hollow frustum (4 faces) and the swept solid (6 faces). Union might reduce face count if faces are coplanar and merged, but shapes are far apart so likely total faces = 4 + 6 = 10.  
**result** = wp17.

---

Now, face counts:
- wp2: 2D circle (wire) — 0 faces in solid sense.
- wp5: 3 faces.
- wp7: 2D — 0.
- wp10: 3 faces.
- wp11: 4 faces.
- wp13: wire — 0.
- wp15: 2D rect — 0.
- wp16: 6 faces.
- wp17: ~10 faces.

We need the target feature’s face count. Possibly the question means we are to examine named variables that are **solids**. The *candidates* appear to be the solid workplanes: wp5 (3), wp10 (3), wp11 (4), wp16 (6), wp17 (10).  

Ordering from smallest to greatest face count:
1. wp5 (3)
2. wp10 (3)  
3. wp11 (4) ← 3rd candidate  
4. wp16 (6)  
5. wp17 (10)  

So the 3rd candidate when ordered from smallest to greatest face count is **wp11**.

---

```json
{"name": "submit_text", "arguments": {"text": "wp11"}}
```
```

**row_id:** `row:graph:graph:src_761577fa6538e2ed:q1:argmin_origin_z_workplane` | **gold:** `wp1`
```text
We need to understand the CadQuery script. It creates a Workplane at origin (0,0,-41) with XY plane. Then adds a circle of radius 100? Actually circle(100) creates a circle of radius 100? In CadQuery, circle(radius) draws a circle. So wp2 is a circle on that workplane. Then extrude 81 units. So wp3 is a solid cylinder of radius 100 and height 81, extruded along the workplane normal? The workplane is XY, origin at (0,0,-41). The normal of XY is Z-direction. So extrusion is along Z? Usually extrude goes in the positive Z direction from the workplane. But origin at -41, so the workplane is at z=-41. Extrude 81 means the solid from z=-41 to z=40? Actually extrude takes a distance. By default extrude goes in the positive normal direction. So it extrudes from z=-41 to z=-41+81=40. So the cylinder spans from z=-41 to z=40, radius 100.

Then wp4 = wp3.edges() selects all edges? Actually .edges() returns a Workplane containing all edges of the solid. Then wp5 = wp4.fillet(2) applies fillet to those edges with radius 2. But fillet on edges? Actually fillet() on a Workplane of edges applies fillet to those edges. So result is a solid with filleted edges.

The question: "Identify the target workplane that satisfies all of these constraints: - Among the remaining candidates, choose the one with the smallest workplane origin height." It says "remaining candidates" implying there are multiple workplanes? Actually the script defines wp1, wp2, wp3, wp4, wp5. We need to find which one satisfies constraints? The constraint is "smallest workplane origin height". We need to look at workplane origin heights. wp1 has origin (0,0,-41). wp2 is a workplane? Actually wp2 = wp1.circle(100) returns a Workplane with the circle shape, but its origin is still same as wp1? In CadQuery, operations like circle() keep the same workplane (the same origin and plane). So wp2 has same origin as wp1? Actually circle() returns a new Workplane with the circle geometry, but the workplane itself retains the same position and orientation. So wp2 origin also (0,0,-41). wp3 = wp2.extrude(81) returns a Workplane? Actually extrude returns a solid, but the workplane of the result? In CadQuery, after extrusion, the workplane is the top face? Actually the result of extrude is a Workplane object that contains the solid, and its workplane is usually the workplane of the extrusion? I'm not entirely sure. Typically, when you extrude, the resulting Workplane is the same as the original workplane? But actually the extrusion returns a new Workplane that contains the solid. The workplane's plane is the same as the original? Or it might be the plane of the top face? Let's check CadQuery documentation: After extrusion, the workplane is moved to the top (or bottom?) Actually I recall that after extrusion, the workplane is reset to the top face of the extrusion. For example, if you do box(10,10,10) the workplane ends up on the top face. In our case, wp2.circle(100) creates a circle on the XY plane at z=-41. Then extrude(81) creates a cylinder with height 81. The resulting workplane might be the top face of the cylinder? That would be at z=-41+81=40. So wp3's workplane origin would be at (0,0,40) and its plane would be XY? Actually the top face is a circle at z=40, so its plane is XY plane offset. So wp3's workplane is at z=40. Then wp4 = wp3.edges() - edges() returns a Workplane containing all edges of the solid. The workplane of that? In CadQuery, .edges() returns a Workplane that is based on the edges, but the workplane might be the same as the previous? Actually edges() returns a new workplane that is a collection of edges, and its workplane is the same as the previous? It might be the same plane? I think edges() does not change the workplane. It just selects edges, but the workplane remains the same as the parent. So wp4's workplane origin is the same as wp3's? Actually wp3's workplane origin is at (0,0,40) (top face). Then wp4 = wp3.edges() returns a Workplane with the same workplane as wp3. So wp4 origin (0,0,40). Then wp5 = wp4.fillet(2) applies fillet to edges. That returns a new solid. The workplane after fillet? Typically, fillet returns a Workplane containing the modified solid, and its workplane is the same as the input's workplane. So wp5's workplane origin likely remains (0,0,40). However, note that the fillet operation might change the workplane? Usually fillet does not change the workplane.

So we have multiple workplane origins: wp1 at z=-41, wp2 at z=-41, wp3 at z=40, wp4 at z=40, wp5 at z=40. Which one has the smallest origin height? -41 is smaller than 40. So wp1 and wp2 have -41. Among those, which are "remaining candidates"? The question says "Among the remaining candidates, choose the one with the smallest workplane origin height." It implies there is a set of candidates. Perhaps we need to identify the workplane that is the target? The instruction: "Identify the target workplane that satisfies all of these constraints: - Among the remaining candidates, choose the one with the smallest workplane origin height." This is ambiguous. Possibly the script defines multiple workplanes and we need to pick one that meets the constraint. The constraint is "smallest workplane origin height". So we need to output the variable name of the workplane with the smallest origin height. That would be either wp1 or wp2 (both -41). But we need one variable name. Possibly they are considered the same? But we need to check if wp1 and wp2 have the same origin? Yes. So any of them? But perhaps wp1 is the first workplane, and wp2 is the result of circle, but its workplane origin is still the same. So both have origin at z=-41. However, the question says "Among the remaining candidates", which might refer to a list of candidates that are not yet eliminated. Maybe we need to reason about which workplane is the "target" for something else? The question is exactly as given. Let's re-read: "Identify the target workplane that satisfies all of these constraints: - Among the remaining candidates, choose the one with the smallest workplane origin height. Return exactly one source variable name, for example `wp7`." So we need to output the variable name of a workplane (presumably one of wp1, wp2, wp3, wp4, wp5) that has the smallest origin height. Since wp1 and wp2 both have -41, and wp3-5 have 40, the smallest is -41. So either wp1 or wp2. But which one? Maybe we need to also consider that some workplanes are not "remaining candidates"? The phrase "remaining candidates" suggests there might be a previous selection step. But the user only gave this script and the constraint. Possibly the constraint is that we need to find the workplane with the smallest origin height among all workplanes defined in the script. So answer should be wp1 (the first) or wp2. But which is the "source variable name"? They said "for example `wp7`". So we should output the name of the variable. Since wp1 is the first workplane created, and its origin is explicitly set to (0,0,-41). wp2 inherits that. So both have same height. But wp1 is the original, wp2 is derived. Usually in CadQuery, the workplane object after circle() is still the same workplane? Actually the origin is preserved. So both have same origin. So we can choose either. However, we must pick one. Let's see if there is any nuance: The workplane origin height is the z-coordinate of the origin. For wp1, it's -41. For wp2, it's also -41. So they tie. But the problem says "the one with the smallest workplane origin height" implying a unique candidate. Possibly wp1 and wp2 are considered the same? Or maybe wp2's origin is actually different? Let's think: When you do wp1.circle(100), the resulting workplane has the same origin as wp1. So yes, same. So we need to pick one. But maybe the script has some implicit selection? Alternatively, perhaps the question is to identify the target workplane that satisfies the constraint, and the answer could be wp1 because it's the only one that has that origin explicitly? Or maybe we need to consider that "remaining candidates" means after some operation? The script only constructs five workplanes, so all are candidates. The constraint is "smallest workplane origin height". The smallest is -41, and there are two. But maybe we need to consider that wp2 is a workplane that contains a circle, but its origin is still the same. So both are valid. However, perhaps the answer expects wp1 because it's the original one? Or maybe we need to output the name of the workplane that is the result of the script? No, result is wp5. So not that.

Let's read the question again: "Identify the target workplane that satisfies all of these constraints: - Among the remaining candidates, choose the one with the smallest workplane origin height." It says "remaining candidates" possibly implying that there was a previous step that eliminated some candidates. But we have no prior context. This is a single question. Possibly it's a trick: The only workplanes that are "candidates" might be those that are defined as variables? All of them are. Perhaps there is an implicit assumption that we consider only workplanes that are used as input to further operations? Or maybe we need to consider the workplane that is the "target" of something else? Hmm.

Another interpretation: The script creates a solid and then works on edges. The question might be asking: Among the workplanes that are created (wp1, wp2, wp3, wp4, wp5), which one has the smallest origin height? Since two have -41, we need to pick one. But maybe we need to consider that wp1's origin is explicitly set, while wp2's origin is inherited, but its height is also -41. So they are equal. However, the phrase "smallest workplane origin height" - if there is a tie, we need to pick one. Perhaps we can choose wp1 because it's the first? Or maybe the answer is wp1 because wp2 is not a "workplane" in the sense of a plane? Actually wp2 is a Workplane object, so it is a workplane.

Let me think about CadQuery: When you do wp1.circle(100), it returns a Workplane object that has the same plane as wp1, but also contains the circle geometry. So yes, it's a workplane. So both wp1 and wp2 have the same origin height. Which one is "remaining candidate"? Possibly the candidates are only those that are used in the final result? The script ends with result = wp5. So the final result is wp5, but the question asks to identify a target workplane. Not much.

Given the instruction is to return exactly one source variable name, and the example is `wp7`, we should output the variable name that has the smallest origin height. Since both wp1 and wp2 have that, we need to decide which is more correct. Perhaps we need to consider that wp1 is the initial plane, and the question might be expecting wp1. Alternatively, maybe we need to look at the actual origin height of each workplane after operations. For wp2, it is still the same plane, but after circle, the workplane might have changed? No, circle doesn't change the plane.

Maybe there is a nuance: In CadQuery, the workplane's origin is not necessarily the same as the plane origin? Actually the Workplane object has a property 'plane' which defines the coordinate system. The origin is the point where the workplane's local origin is. For wp1, it's (0,0,-41). For wp2, after circle, the workplane is still the same plane, so same origin. So tie.

Given the lack of further constraints, I think the most straightforward answer is wp1, as it is the first and explicitly set. Alternatively, perhaps the answer is wp2? But no reason.

Wait, the problem says "Among the remaining candidates". This suggests that there might be a previous selection of candidates. Perhaps the user meant that we have a list of workplanes and we need to choose the one with smallest origin height. But the script only has these. Maybe we need to output the variable name of the workplane that is the "target" for something else? The answer contract says "Return exactly one source variable name". So I'll go with wp1.

But let's double-check: wp1 origin is (0,0,-41). wp2 origin is same. wp3 is after extrusion. Could it be that wp3's origin is also (0,0,-41)? Actually when you extrude, the resulting workplane is often the top face. In CadQuery, after extrusion, the workplane is moved to the top face of the extrusion. For example, if you do box(10,10,10).end, the workplane is on the top face. So wp3 is likely at z=40. So the smallest is -41. So wp1 or wp2.

I'll choose wp1. However, to be safe, maybe we need to consider that the workplane of wp2 is actually the same object as wp1? No, they are separate variables. So answer could be wp1.

Alternatively, the question might be testing understanding that the workplane origin height of wp2 is the same as wp1, and we need to pick the one with smallest height, and since both are equal, perhaps we need to choose the one that comes first? The problem says "Among the remaining candidates", implying there is a set of candidates, and we need to pick the one with smallest height. If there are multiple, we might need to pick the one that appears first? But not specified.

Perhaps we need to look at the script and reason about "remaining candidates" meaning the workplanes that are still valid after some filtering? Actually, the constraint says "Among the remaining candidates", but no other constraints are given. So I think it's a simple question: find the workplane with the smallest origin height. That's wp1 (or wp2). I'll answer wp1.

But wait, could there be any other workplane like the workplane of wp4 or wp5? They have higher z. So smallest is -41.

I'll answer wp1.

However, let's double-check the extrusion: If the workplane is XY at z=-41, extrude by 81 in positive Z, the top face is at z=40. But the workplane after extrusion is typically the top face. So wp3's workplane origin is (0,0,40). So yes.

Thus answer: wp1.

I'll output the JSON tool call with text "wp1".

{
  "name": "submit_text",
  "arguments": {
    "text": "wp1"
  }
}
```

**row_id:** `row:graph:graph:src_5a76c86945d5f757:q1:argmin_origin_z_workplane` | **gold:** `wp1`
```text
wp1 origin (-100,0,0) has z=0. All subsequent workplanes (wp2-wp5) inherit the same origin from wp1 via circle, extrude, edges, chamfer. All have z=0, so wp1 (first) qualifies as smallest.

{"name": "submit_text", "arguments": {"text": "wp1"}}

The script defines five workplane variables (wp1 through wp5), all derived from the same initial workplane. The initial workplane `wp1` is created with origin `(-100, 0, 0)`, and subsequent operations (`circle`, `extrude`, `edges`, `chamfer`) do not alter the workplane's origin. Therefore, all variables share the same origin, with a z‑coordinate (height) of 0. Since all have equal height, any workplane qualifies as having the smallest height; the first variable `wp1` is chosen as the answer.

```json
{"name": "submit_text", "arguments": {"text": "wp1"}}
```

**row_id:** `cadqa_point_membership_73d613a36eb7ba7d` | **gold:** `outside`
```text
The script creates a complex shape consisting of a central swept tube (from the spline path) and many small extruded cylinders positioned at various locations around it. The query point is `[146.1622778101684, 0.0, -0.08248006601032642]`.

Reasoning:
- The main body is formed by sweeping a circle of radius 8 along a spline that goes through points with x ranging from 88 down to -87 and back up to 88, so the maximum extent in x is around ±88 for the centerline, plus radius 8, so ±96. The point's x-coordinate is 146.16, far beyond that.
- The extruded cylinders (circles of radius 5, extruded 5 units) are located at positions like (60,75,-62) etc., near the main body surface, not at x=146.
- Therefore the point is clearly outside the entire combined solid.

The answer is: **outside**

```json
{"name": "submit_text", "arguments": {"text": "outside"}}
```
```

**row_id:** `row:graph:graph:src_445c19cac5db338d:q1:argmin_origin_z_workplane` | **gold:** `wp11`
```text
We need to identify the target workplane that satisfies constraints: "Among the remaining candidates, choose the one with the smallest workplane origin height." The problem says: "Identify the target workplane that satisfies all of these constraints: - Among the remaining candidates, choose the one with the smallest workplane origin height." This is a bit ambiguous: "remaining candidates" likely refers to the workplanes defined in the script? Possibly we need to consider all workplanes created? The script defines wp1, wp2, ..., wp15. But the question asks for a source variable name like wp7. So we need to output the name of the workplane with the smallest origin height.

But what is "origin height"? Typically, workplane origin is a point in 3D space. The height probably refers to the z-coordinate of the origin? Since the workplanes are defined on XY plane (default origin at (0,0,0) unless translated). Let's examine each workplane's origin.

We have the following workplanes:
- wp1 = cq.Workplane('XY') -> origin at (0,0,0)
- wp2 = wp1.box(197,200,10) -> this creates a box, but wp2 is a Workplane object after the box? Actually, in CadQuery, box() returns a Workplane that is the result? Typically, `wp1.box(...)` returns a Workplane object that contains the resulting solid. But the workplane itself might have an origin? The workplane's origin is the same as the parent's origin unless changed. So wp2's origin is still (0,0,0) because it's the same workplane? Actually, after a box operation, the workplane remains the same? In CadQuery, the workplane is not changed; the box is added to the solid. But the Workplane object itself has a "plane" attribute that defines its coordinate system. The origin of the plane is the same as the original. So wp1 and wp2 share the same plane? But wp2 is the result of a box operation; it's a Workplane object that still has the same plane (XY) with origin at (0,0,0). However, there is also a translation later. Similarly, wp3 = cq.Workplane('XY') -> origin (0,0,0). wp4 = wp3.box(197,13,3) -> still origin (0,0,0). wp5 = wp4.translate([0,-36,3]) -> this translates the workplane? Actually, `translate` on a Workplane moves the workplane's origin? In CadQuery, `translate` on a Workplane returns a new workplane with the plane shifted by the vector. So wp5's origin is (0, -36, 3). wp6 = cq.Workplane('XY') -> origin (0,0,0). wp7 = wp6.box(197,13,3) -> origin (0,0,0). wp8 = wp7.translate([0,36,3]) -> origin (0,36,3). Then wp9 = wp2.cut(wp5) -> cut operation, but wp9 is the result of cutting wp5 from wp2; it's a Workplane? Actually, cut returns a Workplane with the resulting solid. The workplane's plane is still the same as the original? Which one? Typically, the result of cut returns a workplane that is the same as the first operand's workplane? But we don't care about that. The important thing is that we need the workplane origins. The script defines many workplane variables, but some are intermediate results. The question asks: "Identify the target workplane that satisfies all of these constraints: - Among the remaining candidates, choose the one with the smallest workplane origin height." So we need to consider the workplanes that are "candidates". Possibly the "remaining candidates" are the workplanes that are explicitly created? Or maybe the ones that are not used in operations? The instruction says "Return exactly one source variable name". So we need to pick one of the variables.

Let's list all workplane variables with their origins:

- wp1: Workplane('XY') -> origin (0,0,0)
- wp2: result of wp1.box(...) -> same plane, origin (0,0,0)
- wp3: Workplane('XY') -> origin (0,0,0)
- wp4: result of wp3.box(...) -> origin (0,0,0)
- wp5: translate of wp4 -> origin (0, -36, 3)
- wp6: Workplane('XY') -> origin (0,0,0)
- wp7: result of wp6.box(...) -> origin (0,0,0)
- wp8: translate of wp7 -> origin (0, 36, 3)
- wp9: result of wp2.cut(wp5) -> origin? The workplane of wp2 is (0,0,0), so wp9 likely stays at (0,0,0)
- wp10: result of wp9.cut(wp8) -> origin (0,0,0)
- wp11: cq.Workplane(cq.Plane(origin=cq.Vector(-98,0,-5), xDir=cq.Vector(0,3,0), normal=cq.Vector(3,0,0))) -> This creates a custom plane. Origin is (-98, 0, -5). Note: The plane's normal is (3,0,0), so it's a plane perpendicular to x-axis? Actually, normal = (3,0,0) is along x-axis, so the plane is YZ plane? But xDir is (0,3,0) which is along y-axis. So the plane is defined with origin at (-98,0,-5). The workplane's origin is that point.
- wp12: wp11.polyline(...) -> returns a Workplane with same plane? Probably same origin.
- wp13: wp12.close() -> same.
- wp14: wp13.extrude(197, combine=0) -> extrude creates a solid, but the workplane? The extrude returns a Workplane? Actually, combine=0 means it returns a new solid? The resulting workplane might have same plane? Typically, the result of extrude is a Workplane that contains the solid, but the plane remains the same. So origin still (-98,0,-5).
- wp15: wp10.union(wp14) -> union, result workplane likely same as wp10? Probably origin (0,0,0) since wp10 is the first.

Now, the question: "Among the remaining candidates, choose the one with the smallest workplane origin height." "Height" likely means the z-coordinate of the origin. So we need to compare the z values of the origins of the workplane variables. Which workplanes are "candidates"? Possibly all workplanes that are defined? Or maybe only those that are "source" workplanes? The answer is a variable name, so we need to output the one with smallest z.

Let's list z-coordinates:
wp1: 0
wp2: 0
wp3: 0
wp4: 0
wp5: 3
wp6: 0
wp7: 0
wp8: 3
wp9: 0 (likely)
wp10: 0
wp11: -5 (since origin z = -5)
wp12: -5
wp13: -5
wp14: -5
wp15: 0 (since union of wp10 and wp14, but the workplane origin of wp15 is the same as wp10? Actually, union returns a Workplane, and the plane is the same as the first operand? Usually, the workplane is unchanged. So origin (0,0,0) for wp15.)

Thus the smallest z is -5, belonging to wp11, wp12, wp13, wp14. Which one is the "target workplane"? The question says "identify the target workplane that satisfies all of these constraints". Possibly the constraint is "among the remaining candidates", meaning we need to choose from the workplanes that are explicitly defined? But the script defines many, and we need to pick one. The smallest origin height is -5, so any of wp11, wp12, wp13, wp14 have that. However, they are all derived from the same plane. Which one is the "source variable"? The question likely expects the variable that is the workplane itself, not the result of operations. Notice that the script defines wp11 as a custom workplane. Then wp12, wp13, wp14 are derived from it. The "source" might be the original workplane before any geometry? The problem says "source variable name", so probably the variable that is not derived from a previous operation? But all are variables. However, often in such problems, they want the workplane that is used to create the geometry. But the instruction: "Return exactly one source variable name, for example `wp7`." So we need to pick one that has the smallest height. Among all, the smallest is -5, and there are multiple. Which one is the "target"? Possibly we need to consider only the workplanes that are created with `Workplane( ... )` directly, not the ones resulting from operations like box, translate, cut, etc. Let's see: The script creates wp1, wp3, wp6, and wp11 as explicit Workplane constructors. The others are results of operations. So the "remaining candidates" might be those explicit workplanes? But then wp1, wp3, wp6 have z=0, wp11 has z=-5, so wp11 is smallest. But also wp5 and wp8 have z=3, which are higher. So wp11 is the smallest among explicit ones.

Alternatively, maybe the "remaining candidates" are all workplane variables that are defined (including wp2, etc.) but we need to choose the one with smallest origin height. That would be wp11, wp12, wp13, wp14. Among these, which one is the "source variable"? The problem says "source variable name", perhaps meaning the original workplane that is used to create the shape? The final result is wp15, but we are asked to identify a workplane. The example output is `wp7`. So likely we need to pick one of the defined variables. Since multiple have same smallest height, we need to see if there is any other constraint? The problem statement: "Identify the target workplane that satisfies all of these constraints: - Among the remaining candidates, choose the one with the smallest workplane origin height." That's the only constraint. So we need to find the workplane variable with the smallest z-coordinate of its origin. That is -5. Which variable has that? wp11, wp12, wp13, wp14. But note that wp12, wp13, wp14 are derived from wp11 and have the same plane. So they all have same origin. So they are all candidates. But the answer must be exactly one variable name. Which one is the "target"? Possibly the one that is the first one created? Or maybe the one that is used in the final union? Actually, wp14 is used in union. But we need to pick the smallest. Perhaps we need to consider the "workplane origin height" as the z-coordinate of the workplane's origin. All have -5. So we need to decide which one to output. The problem might expect the original workplane that was defined, not the result of operations like polyline, close, extrude. Because those are not "workplane" in the sense of a plane? Actually, they are still Workplane objects. But the typical interpretation: The "source" workplane is the one that is created with a plane definition. The later operations like polyline, close, extrude modify the geometry but the plane remains the same. So wp11 is the initial plane. wp12 is the result of polyline, which is a wire, but the workplane is still the same. So all have same origin. So any of them would have the same height. But the problem likely expects wp11, because it's the one that is explicitly defined with a custom plane. However, let's check the phrasing: "Among the remaining candidates" - what are the "remaining candidates"? Perhaps the script creates multiple workplanes, and we need to consider those that are used in the final result? Or maybe we need to consider all workplanes that are defined, but the "remaining" suggests some are eliminated? Possibly there is a hidden constraint: The question says "Identify the target workplane that satisfies all of these constraints:" and then only one constraint is listed. It might be that we need to consider the workplanes that are "candidates" for something else? The problem statement is a bit ambiguous.

Given typical CAD questions, they often ask: "Which workplane has the smallest origin height?" and we need to output the variable name. The smallest origin height is -5, and wp11 is the first one with that. Also note that wp11 is defined as a workplane with a custom plane. The others are derived. So I'll go with wp11.

But let's double-check: Is there any other workplane with a lower z? No, -5 is the lowest. So answer is wp11.

However, we must ensure that we are not missing any: wp5 has z=3, wp8 has z=3, all others 0. So yes.

Thus final answer: wp11.

We'll output the JSON tool call with text "wp11".

The workplane with the smallest origin height (z-coordinate) is wp11, which has an origin at (-98, 0, -5), giving a height of -5. All other workplanes have heights of 0 or 3.

```json
{"name": "submit_text", "arguments": {"text": "wp11"}}
```
```

**row_id:** `row:graph:graph:src_c39a861dbf652d38:q1:argmin_origin_z_workplane` | **gold:** `wp1`
```text
wp1 origin=(0,0,-2) height=-2; all others have heights 7 or 12. Thus smallest is -2; among candidates (all workplanes), wp1 is the one with explicitly set negative origin.

{"name": "submit_text", "arguments": {"text": "wp1"}}
```

### 6c. Submissions-only check: what does each trace actually end with?

Note on extraction: `sub` above shows the decoded arguments of the trace's final submission
(innermost JSON object). Checked properly (last `{"name":..., "arguments":...}` envelope in
the trace, else last bare JSON):

- **157/158** traces end with a full envelope, e.g. `{"name":"submit_text","arguments":{"text":"wp1"}}`
- **1/158** ends with bare args only: `row:graph:src_1fd9001060cfafdc:synth:v6:parameterized_*` → `{"text":"wp18"}`
- **0/158** have no final JSON.
- Note: many traces ALSO contain an example call inside the reasoning (e.g. `For example: {"name": ...}`)
  — the final block is the actual submission.
  - NOT submit_text: `row:graph:src_e0877e953bfb1632:synth:v0:parameterized_void_region_rank` last-json={"text":"wp40"}
  - NOT submit_text: `row:graph:src_a9645b50d0f33d97:synth:v0:parameterized_feature_extreme` last-json={"text":"wp5"}
  - NOT submit_text: `row:graph:graph:src_b966c1e81b88b84b:q1:argmax_origin_z_workplane` last-json={"text":"wp9"}
  - NOT submit_text: `row:graph:graph:src_52502a9d163c189b:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:src_4f329454f966c395:synth:v4:parameterized_feature_extreme` last-json={"text":"wp9"}
  - NOT submit_text: `row:graph:src_ba0cbaa3a36f33a8:synth:v2:parameterized_material_region_` last-json={"text":"wp14"}
  - NOT submit_text: `row:graph:graph:src_c652e441e8a12433:q1:argmax_origin_z_workplane` last-json={"text":"wp8"}
  - NOT submit_text: `row:graph:src_965d6cf1e63f032e:synth:parameterized_feature_effect_delt` last-json={"text":"wp88"}
  - NOT submit_text: `row:graph:src_5f1bce09365d2f9c:synth:v1:parameterized_feature_extreme` last-json={"text":"wp12"}
  - NOT submit_text: `row:graph:graph:src_09b8d8412ad88a86:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:src_d42a84549ea74920:synth:v2:parameterized_feature_rank` last-json={"text":"wp6"}
  - NOT submit_text: `row:graph:src_5372470d0d60b21b:synth:v4:parameterized_equal_feature_me` last-json={"text":"wp34"}
  - NOT submit_text: `row:graph:src_5f1bce09365d2f9c:synth:v3:parameterized_feature_extreme` last-json={"text":"wp12"}
  - NOT submit_text: `row:graph:src_312095f6cdb5b792:synth:v1:parameterized_feature_extreme` last-json={"text":"wp40"}
  - NOT submit_text: `row:graph:graph:src_ca2337b1a3e41549:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `cadqa_coordinate_frame_34be2d2cb6dbfd6b` last-json={"text":"cq.Plane(origin=cq.Vector(28, 85, -71), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))"}
  - NOT submit_text: `row:graph:graph:src_36312c330886e941:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:graph:src_bc0b45221d8f26d5:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:src_076afe82034b0268:synth:v3:parameterized_feature_extreme` last-json={"text":"wp16"}
  - NOT submit_text: `row:graph:src_30f43e17f3f6a93c:synth:v0:parameterized_void_region_extr` last-json={"text":"wp7"}
  - NOT submit_text: `cadqa_point_membership_73d613a36eb7ba7d` last-json={"text":"outside"}
  - NOT submit_text: `row:graph:src_cac1d4a39cbe829e:synth:v1:parameterized_feature_rank` last-json={"text":"wp5"}
  - NOT submit_text: `row:graph:src_a9645b50d0f33d97:synth:v0:parameterized_feature_extreme` last-json={"text":"wp5"}
  - NOT submit_text: `row:graph:graph:src_445c19cac5db338d:q1:argmin_origin_z_workplane` last-json={"text":"wp11"}
  - NOT submit_text: `row:graph:graph:src_7fe7c16131f2b4ef:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:graph:src_b966c1e81b88b84b:q1:argmax_origin_z_workplane` last-json={"text":"wp9"}
  - NOT submit_text: `row:graph:graph:src_c39a861dbf652d38:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:src_fc647ebe204a8cae:synth:v1:parameterized_feature_effect_d` last-json={"text":"wp6"}
  - NOT submit_text: `row:graph:src_d42a84549ea74920:synth:v5:parameterized_feature_rank` last-json={"text":"wp6"}
  - NOT submit_text: `row:graph:graph:src_761577fa6538e2ed:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:src_ba0cbaa3a36f33a8:synth:v2:parameterized_material_region_` last-json={"text":"wp14"}
  - NOT submit_text: `row:graph:src_4f329454f966c395:synth:v4:parameterized_feature_extreme` last-json={"text":"wp9"}
  - NOT submit_text: `row:graph:graph:src_52502a9d163c189b:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:graph:src_c652e441e8a12433:q1:argmax_origin_z_workplane` last-json={"text":"wp8"}
  - NOT submit_text: `row:graph:src_965d6cf1e63f032e:synth:parameterized_feature_effect_delt` last-json={"text":"wp88"}
  - NOT submit_text: `row:graph:src_f8d598a7cae260b8:synth:v2:parameterized_feature_rank` last-json={"text":"wp11"}
  - NOT submit_text: `row:graph:src_5f1bce09365d2f9c:synth:v1:parameterized_feature_extreme` last-json={"text":"wp12"}
  - NOT submit_text: `row:graph:src_5372470d0d60b21b:synth:v4:parameterized_equal_feature_me` last-json={"text":"wp34"}
  - NOT submit_text: `row:graph:graph:src_5a76c86945d5f757:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:graph:src_09b8d8412ad88a86:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:graph:src_ca2337b1a3e41549:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `cadqa_coordinate_frame_34be2d2cb6dbfd6b` last-json={"text":"cq.Plane(origin=cq.Vector(28, 85, -71), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))"}
  - NOT submit_text: `row:graph:graph:src_36312c330886e941:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:graph:src_bc0b45221d8f26d5:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:src_30f43e17f3f6a93c:synth:v0:parameterized_void_region_extr` last-json={"text":"wp7"}
  - NOT submit_text: `row:graph:src_312095f6cdb5b792:synth:v1:parameterized_feature_extreme` last-json={"text":"wp40"}
  - NOT submit_text: `row:graph:src_d42a84549ea74920:synth:v2:parameterized_feature_rank` last-json={"text":"wp6"}
  - NOT submit_text: `row:graph:graph:src_fb4914e26978c152:q1:argmax_origin_z_workplane` last-json={"text":"wp58"}
  - NOT submit_text: `row:graph:graph:src_01c11226b429ee19:q1:argmin_origin_z_workplane` last-json={"text":"wp8"}
  - NOT submit_text: `row:graph:graph:src_c506fa5d2a4c300e:q1:argmax_origin_z_workplane` last-json={"text":"wp15"}
  - NOT submit_text: `row:graph:src_199f9fbf5deeeccc:synth:v3:parameterized_feature_extreme` last-json={"text":"wp8"}
  - NOT submit_text: `row:graph:src_fff34c4e0845c7d5:synth:v2:parameterized_feature_rank` last-json={"text":"wp6"}
  - NOT submit_text: `row:graph:src_bf8ed1ccf42d99c3:synth:v4:parameterized_feature_rank` last-json={"text":"wp8"}
  - NOT submit_text: `row:graph:graph:src_2093036ba9d6ad16:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:graph:src_45e918a473b0b968:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:src_8cafa9c69b341ef5:synth:v0:parameterized_feature_rank` last-json={"text":"wp2"}
  - NOT submit_text: `row:graph:graph:src_ef76c3ead2acd74c:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:src_f4b77085698cf5e9:synth:v2:parameterized_feature_rank` last-json={"text":"wp3"}
  - NOT submit_text: `row:graph:src_076afe82034b0268:synth:v3:parameterized_feature_extreme` last-json={"text":"wp16"}
  - NOT submit_text: `row:graph:src_2567a3d79e3e7bb7:synth:v3:parameterized_feature_extreme` last-json={"text":"wp9"}
  - NOT submit_text: `row:graph:src_5721f17b41ba3d02:synth:v6:parameterized_feature_rank` last-json={"text":"wp11"}
  - NOT submit_text: `row:graph:graph:src_1a40408933c7e404:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:src_97f0da8117bea982:synth:v4:parameterized_feature_rank` last-json={"text":"wp6"}
  - NOT submit_text: `row:graph:graph:src_71d0b11eb1003c71:q1:argmax_origin_z_workplane` last-json={"text":"wp11"}
  - NOT submit_text: `row:graph:src_1fd9001060cfafdc:synth:v1:parameterized_feature_extreme` last-json={"text":"wp18"}
  - NOT submit_text: `row:graph:src_0bb71a18d5caede7:synth:v2:parameterized_feature_extreme` last-json={"text":"wp9"}
  - NOT submit_text: `cadqa_coordinate_frame_fa0f30cb24e9b0b7` last-json={"text":"XZ"}
  - NOT submit_text: `row:graph:graph:src_6599baa5190ac687:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:graph:src_ffce9e501f2990b6:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:src_5177f88909d9bc07:synth:v4:parameterized_feature_rank` last-json={"text":"wp24"}
  - NOT submit_text: `cadqa_point_membership_45983b175c10d33a` last-json={"text":"outside"}
  - NOT submit_text: `row:graph:src_10a0d99433f681dd:synth:v6:parameterized_feature_extreme` last-json={"text":"wp13"}
  - NOT submit_text: `row:graph:graph:src_96244e33e98986c9:q1:argmax_origin_z_workplane` last-json={"text":"wp15"}
  - NOT submit_text: `row:graph:graph:src_8c991c83d6889e31:q1:argmax_origin_z_workplane` last-json={"text":"wp9"}
  - NOT submit_text: `row:graph:src_5f1bce09365d2f9c:synth:v5:parameterized_feature_extreme` last-json={"text":"wp4"}
  - NOT submit_text: `row:graph:graph:src_792574c1eb0a85ac:q1:argmin_origin_z_workplane` last-json={"text":"wp37"}
  - NOT submit_text: `row:graph:graph:src_5d0aef385602f7b8:q1:argmin_origin_z_workplane` last-json={"text":"wp7"}
  - NOT submit_text: `row:graph:graph:src_498a150dd91703c8:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:src_45411243056a83aa:synth:v4:parameterized_feature_extreme` last-json={"text":"wp9"}
  - NOT submit_text: `row:graph:src_912f1e9bba23e9c2:synth:v3:parameterized_material_region_` last-json={"text":"wp27"}
  - NOT submit_text: `row:graph:graph:src_2fcfebe03ee4bafe:q1:argmax_origin_z_workplane` last-json={"text":"wp15"}
  - NOT submit_text: `row:graph:src_a9645b50d0f33d97:synth:v5:parameterized_feature_rank` last-json={"text":"wp10"}
  - NOT submit_text: `row:graph:src_49b4e19335c94de4:synth:v4:parameterized_equal_feature_me` last-json={"text":"wp4"}
  - NOT submit_text: `row:graph:src_fff34c4e0845c7d5:synth:v5:parameterized_feature_extreme` last-json={"text":"wp6"}
  - NOT submit_text: `row:graph:src_f8d598a7cae260b8:synth:v0:parameterized_feature_extreme` last-json={"text":"wp11"}
  - NOT submit_text: `row:graph:graph:src_11ba889dc68f5860:q1:argmin_origin_z_workplane` last-json={"text":"wp18"}
  - NOT submit_text: `row:graph:src_448c4ee6d20dbd71:synth:v0:parameterized_feature_extreme` last-json={"text":"wp5"}
  - NOT submit_text: `row:graph:src_10a0d99433f681dd:synth:v2:parameterized_feature_rank` last-json={"text":"wp5"}
  - NOT submit_text: `row:graph:graph:src_4cfb753ecf36ca8d:q1:argmax_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:src_d593f529e4ece0ed:synth:v1:parameterized_equal_feature_me` last-json={"text":"wp13"}
  - NOT submit_text: `row:graph:src_1fd9001060cfafdc:synth:v6:parameterized_feature_extreme` last-json={"text":"wp18"}
  - NOT submit_text: `row:graph:src_a9645b50d0f33d97:synth:v1:parameterized_feature_extreme` last-json={"text":"wp10"}
  - NOT submit_text: `cadqa_coordinate_frame_3fc34533f867475e` last-json={"text":"XY"}
  - NOT submit_text: `row:graph:graph:src_63920ba56647ad9b:q1:argmax_origin_z_workplane` last-json={"text":"wp7"}
  - NOT submit_text: `cadqa_coordinate_frame_255f68d7d652d955` last-json={"text":"cq.Plane(origin=cq.Vector(-72, 53, 36), xDir=cq.Vector(-2, -2, 0), normal=cq.Vector(-2, 2, 0))"}
  - NOT submit_text: `row:graph:graph:src_5c4c502dda30f91e:q1:argmax_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:src_ae75bdf1f46f2e97:synth:v2:parameterized_equal_feature_me` last-json={"text":"wp7"}
  - NOT submit_text: `row:graph:graph:src_c96f1465b0b434d5:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:graph:src_2c7ab7e12c203437:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:graph:src_b282ae8b3a703a7c:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:graph:src_6d32ccf39ec26016:q1:argmax_origin_z_workplane` last-json={"text":"wp8"}
  - NOT submit_text: `row:graph:src_e75edeac3a3125f2:synth:v2:parameterized_feature_rank` last-json={"text":"wp5"}
  - NOT submit_text: `row:graph:src_9395d21214e13847:synth:v0:parameterized_feature_extreme` last-json={"text":"wp8"}
  - NOT submit_text: `row:graph:src_fff34c4e0845c7d5:synth:v5:parameterized_feature_rank` last-json={"text":"wp6"}
  - NOT submit_text: `cadqa_coordinate_frame_84dbfb4a2e3c199a` last-json={"text":"cq.Plane(origin=cq.Vector(-21, 94, 21), xDir=cq.Vector(3, 1, 0), normal=cq.Vector(-1, 3, 0))"}
  - NOT submit_text: `row:graph:src_cac1d4a39cbe829e:synth:v0:parameterized_feature_extreme` last-json={"text":"wp10"}
  - NOT submit_text: `row:graph:src_ec27c2c6c3c4874c:synth:v1:parameterized_feature_extreme` last-json={"text":"wp16"}
  - NOT submit_text: `row:graph:graph:src_657f2343a89a88b6:q1:argmin_origin_z_workplane` last-json={"text":"wp1"}
  - NOT submit_text: `row:graph:src_fff34c4e0845c7d5:synth:v6:parameterized_feature_rank` last-json={"text":"wp6"}
  - NOT submit_text: `row:graph:src_e9b6195afa5f9fd8:synth:v3:parameterized_feature_rank` last-json={"text":"wp2"}
  - NOT submit_text: `cadqa_coordinate_frame_6fc5fec0e50f913d` last-json={"text":"cq.Plane(origin=cq.Vector(28, 85, 18), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))"}
  - NOT submit_text: `row:graph:src_f8d598a7cae260b8:synth:v4:parameterized_feature_rank` last-json={"text":"wp17"}
  - NOT submit_text: `row:graph:src_f26a873793182b86:synth:v0:parameterized_feature_rank` last-json={"text":"wp7"}
  - NOT submit_text: `row:graph:src_e70d18a16c5d74c9:synth:v0:parameterized_material_region_` last-json={"text":"wp32"}
  - NOT submit_text: `row:graph:src_ec27c2c6c3c4874c:synth:v0:parameterized_feature_rank` last-json={"text":"wp11"}
  - NOT submit_text: `row:graph:src_418323d094b238ea:synth:v0:parameterized_equal_feature_me` last-json={"text":"wp4"}
  - NOT submit_text: `row:graph:src_962a96132d3c97fb:synth:v2:parameterized_feature_extreme` last-json={"text":"wp2"}
  - NOT submit_text: `row:graph:src_f4b704cae821ea18:synth:v2:parameterized_equal_feature_me` last-json={"text":"wp16"}
  - NOT submit_text: `row:graph:src_d42a84549ea74920:synth:v3:parameterized_feature_rank` last-json={"text":"wp6"}
  - NOT submit_text: `row:graph:src_a9645b50d0f33d97:synth:v3:parameterized_feature_rank` last-json={"text":"wp5"}
  - NOT submit_text: `row:graph:src_41f38f1f99b53bf2:synth:v2:parameterized_feature_effect_d` last-json={"text":"wp27"}
  - NOT submit_text: `row:graph:src_d42a84549ea74920:synth:v6:parameterized_feature_rank` last-json={"text":"wp6"}
  - NOT submit_text: `row:graph:src_28bbaee6a238a3dd:synth:v1:parameterized_feature_extreme` last-json={"text":"wp6"}
  - NOT submit_text: `row:graph:src_cdb3d79dad35eb0e:synth:v3:parameterized_equal_feature_me` last-json={"text":"wp3"}
  - NOT submit_text: `cadqa_coordinate_frame_771ddff402c042f4` last-json={"text":"cq.Plane(origin=cq.Vector(28, 85, -71), xDir=cq.Vector(3, -1, 0), normal=cq.Vector(1, 3, 0))"}
  - NOT submit_text: `row:graph:src_448c4ee6d20dbd71:synth:v2:parameterized_feature_rank` last-json={"text":"wp11"}
  - NOT submit_text: `row:graph:src_448c4ee6d20dbd71:synth:v2:parameterized_feature_extreme` last-json={"text":"wp5"}
  - NOT submit_text: `row:graph:src_60104e08ce206114:synth:v3:parameterized_void_region_extr` last-json={"text":"wp11"}
  - NOT submit_text: `row:graph:src_1fd9001060cfafdc:synth:v6:parameterized_feature_rank` last-json={"text":"wp18"}
  - NOT submit_text: `row:graph:src_5a4cb92eccd9464d:synth:v0:parameterized_equal_feature_me` last-json={"text":"wp15"}
  - NOT submit_text: `cadqa_coordinate_frame_34066716c9cd26d1` last-json={"text":"cq.Plane(origin=cq.Vector(-21, -94, -21), xDir=cq.Vector(-3, 1, 0), normal=cq.Vector(-1, -3, 0))"}
  - NOT submit_text: `cadqa_coordinate_frame_5ee53d30742db479` last-json={"text":"XY"}
  - NOT submit_text: `row:graph:src_2f7164378ebc1070:synth:v4:parameterized_equal_feature_me` last-json={"text":"wp7"}
  - NOT submit_text: `row:graph:src_45d78af91b095c0b:synth:v3:parameterized_feature_effect_d` last-json={"text":"wp24"}
  - NOT submit_text: `row:graph:src_a8e86677b1229be6:synth:v4:parameterized_material_region_` last-json={"text":"wp6"}
  - NOT submit_text: `row:graph:src_d96435feec0d1857:synth:v2:parameterized_equal_feature_me` last-json={"text":"wp4"}
  - NOT submit_text: `row:graph:src_a7cbffac392f370d:synth:v4:parameterized_equal_feature_me` last-json={"text":"wp20"}
  - NOT submit_text: `row:graph:src_66f7d69e9876eb33:synth:v4:parameterized_feature_rank` last-json={"text":"wp40"}
  - NOT submit_text: `row:graph:src_93c5c43d89c9c119:synth:v4:parameterized_equal_feature_me` last-json={"text":"wp13"}
  - NOT submit_text: `row:graph:src_7358a92e08fb679a:synth:v0:parameterized_equal_feature_me` last-json={"text":"wp7"}
  - NOT submit_text: `row:graph:src_a9645b50d0f33d97:synth:v1:parameterized_material_region_` last-json={"text":"wp5"}
  - NOT submit_text: `row:graph:src_ac7a3c4224a74dc8:synth:v0:parameterized_equal_feature_me` last-json={"text":"wp5"}
  - NOT submit_text: `row:graph:src_2e6a054d4e4c7dbf:synth:v1:parameterized_material_region_` last-json={"text":"wp3"}
  - NOT submit_text: `row:graph:src_39f9120cba7a64ed:synth:v2:parameterized_equal_feature_me` last-json={"text":"wp5"}
  - NOT submit_text: `row:graph:src_2654282f90eba4e2:synth:v2:parameterized_void_region_rank` last-json={"text":"wp15"}
  - NOT submit_text: `row:graph:src_b4d3ba4fc7b2f407:synth:v2:parameterized_feature_extreme` last-json={"text":"wp7"}
  - NOT submit_text: `row:graph:src_90c616ed38c6eb19:synth:v0:parameterized_equal_feature_me` last-json={"text":"wp8"}
  - NOT submit_text: `row:graph:src_5b820ae8cb16edbc:synth:v0:parameterized_void_region_rank` last-json={"text":"wp15"}
