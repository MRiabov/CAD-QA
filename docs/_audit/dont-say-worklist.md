# Don't-say sweep worklist

**Throwaway.** Working list for the D2 docs sweep. Not part of the canonical tree; not
linted. Regenerate:

```bash
tools/dont-say --quiet
```

As of 2026-11-21 the checker reports **177 hits** against a baseline re-pinned at 177:
103 in `plans/` (dated decision records) and 74 in `docs/`. The 2026-10-21 baseline of 107
went stale while the docs tree was restructured, and the pytest ratchet was red from
2026-11-20 until the check moved to the `dont-say` pre-commit hook.

As of 2026-10-08 the checker reports **358 hits**, all in `docs/`. Code is clean: the
identifier-shaped Don't-says that appear in code (`OntologyGraph`, `entity_id`,
`QueryProgram`, `hop_count`, `void_region`, `difficulty_bucket`, …) are documented
`In code:` names and are exempted per tree with `(cad_qa)`-style annotations. 447 → 357
(after skipping inline/fenced code) → 353 (after the `(home)` annotations) → 361 (after
adding the bare `kind`/`type` bans).

## Mechanism (ported from product-launch / placis)

- **`(home)` annotation** on a Don't-say term exempts it under that tree (`cad_qa`,
  `train_and_eval`, `tools`, `docs`, `dataset_generation`, `fine_tuning`).
- **`ALLOWLIST`** in `tools/check_dont_say.py` exempts cross-cutting phrases
  (`open-source`, `source of truth`, …).
- **`<!-- dont-say: allow -->`** exempts a line; `# dont-say: home` exempts a code file.
- **Say-term covering**: a Say term covers its own Don't-say tokens.
- **Code**: identifier-shaped tokens only (snake/kebab/Pascal/camel); bare words are
  prose-only, so legit string values like `"selector"` are not flagged.
- **Ratchet**: `tools/dont_say_baseline.txt` holds the accepted count; the checker fails if
  hits rise, or if they fall without the baseline being lowered. Enforced by the
  `dont-say` pre-commit hook (`tools/dont-say`), not by pytest: the check is a
  whole-repository scan, so a test would pay for it on every test run.

## By Don't-say term

| Term | Hits | Notes |
|---|---|---|
| model | 107 | bare word; mostly generic "the model" — needs covering or a narrower Say |
| source | 61 | bare word; "open-source" is allowlisted; stage name "source ingestion" |
| trace | 44 | bare word; headings ("Trace / snapshot") and prose |
| verifier | 31 | covered by "Query verifier" only when qualified |
| selector | 18 | covered by "CadQuery selector" when qualified |
| clause | 13 | rename to "Gold query predicate" |
| CADEvolve | 13 | proper noun; rephrase in prose |
| ontology | 12 | covered by "CAD ontology" when qualified |
| snapshot | 8 | rename to "Trace snapshot" |
| quarantine | 8 | rename to "Non-release-ready row" |
| ontology graph | 8 | covered by "CAD ontology graph" when qualified |
| the pipeline | 6 | unspecific placeholder |
| workplane, profile, public/private row, query program, candidate trace | 22 | qualifying/rename |
| node, hop count, difficulty bucket, the value, the object | 5 | one each |
| kind / kinds | 3 | raw noun; say "predicate kind" |
| type / types | 5 | raw noun; qualify (node type, relation type, answer format, …) |

## By file (top)

| File | Hits |
|---|---|
| `docs/evaluation/harness.md` | 39 |
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

## Remaining decision

Bare-word bans (`model`, `source`, `trace`, `node`) still match legitimate generic prose.
Options: add covering phrases to each Say cell, or grow `ALLOWLIST`. That is the owner's
terminology call and the last blocker before the sweep can reach zero.

## Sweep order (proposed)

1. Unambiguous renames: CADEvolve, clause, quarantine, snapshot, difficulty bucket,
   candidate trace, public/private row, hop count.
2. Covering/allowlist for the qualified terms (selector, workplane, profile, ontology,
   verifier, query program).
3. Bare-word pass (model, source, trace, node, the pipeline/object/value).
