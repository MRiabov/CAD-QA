# Invalid text-gold rows — exact row_ids (recovered 2026-08-09)

These 22 `v3_curriculum` rows had `wpN_center` golds (centered-workplane node-id
leak): the gold encoded the ontology node id, not the source variable name —
**uninstructable** for eval and rejection sampling (model's `wp16` could never
match gold `wp16_center`). Fixed in `fix-text-gold-encoding` (re-uploaded
parquets: golds normalized to `wp16` etc., 0 quoted, 0 `_center`).

Recovered from the stale pre-fix local HF cache
(`v3_curriculum/0.0.0/{604f135cc497dadd388387ea9093579223699500,1e681cf82fc2b7ae5c3e3dd6faa84933094041bc}/cadqa-rl-2000-train.arrow`,
which still carry the original `_center` golds; the newest cache hash
`494af2d1fe9a630cb3d58511840ffe01e6d99301` is post-fix with 0 center golds).

Use these row_ids to target re-sampling (now gradable against the fixed golds).

```text
row:graph:graph:src_0e9e2eded60c5714:q1:argmax_origin_z_workplane
row:graph:graph:src_0e9e2eded60c5714:q1:argmin_origin_z_workplane
row:graph:graph:src_2c2f5faf819cc714:q1:argmax_origin_z_workplane
row:graph:graph:src_2c2f5faf819cc714:q1:argmin_origin_z_workplane
row:graph:graph:src_2c491af066c68df8:q1:argmax_origin_z_workplane
row:graph:graph:src_2c491af066c68df8:q1:argmin_origin_z_workplane
row:graph:graph:src_33806dac2401d929:q1:argmax_origin_z_workplane
row:graph:graph:src_33806dac2401d929:q1:argmin_origin_z_workplane
row:graph:graph:src_36629229b5ba4373:q1:argmax_origin_z_workplane
row:graph:graph:src_36629229b5ba4373:q1:argmin_origin_z_workplane
row:graph:graph:src_3cbce23163879930:q1:argmax_origin_z_workplane
row:graph:graph:src_3cbce23163879930:q1:argmin_origin_z_workplane
row:graph:graph:src_3dac547343362b42:q1:argmax_origin_z_workplane
row:graph:graph:src_3dac547343362b42:q1:argmin_origin_z_workplane
row:graph:graph:src_6e78359d2d52f77f:q1:argmax_origin_z_workplane
row:graph:graph:src_6e78359d2d52f77f:q1:argmin_origin_z_workplane
row:graph:graph:src_72deb204448950c5:q1:argmax_origin_z_workplane
row:graph:graph:src_72deb204448950c5:q1:argmin_origin_z_workplane
row:graph:graph:src_7f805e6088e4c466:q1:argmax_origin_z_workplane
row:graph:graph:src_7f805e6088e4c466:q1:argmin_origin_z_workplane
row:graph:graph:src_a5c68d8a5dbb5254:q1:argmax_origin_z_workplane
row:graph:graph:src_a5c68d8a5dbb5254:q1:argmin_origin_z_workplane
```

Family split: 11× `argmax_origin_z_workplane` + 11× `argmin_origin_z_workplane`,
all `logical_hop_count=1`, all `answer_format=text`.
