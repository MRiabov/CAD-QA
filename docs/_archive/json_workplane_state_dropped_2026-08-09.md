# Dropped `json` (workplane_state) rows from `v3_curriculum` — 2026-08-09

## What happened

The 16 `answer_format="json"` rows (`cadqa_workplane_state_*`) were dropped from
HF `MRiabov/cadqa-rl-2000` config `v3_curriculum` and the config was republished
(1445 → 1429 rows). No other format changed.

## Why

The workplane_state golds are degenerate: every row is

```json
{"base": "cq", "coordinate_frame": "cq.Plane(origin=cq.Vector(...), xDir=..., normal=...)", "feature_id": "wpN", "operation": "Workplane"}
```

- `base` is the constant `"cq"` (the creator module) for all 16 rows — zero
  information, exact-match validation, unlearnable by any model (teacher
  guessed `"None"/"new"/"wp26"`; baseline json success 0/113).
- 4/16 rows use named-plane frames (`"XZ"`/`"XY"`) that the grader
  (`_decompose_plane`) cannot even decompose → structurally ungradeable.
- The generator family (`workplane_state` / json answers) was already pruned
  from `cad_qa/` in commit `a0187dd` ("Pruning and re-doing"); the published
  rows were stale artifacts. A validation guard now rejects `answer_format ==
  "json"` (`cad_qa/dataset/validate.py`) so the format cannot be re-emitted.

## Decision

User-approved (2026-08-09): drop the rows rather than regenerate golds;
the numpy compute-tool phase focuses on the remaining formats
(text/candidate_label/coordinate/bbox/integer/number).

## Dropped row_ids (16)

```
cadqa_workplane_state_92d6de2c7efb459d
cadqa_workplane_state_a104206081cfb7cd
cadqa_workplane_state_a49994ed17f41828
cadqa_workplane_state_0835281970cbf949
cadqa_workplane_state_8cf6a2d2061a7008
cadqa_workplane_state_bb460693464198fe
cadqa_workplane_state_0eacc0fffdc5dca6
cadqa_workplane_state_13c13b1e73210387
cadqa_workplane_state_58bfe1fc63607516
cadqa_workplane_state_cd01d0108bcf77fa
cadqa_workplane_state_bca0e179db0b44d6
cadqa_workplane_state_bf8e009fc3ce6d22
cadqa_workplane_state_6b3e8cbec32f70f9
cadqa_workplane_state_99e93dbbc7f47983
cadqa_workplane_state_dbfda07b5a42dbd5
cadqa_workplane_state_54ae2185e6dbcea7
```

## Downstream impact

- `submit_workplane` / `_json_matches` stay in the tool contract (harmless,
  unit-tested); the dataset simply has no json rows anymore.
- Consumers that pin `v3_curriculum` to an old snapshot commit keep working
  (HF snapshots are immutable); fresh loads get the clean set.
