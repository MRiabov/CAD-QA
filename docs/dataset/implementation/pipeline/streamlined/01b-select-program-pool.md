# 01b select program pool — deterministic safety pool

> Authoritative: `../01b-select-program-pool.md`

READ:
- `ProgramMetadata` from `01a` → metadata columns only
- `SelectionPolicy` → `scope, seed, active_count (1500), reserve_count (300-450)`

## 1 — Derive tier and family

TRANSFORM:
- `tier`: `source_subtree == CADEvolve-C` → `C`; `source_subtree == CADEvolve-P` → `P`; any other value → cache-schema failure, recorded; never infer from `source_collection` or `generator_id`
- `cadevolve_program_family_id` from `path_family` only: take the last component, strip a trailing `.py`
- `*-core`: strip a trailing `_<digits>`, lowercase, keep alphanumerics, prefix `cadevolve:`
- ABC: strip a trailing `_trimesh_<digits>`, prefix `abc:` on the remaining mesh identifier
- ShapeNet: keep the last component, prefix `shapenet:`
- empty component or unknown collection → `unknown:<source_id>`; record the fallback

WRITE:
- (none)

## 2 — Select

TRANSFORM:
- scope: C only for P0/P1 (`ABC-C`, `CADEvolve-C-core`, `ShapeNet-C`); P2 adds P as a separate pool sized inside its own tier, never against a combined C+P total
- deduplicate by `normalized_source_code_hash` within each collection; keep the lexicographically smallest `source_id`; record discarded IDs and family conflicts; the survivor's family wins; never deduplicate across collections or across P and C
- hard family cap: at most 2 programs per `cadevolve_program_family_id`
- feature-tag reservation: at least 50 active seats for each of `void_cut`, `kernel_face_selector`, `kernel_edge_selector`, `profile_polyline`, `path_curve`; one program may satisfy several; `kernel_vertex_selector` is diagnostic with no quota
- collection minimum: 300 active per in-scope collection; tag reservations count toward it
- order within each collection by `sha256(seed || source_id)`
- fill remaining active slots proportionally to collection size
- select 1500 active; take the next 300-450 by the same order as reserve
- precedence: scope/dedupe/family cap → hard 1500 cap → tag minima → collection minima → proportional fill
- never exceed 1500; a tag with fewer than 50 eligible after the family cap → select all eligible and record the shortfall; a collection that cannot reach 300 after the family cap, tag reservations, and the hard cap → record the shortfall

WRITE:
- (none)

## 3 — Supplemental delta

TRANSFORM:
- on `ProgramRequest` from `03c`: extend the existing hash order, or target the missing feature tag, collection, or family
- emit a `ProgramSelectionDelta`; never replace or rewrite the original selection
- record request ID, policy version, added IDs, and reason
- a program in an already assigned family inherits its split; a new family is assigned in `03a`

WRITE:
- program selection Parquet `(selection policy version, seed)` → active IDs, reserve IDs, supplemental deltas, `tier`, `cadevolve_program_family_id`, policy, seed, collection counts, family counts, exclusions
- exclusion rows `(source_id)` → `source_id, source_collection, reason`; `reason` is one of `duplicate_hash, family_cap, out_of_scope_tier, not_selected`
- counts reconcile: cache rows = active + reserve + exclusions; an exclusion is not a failure record
- the original selection is immutable; a delta is additive
