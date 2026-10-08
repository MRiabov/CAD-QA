# Don't-say sweep worklist

**Throwaway.** Working list for the D2 docs sweep. Not part of the canonical tree; not
linted. Regenerate:

```bash
uv run python tools/check_dont_say.py --roots docs --quiet
```

As of 2026-10-08 the checker reports **357 hits** across the canonical docs. The blanket ban
list is fresh, so the count is expected to fall as covering rules and rewrites land.
(447 → 357 after the checker learned to skip inline/fenced code: `cad_qa/trace.py::…` and
`` `TraceRecord` `` are code, not prose.)

## By Don't-say term

| Term | Hits | Notes |
|---|---|---|
| model | 107 | bare word; mostly generic "the model" — needs covering or a narrower Say |
| source | 65 | bare word; "open-source", "source material", stage name "source ingestion" |
| trace | 44 | bare word; headings ("Trace / snapshot"), prose, code paths now skipped |
| verifier | 31 | covered by "Query verifier" only when qualified |
| selector | 18 | covered by "CadQuery selector" when qualified |
| clause | 13 | rename to "Query clause" |
| CADEvolve | 13 | proper noun; rephrase in prose |
| ontology | 12 | covered by "CAD ontology" when qualified |
| snapshot | 8 | rename to "Trace snapshot" |
| quarantine | 8 | rename to "Non-release-ready row" |
| ontology graph | 8 | covered by "CAD ontology graph" when qualified |
| the pipeline | 6 | unspecific placeholder |
| workplane | 5 | covered by "CadQuery workplane" when qualified |
| profile | 4 | covered by "CadQuery profile" when qualified |
| public row / private row | 6 | qualify |
| query program | 2 | covered by "Gold query program" when qualified |
| candidate trace | 2 | rename to "Candidate-set trace" |
| node, hop count, difficulty bucket, the value, the object | 5 | one each |

## By file (top)

| File | Hits |
|---|---|
| `docs/evaluation/harness.md` | 40 |
| `docs/evaluation/baselines.md` | 33 |
| `docs/dataset/pipeline/03-ontology-graph.md` | 28 |
| `docs/dataset/pipeline/02-trace-snapshot.md` | 20 |
| `docs/dataset/decisions.md` | 19 |
| `docs/dataset/requirements.md` | 18 |
| `docs/dataset/pipeline/01-source-ingestion.md` | 18 |
| `docs/dataset/pipeline/05-prompt-rendering.md` | 16 |
| `docs/dataset/pipeline/06-materialize-validate-release.md` | 15 |
| `docs/PRD.md` | 14 |
| `docs/fine-tuning/pipeline/02-teacher-sampling.md` | 12 |

## Findings before the sweep can go green

1. **Bare-word bans need covering or an allowlist.** `model`, `source`, `trace`, `node`
   have many legitimate generic uses ("open-source", "the base model", "source material").
   Left as-is the ban is unreachable. Two options: extend each Say cell to enumerate the
   qualified alternatives, or add a checker allowlist (product-launch precedent:
   `ALLOWLISTED`).
2. **Fixed:** a Say term could trip its own ban (`Trace snapshot` contained banned `trace`);
   `Trace snapshot` was added to the `trace (bare)` Say cell.
3. **Fixed:** the checker skipped no code; it now ignores inline code spans and fenced
   blocks, so `path::symbol` references and backticked identifiers do not trip the ban.
4. **Frozen code is not scanned.** `dataset_generation/` keeps its identifiers (`In code:`);
   only docs are scanned today. `fine_tuning/` scanning is a follow-up.

## Sweep order (proposed)

1. Unambiguous renames, low risk: CADEvolve, clause, quarantine, snapshot, difficulty
   bucket, candidate trace, public/private row, hop count.
2. Covering/allowlist for the qualified terms (selector, workplane, profile, ontology,
   verifier, query program) so the checker stops flagging correct usage.
3. Bare-word pass (model, source, trace, node, the pipeline/object/value) — the judgement
   call; needs owner input on the Say.
