# Don't-say sweep worklist

**Throwaway.** Working list for the D2 docs sweep. Not part of the canonical tree; not
linted. Regenerate:

```bash
tools/ci_cd/dont-say --quiet
```

As of 2026-11-21 the checker reports **53 prose hits** and **0 declared-name hits**.
Every prose hit sits in `docs/train-and-eval/`, stale design input for the deleted
training stack, and stays in the baseline until the rewrite replaces it. Dated plans
and audits, and the verbatim supervisor correspondence, carry `dont-say: allow-file`
and are excluded as historical records. The name ratchet replaced the old
`--identifiers` count of 5,339: that count matched every identifier occurrence, while
the name ratchet matches only declarations (class, function, method, parameter,
variable, field, type, constant, file, folder) and skips attribute reads.

As of 2026-10-08 the checker reported **358 hits**, all in `docs/`. Code is clean: the
identifier-shaped Don't-says that appear in code (`OntologyGraph`, `entity_id`,
`QueryProgram`, `hop_count`, `void_region`, `difficulty_bucket`, …) are documented
`In code:` names and are exempted per tree with `(cad_qa)`-style annotations. 447 → 357
(after skipping inline/fenced code) → 353 (after the `(home)` annotations) → 361 (after
adding the bare `kind`/`type` bans).

## Mechanism (ported from product-launch / placis)

- **`(home)` annotation** on a Don't-say term exempts it under that tree (`cad_qa`,
  `train_and_eval`, `tools`, `docs`, `dataset_generation`, `fine_tuning`).
- **`ALLOWLIST`** in `tools/ci_cd/dont_say_rules.py` exempts cross-cutting phrases
  (`open-source`, `source of truth`, …).
- **`<!-- dont-say: allow -->`** exempts a line; `<!-- dont-say: allow-file -->` in the
  file header exempts a historical record or verbatim text; `# dont-say: home` exempts a code
  file.
- **Say-term covering**: a Say term covers its own Don't-say tokens.
- **Code**: every declared name, matched by word segments (snake/kebab/Pascal/camel), so
  `query_program`, `QueryProgram`, and `query-program` all match. Bare terms need a
  qualifier (`clue_type` is clean, `get_type` is a hit). Attribute reads and string
  values are not names, so `token.type` and `"selector"` are not flagged.
- **Go**: syntax comes from `tools/dont-say-go` (`go/parser`), which also reports comment
  lines as prose. The checker never guesses at Go syntax.
- **Ratchets**: `tools/ci_cd/dont_say_baseline.txt` counts prose hits and
  `tools/ci_cd/dont_say_names_baseline.txt` counts declared-name hits; the checker fails if
  either rises, or if either falls without the baseline being lowered. Enforced by the
  `dont-say` pre-commit hook (`tools/ci_cd/dont-say`), not by pytest: the check is a
  whole-repository scan, so a test would pay for it on every test run.

## By Don't-say term

The table below is the 2026-10-08 breakdown, kept as history; the current count is 53
prose hits and 0 declared-name hits.

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
