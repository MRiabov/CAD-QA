# Task reasoning step support table tests

**Parent:** [`README.md`](README.md).

**Contract under test:**
[`../../task-step-support.md`](../../task-step-support.md).

## What is proven

The support table claims that a value can appear at a task reasoning step count.
Two tiers prove different halves of that claim, at different costs.

| Tier | Proves | Needs CadQuery | Runs |
|---|---|---|---|
| Structural | every absent cell has a forbidding rule; every present cell is not forbidden | no | every commit |
| Witness | every present cell is constructible from a real graph | yes | the generation job |

A witness proves possible. A rule proves impossible. Neither alone is enough, so
the table is checked by both.

## Fixtures

A fixture is a **program**, not a graph:

- committed under [`fixtures/`](fixtures/) as program text plus its
  `program_sha256`; the hash is checked, so an edited fixture fails;
- chosen from the pinned pool for a capability it exercises: several solid
  states, a pair relation, a CadQuery profile, a CadQuery workplane, and a
  feature-added region. One program may cover several capabilities;
- representative, not degenerate. A solid built only to make one cell true is not
  a fixture.

The graph is derived, never committed: `02a` extract CadQuery AST, `02b` execute
CadQuery, `02c` build CAD graph, written to a temporary directory. No Parquet
enters the repository, and there is no cache to key or evict.

## Expected table

`pipeline/testing/support-table.json` is the checked-in expected table: one row per
dimension value and task reasoning step count, with `structurally_supported` and
`reason_code`.

It is reviewed like code. A diff claims that a value became possible or
impossible, and the reviewer asks which fixture or rule changed.

## Tier 1 — structural

No fixtures, no geometry. For every row:

- a present cell must not match a forbidding rule;
- an absent cell must carry a reason code from the closed set in
  `task-step-support.md`;
- `implementation_scope` must match the requirement priority marks;
- the row set must be complete: every value of every dimension at every task
  reasoning step count in the release.

A forbidden cell marked present, or an absent cell with no reason, fails.

## Tier 2 — witness

1. Build the graph for each fixture program. Six programs take seconds, so the
   tier runs without a cache.
2. Run the constructor over each graph for the cells its census claims.
3. Record every cell that produced at least one valid task.
4. Assert that the union of observed cells over the fixture set equals the set of
   expected-present cells.

A cell expected present but not observed names the missing capability and the
fixtures that were tried. A cell expected absent but observed is a contradiction:
either the forbidding rule is wrong or a fixture is degenerate.

## Fixture growth

When a value is added to the vocabulary, the expected table gains rows. If no
fixture can produce them, the tier 2 failure names the missing capability, and
the fixture set grows by one program. That is the cost of the approach: the
fixture set follows the vocabulary, not the cell count.

## What this does not prove

- That the pool has enough instances. That is a coverage question in `05`
  validate and export release.
- That a value appears in a particular release. That is the coverage check.
- That a task is natural or well worded. That is the review gate.
