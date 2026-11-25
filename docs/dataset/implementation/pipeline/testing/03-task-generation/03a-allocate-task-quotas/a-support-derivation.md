# 03a/a support derivation — test contract

**Parent:** [`README.md`](README.md).

**Contract under test:**
[`../../../03-task-generation/03a-allocate-task-quotas/a-support-derivation.md`](../../../03-task-generation/03a-allocate-task-quotas/a-support-derivation.md),
with the census in
[`../../../03-task-generation/algorithm/program-capability-census.md`](../../../03-task-generation/algorithm/program-capability-census.md).

## Tests

`test_03a_census_is_not_re_derived_on_a_fast_replan` — the test mutates the
graphs after the first plan, then replans in the fast loop. `family_profiles`
and `program_census` keep their first values, because the graph batch did not
change. A slow round that adds one program to one new family adds only that
family's profile and leaves the others byte-identical.

`test_03a_census_entry_is_keyed_by_graph_hash` — a program whose `graph_identity_sha256`
changes gets a new census entry; a program whose hash is unchanged keeps its
entry. `03b` reads the entry instead of deriving the census again, and a stale
entry is not used.

`test_03a_support_values_come_from_the_derivation` — the plan uses the
`supported_values` the support-table derivation returns for the implementation
scope, not a scope file or a second grammar typed model. A value above the release
scope has no quota target.

`test_03a_scope_outlives_the_corpus` — an in-scope value whose capability no
accepted graph realizes keeps its supported row and its quota target. The census
and `family_profiles` record the capability as absent, and the missing cell is
the `05` `extraction_capability_coverage` miss, not a `03a` decision. The test
pins that `03a` does not narrow the scope to what the graphs happen to offer.

**TDD pin:** pins census reuse, the graph-hash key, and the single support
derivation before `03a` exists.

## What this does not prove

- That the support tables are correct. That is
  [`../../00-support-tables.md`](../../00-support-tables.md).
