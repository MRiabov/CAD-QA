# Task reasoning step support table tests

**Parent:** [`00-testing-strategy.md`](00-testing-strategy.md).

**Contract under test:**
[`../../task-step-support.md`](../../task-step-support.md).

This is the one cross-cutting test in the directory. The support tables are an
observation over the fixture set, not the output of one pipeline stage, so this
contract has no pipeline stage counterpart.

## What is proven

The support table is an observation: it records what the constructor produced
over the coverage fixture set. Two tiers keep it honest at different costs.

| Tier | Proves | Needs CadQuery | Runs |
|---|---|---|---|
| Structural | the table is complete and well-formed | no | every commit |
| Witness | the table is what the constructor actually produces | yes | the generation job |

The structural tier cannot prove that a value is impossible. Under the observed
definition nothing forbids a cell, and a reason code explains an absence rather
than establishing one. The witness tier establishes the table; the structural
tier makes a witness failure readable, because a missing row is a table defect
while a present cell no fixture produces is a missing capability.

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
dimension value and task reasoning step count, with `supported` and
`reason_code`.

It is reviewed like code. A diff claims that a value became supported or
unsupported, and the reviewer asks which fixture changed.

## Tier 1 — structural

No fixtures, no geometry. For every row:

- every value of every dimension at every task reasoning step count in the
  release has a row;
- an absent cell carries a reason code from the closed set in
  `task-step-support.md`;
- `implementation_scope` matches the requirement priority marks;
- the five files share one schema version and one row shape.

A missing row, or an absent cell with no reason, fails. A present cell is not
checked here, because only a fixture can establish one.

## Tier 2 — witness

1. Build the graph for each fixture program. Six programs take seconds, so the
   tier runs without a cache.
2. Run the constructor over each graph for the cells its census claims.
3. Record every cell that produced at least one valid task.
4. Assert that the union of observed cells over the fixture set equals the set of
   expected-present cells.

A cell expected present but not observed names the missing capability and the
fixtures that were tried. A cell expected absent but observed means the table is
stale: the constructor produced that cell, so the expected table is regenerated
and reviewed.

## Fixture growth

When a value is added to the vocabulary, the expected table gains rows. If no
fixture can produce them, the tier 2 failure names the missing capability, and
the fixture set grows by one program. That is the cost of the approach: the
fixture set follows the vocabulary, not the cell count.

## What this does not prove

- That the pool has enough instances. That is a coverage question in `05`
  validate and export release.
- That a value appears in a particular release. That is the coverage check.
- That an in-scope capability is realized by at least one accepted graph. That is
  `extraction_capability_coverage`: this table records what the fixture set can
  construct, and a fixture graph that lost a capability reads as unsupported here.
- That a task is natural or well worded. That is the review gate.
