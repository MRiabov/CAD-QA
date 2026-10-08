# Term audit (owner review)

**Throwaway.** Working list from the owner's read of `docs/glossary.md` (2026-10-07; in
progress — the owner is partway through). Per the ubiquitous-language rule, a proposed term
does not land in `docs/glossary.md` until the owner approves it. Renames apply to docs; the
frozen `dataset_generation` code keeps its identifiers (`In code:`).

**Applied 2026-10-07:** the qualified terms are now the glossary's Say terms, and every
flagged bare term is in its *Don't say* table. The docs sweep (replace don't-say usage in
all docs until the checkers are green) is still pending; it needs the Don't-say checker
(D8).

## Principles (proposed)

1. **Qualify every Domain term** with its domain: `CAD-QA`, `CAD`, `CadQuery`, or the owning
   concept. A bare common English noun (`source`, `snapshot`, `selector`) is opaque.
2. **Capitalize Domain terms** (Title case, like placis). The glossary is the naming
   authority; code conforms, not the reverse.
3. **No proper nouns as terms.** `CADEvolve` is a corpus name; name it in prose.
4. **Enums are closed sets** and live under `## Enums`.

## Flagged (owner, in progress)

| # | Current | Problem | Proposed |
|---|---|---|---|
| 1 | source | "source" of what? bare noun | **CadQuery program** |
| 2 | snapshot | opaque; which assignment? why "measured"? | **trace snapshot** |
| 3 | CADEvolve | proper noun, not a concept | remove from glossary |
| 4 | ontology graph | unqualified | **CAD ontology graph** |
| 5 | ontology (used bare) | generic/overloaded | always **CAD ontology** |
| 6 | selector | CadQuery-specific | **CadQuery selector** |
| 7 | workplane | CadQuery-specific | **CadQuery workplane** |
| 8 | profile | generic | **CadQuery profile** |
| 9 | material region / void region | unclear | **added-material region** / **removed-material region** |
| 10 | dataset row | which dataset? | **CAD-QA dataset row** |
| 11 | public row | qualify | **public CAD-QA dataset row** |
| 12 | private row | qualify | **private CAD-QA dataset row** |
| 13 | query program | conflates with gold; "program" | **gold query program** |
| 14 | clause | incoherent; why "clause"? | **query clause** |
| 15 | public clue (in `clause`) | wrong word | **public clue** (a rendered clue sentence) |
| 16 | candidate trace | candidate to what? | **candidate-set trace** |
| 17 | hop count | unqualified | **reasoning hop count** |
| 18 | difficulty bucket | "bucket" imprecise | **difficulty tier** |
| 19 | verifier | unqualified | **query verifier** |
| 20 | quarantine | imprecise plain word | **non-release-ready row** |
| 21 | all terms | lowercased | capitalize Domain terms |

## Clarifications to write into the glossary

- **public row / private row.** A row is one dataset record (one question instance); its
  fields are the columns. "Public" and "private" are two visibility views of the same row
  (answer-free input vs verifier key). Qualify both as above.
- **query program.** It is the hidden query whose result is the gold; name it
  **gold query program**, not a general "query program".
- **verifier.** It does two things — decide uniqueness and compute the gold. Decide whether
  that is one concept (**query verifier**) or two.

## Open questions (owner)

- Keep going through the rest of the glossary; add rows here as flagged.
- After the full pass: approve the rename set, then apply to `docs/glossary.md` and to the
  docs that use the terms (not to the frozen code).
