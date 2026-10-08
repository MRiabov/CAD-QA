# Don't-say sweep worklist

**Throwaway.** Working list for the D2 docs sweep. Not part of the canonical tree; not
linted. Regenerate:

```bash
uv run python tools/check_dont_say.py --roots docs --quiet
```

As of 2026-10-08 the checker reports **447 hits** across the canonical docs. The blanket
ban list is fresh, so the count is expected to fall as covering rules and rewrites land.

## By Don't-say term

| Term | Hits | Notes |
|---|---|---|
| model | 119 | bare word; mostly generic "the model" — needs covering or a narrower Say |
| source | 82 | bare word; "open-source", "source material", stage name "source ingestion" |
| trace | 72 | bare word; **false-positives on the Say term "Trace snapshot"** |
| verifier | 33 | covered by "Query verifier" only when qualified |
| ontology | 28 | covered by "CAD ontology" when qualified |
| selector | 18 | covered by "CadQuery selector" when qualified |
| CADEvolve | 16 | proper noun; rephrase in prose |
| clause | 15 | rename to "Query clause" |
| quarantine | 13 | rename to "Non-release-ready row" |
| ontology graph | 10 | covered by "CAD ontology graph" when qualified |
| snapshot | 9 | rename to "Trace snapshot" |
| the pipeline / the object / the value | 8 | unspecific placeholders |
| workplane | 5 | covered by "CadQuery workplane" when qualified |
| profile | 4 | covered by "CadQuery profile" when qualified |
| public row / private row | 6 | qualify |
| query program | 2 | covered by "Gold query program" when qualified |
| node | 2 | qualify |
| candidate trace | 2 | rename to "Candidate-set trace" |
| hop count | 1 | covered by "Reasoning hop count" |
| difficulty bucket | 1 | rename to "Difficulty tier" |

## By file (top)

| File | Hits |
|---|---|
| `docs/dataset/pipeline/03-ontology-graph.md` | 43 |
| `docs/evaluation/harness.md` | 41 |
| `docs/evaluation/baselines.md` | 33 |
| `docs/dataset/pipeline/02-trace-snapshot.md` | 32 |
| `docs/dataset/pipeline/01-source-ingestion.md` | 26 |
| `docs/dataset/pipeline/00-overview.md` | 26 |
| `docs/dataset/decisions.md` | 23 |
| `docs/dataset/requirements.md` | 19 |
| `docs/dataset/pipeline/06-materialize-validate-release.md` | 18 |
| `docs/dataset/pipeline/05-prompt-rendering.md` | 17 |
| `docs/PRD.md` | 14 |
| `docs/fine-tuning/pipeline/02-teacher-sampling.md` | 14 |

## Findings before the sweep can go green

1. **Bare-word bans need covering or an allowlist.** `model`, `source`, `trace`, `node`
   have many legitimate generic uses ("open-source", "the base model", "source material").
   Left as-is the ban is unreachable. Two options: extend each Say cell to enumerate the
   qualified alternatives, or add a checker allowlist (product-launch precedent:
   `ALLOWLISTED`).
2. **A Say term can trip its own ban.** `Trace snapshot` contains the banned `trace`; the
   `trace (bare)` rule's Say must list `Trace snapshot` (or the checker must accept a
   qualified capitalised form). Same risk for `model`, `ontology`.
3. **Frozen code is not scanned.** `dataset_generation/` keeps its identifiers (`In code:`);
   only docs are scanned today. `fine_tuning/` scanning is a follow-up.

## Sweep order (proposed)

1. Unambiguous renames, low risk: CADEvolve, clause, quarantine, snapshot, difficulty
   bucket, candidate trace, public/private row, hop count.
2. Covering/allowlist for the qualified terms (selector, workplane, profile, ontology,
   verifier, query program) so the checker stops flagging correct usage.
3. Bare-word pass (model, source, trace, node, the pipeline/object/value) — the judgement
   call; needs owner input on the Say.
