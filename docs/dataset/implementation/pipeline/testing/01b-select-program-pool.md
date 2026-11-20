# 01b select program pool — adversarial integration test (TDD)

**Parent:** [`00-testing-strategy.md`](00-testing-strategy.md).

**Contract under test:** [`../01b-select-program-pool.md`](../01b-select-program-pool.md).

## Happy-path integration test (test-first, adversarial)

`test_01b_selection_happy_path_adversarial` — selects from a metadata fixture and
asserts the persisted selection artifact read back through the reader `01c` fetch
program pool uses.

**Given** a `ProgramMetadata` fixture and a `SelectionPolicy` with small numbers,
so the fixture stays readable: active count 6, reserve 2, family cap 2,
collection minimum 3, feature-tag minimum 1, in-scope tier `C`. The rows are:

- `ABC-C`: `a1` and `a2` with `void_cut`, `a3` with `void_cut` and `path_curve`,
  `a4` with the same `normalized_source_code_hash` as `a3`, and `a5` with
  `kernel_face_selector`;
- `CADEvolve-C-core`: `c1`, `c2`, and `c3`, one `cadevolve_program_family_id`;
- `ShapeNet-C`: `s1` and `s2`;
- `ABC-P`: `p1`.

**When** `01b` selects with a fixed seed.

**Then** assert the persisted selection:

- `a4` is excluded as `duplicate_hash` and `a3` survives, because `a3` is the
  lexicographically smaller `source_id`;
- `c3` is excluded as `family_cap`, and `c1` and `c2` survive;
- `p1` is excluded as `out_of_scope_tier`;
- `CADEvolve-C-core` reaches 2 active programs against a minimum of 3, and the
  shortfall is recorded against that collection;
- active has 6 programs and reserve has 2, they are disjoint, and their union is
  the eligible set: `a1`, `a2`, `a3`, `a5`, `c1`, `c2`, `s1`, `s2`;
- within each collection, the reserve programs are the next ones after the active
  allocation under `sha256(seed || source_id)`, recomputed by the test, not read
  from the artifact;
- the rows reconcile: 11 cache rows equal 6 active, plus 2 reserve, plus 3
  exclusions;
- every selected row carries `tier` and `cadevolve_program_family_id`, and the
  artifact records `policy_version`, `seed`, and the policy it applied;
- no failure record is written for an excluded program.

`test_01b_dedup_scope` — the same hash twice in one collection keeps the smaller
`source_id` and records the discarded ID. The same hash in two collections keeps
both: the rule deduplicates within a collection, never across collections and
never across the two tiers.

`test_01b_family_cap_and_span` — four rows in one family yield two active
programs and two exclusions that name the family. The family still supplies
reserve rows, because the cap counts active programs only. A duplicate group
whose members carry different families keeps the survivor's family and records
the conflict.

`test_01b_tag_minimum_counts_every_tag` — `a3` counts toward both `void_cut` and
`path_curve`. A tag with fewer eligible programs than its minimum selects all of
them and records the shortfall, and it does not push active past the hard cap. A
`kernel_vertex_selector` row is selected only by hash order: the tag is
diagnostic and carries no minimum.

`test_01b_tier_and_family_derivation` — one table drives both derivations. `tier`
comes from `source_subtree` and from nothing else: a CADEvolve-C row whose
collection name says otherwise still derives `C`. `cadevolve_program_family_id`
comes from `path_family` for the four naming rules and the empty-component
fallback `unknown:<source_id>`; two rows whose `path_family` differs only in the
`_<digits>` sample suffix derive the same family, and so do a P and a C row of
one generator.

`test_01b_supplemental_delta` — an extend request continues the hash order beyond
the reserve set; a target request selects by missing feature tag. The delta
records the request ID, the policy version, the added IDs, and the reason. The
original selection is unchanged after both. A program whose family is already
assigned inherits its split, and the delta adds no split for a new family.

**TDD pin:** pins the four exclusion reasons and the reconciliation, the
within-collection deduplication scope, the family cap, the tag and collection
shortfall records, both derivations, and the reserve position under hash order
before `01b` exists.

## Failure-mode tests

- `test_01b_unknown_tier_value` — a `source_subtree` outside `CADEvolve-C` and
  `CADEvolve-P` fails as a cache-schema failure naming the row, and no selection
  artifact is written.
- `test_01b_shortfall_is_recorded_not_fatal` — a pool smaller than the active
  count selects everything, records the shortfall, and writes no failure record.
  Failing the run below 1,000 usable programs is `01c`'s decision.
- `test_01b_targets_never_exceed_the_cap` — collection minima that sum above the
  active count leave active at the cap and record each shortfall; the hard cap is
  never exceeded to satisfy a lower-priority target.
- `test_01b_policy_and_seed_change_the_result` — a changed seed changes the
  reserve position but not the eligible set; a changed policy version changes the
  artifact identity and the recorded policy.

## What this does not prove

- That the selected rows exist in the cache. That is
  `01c-fetch-program-pool.md`.
- That the selected text normalizes. That is `01d-normalize-programs.md`.
- That a family is split correctly. That is `03a-allocate-task-quotas.md`.
