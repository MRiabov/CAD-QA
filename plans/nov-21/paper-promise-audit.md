# Paper promise audit — 2026-11-21
<!-- dont-say: allow-file: point-in-time audit; findings are quoted and not rewritten -->

**Status:** audit, 2026-11-21. Snapshot: `c8fa379` (`docs: add dataset
architecture audit (#2)`).

**Scope:** the promises in `docs/paper/CA2_Riabov_final.md` (the `.tex` is
parity-kept), checked against the project PRD, the dataset PRD and requirements,
the release contract, the dataset decisions, and the train-and-eval docs. This is
a review document, not a source of truth. It does not change the paper or an
owner document.

**Question:** for every promise in the paper, is it (a) planned in the PRD, and
(b) delivered in the docs?

**Verdict:** the dataset core is planned and largely documented. The paper's
*scope* is not. The paper reads as a 0–10-hop, three-harness, exhaustive-ontology
benchmark with entity-reference answers and rich distractors. The current
requirements describe a 1–5-step, NumPy-primary, P0 graph-vocabulary benchmark
with multiple-choice identity answers and P2 near-miss distractors. The paper is
written against the pre-rebuild spec (`specs/paper-spec.md`) and has not been
narrowed to the rebuilt dataset. Eight claims are direct contradictions, not
just priority differences.

The known missing evaluation contract is not counted as a finding. One schema
gap is separate from it and is counted: the PRD asks for accuracy by relation
family and measurement scope, but the release contract carries neither field.

## Method

- Read the paper, `docs/PRD.md`, `docs/dataset/requirements/*`,
  `docs/dataset/decisions.md`, the release contract, `docs/train-and-eval/*`, the
  glossary, `docs/development-plan.md`, and `specs/paper-spec.md`.
- Classified each promise as **aligned**, **partial** (planned P1/P2 or
  narrower), **contradicted**, **stale**, or **known gap**.
- "Delivered" means "specified in the current docs". The dataset docs are
  requirements and implementation docs, not a built release; code status is
  noted only where the docs state it.

## Summary

| # | Paper promise | Paper | Planned in PRD/requirements? | Specified in docs? | Status |
|---|---|---|---|---|---|
| 1 | Dataset built from CadQuery/CADEvolve programs; AST plus runtime extraction; offline precomputed tabular release | 12–16, 137–178 | Yes, P0 (`PRD.md:9–12, 105–112`; dataset PRD 92–100) | Yes (`graph-content.md`, `release-dataset-contract.md`) | Aligned |
| 2 | Questions about faces, edges, vertices, boolean operations, volume, span, location | 12–16, 197–213 | Yes (`dataset PRD:27–40`) | Yes (`task-structure.md:38–56, 147–163`) | Aligned |
| 3 | 0–10 reasoning hops; 0/1/2/3–10 taxonomy | 107, 129, 215–220 | No: release is 1–5 P0, 6+ P2; 0/1 not generated (`PRD.md:56, 72`; dataset PRD 195–220) | No: no 0-step; release floors at 2 (`task-structure.md:193`; `DS-REQ-11`; `data.md:382–388`) | Contradicted |
| 4 | Rich distractors | 15–16, 220 | Only P2 near-miss (`dataset PRD:188–191`; `DS-REQ-25`) | P0 requires real candidates, not padding (`prompt-content.md:141–149`) | Partial |
| 5 | Three harnesses: `no_tools`, `numpy`, `cadquery` | 17, 248–264 | `numpy` P0; `no_tools` and `cadquery` P2 (`PRD.md:90–93`) | `numpy` exists; `no_tools` exists; `cadquery` missing (`harness.md:59–80, 162–179`) | Partial |
| 6 | Harbor/TerminalBench environments; answers submitted as files | 264 | Not in PRD; Harbor deferred P2 (`harness.md:3–5, 98–119, 154–160`) | Harbor exists but is unverified and deferred | Partial |
| 7 | Accuracy by hop, task family, and harness mode | 17 | Hop, relation family, measurement scope; no task family (`PRD.md:99–101`) | No task families (`task-structure.md:195–205`; `DS-REQ-03`) | Contradicted |
| 8 | Entity-reference answers (`wp3`, `feature:wp3`, …) | 182–184 | No: the variable-name answer format is removed (`dataset PRD:170–191`; `DS-REQ-05`) | Identity answers are multiple choice (`task-structure.md:149, 174`; `DS-REQ-05`) | Contradicted |
| 9 | Enum answers: coordinate frames, `inside`/`outside`/`on_boundary`/`ambiguous`, selector labels | 191–193 | No separate enum format; membership is yes/no; boundary and ambiguity are excluded (`dataset PRD:170–191`; `task-structure.md:157`; `release-dataset-contract.md:330`) | Workplane state is P1 structured object; selector result is P1 | Contradicted |
| 10 | Structured JSON: bounding box and workplane-state snapshot | 194–195 | Bounding box P0; workplane state P1 (`task-structure.md:134, 160`) | Bounding box P0; structured object P1 | Partial |
| 11 | Validity booleans | 190 | Validity P2 (`task-structure.md:163`) | P2 | Partial |
| 12 | Exhaustive CAD ontology with the listed nodes and relations | 197–213 | No: the graph is "at least" and not a full dump (`graph-content.md:28–46, 76–129, 305–319`) | P0/P1/P2 subset; many relations are absent | Contradicted |
| 13 | Measurement scopes | 206–209 | Yes (PRD metric `PRD.md:99–101`; glossary defines it) | Defined (`glossary.md:437–445`); not a release column | Partial |
| 14 | Unique-target classifiers (2nd highest on Y, lowest on X) | 211 | Aggregation and rank are P1 (`task-structure.md:85, 156`) | P1; no geometric tie-break rule is specified | Partial |
| 15 | Curriculum and warmup | 58, 215–220 | Dataset PRD says 1-step warmup P0 (`200–220, 311–329`), but the project PRD says 0/1-hop is not generated (`56`); training docs floor at 2 (`data.md:382–388`) | Contradictory | Contradicted |
| 16 | Graphs are provided; critical path; conciseness training | 57 | Conciseness is deferred (`PRD.md:65`); the PRD also says the dataset exposes the critical path (`71`) | Release ships answer evidence only; no graph or candidate-set trace (`release-dataset-contract.md:82–106`) | Partial |
| 17 | SFT then RL; rejection sampling; trace editing | 228–246 | SFT P0, GRPO P1 (`PRD.md:62–65`; `development-plan.md:71–81`) | Yes (`train-and-eval/fine-tuning/*`); `compact_trace` is defined | Aligned |
| 18 | TRL or Unsloth | 228 | No: LFM2.5 plus `liquid-finetune` (`FT-D11`; `training.md:140`) | Stale | Stale |
| 19 | Base model Gemma4-E2B or Qwen3.5-2B | 230–233 | Small 2–4B (`PRD.md:81`); current base is LFM2.5 (`FT-D11`) | Gemma is superseded; Qwen is not planned | Stale |
| 20 | Cost-effective models: `deepseek-v4-flash`, `xiaomi-mimo-v2.5`, NemoTron super; ≤30%; task families equally distributed | 222–224 | ≤30% is a planning estimate (`PRD.md:94–98`); no task-family balance | Two recorded on rc10 0-hop; NemoTron missing; hard slice unrecorded (`baselines.md:60–80, 153–156`) | Partial |
| 21 | P0 improvement over base plus format/answer-only; P1 BenchCAD `qa_code`; P2 teacher-surpass | 236–242 | Yes (`PRD.md:34–41, 62–65`) | Yes (`evaluation/plan.md`; `training.md:78`) | Aligned |
| 22 | Exact-match grading | 129 | Numeric tolerance (`release-dataset-contract.md:103, 170–172`) | Not exact for numbers | Contradicted |
| 23 | Flagship example: Z difference between topmost vertices | 137–175 | R-2 uniqueness (`dataset PRD:231`) | No "Z difference" answer meaning; the cylinder top is a face, not a unique vertex | Contradicted |
| 24 | Ethical: no risks expected | 266–269 | — | License and attribution are open (`DA-9`) | Partial |

## Abstract-level mismatches

The abstract is the most visible mismatch. It promises a different benchmark
from the one the current docs specify.

- **"Questions range from simple lookups to challenging high reasoning hop
  questions with rich distractors"** (`paper:15–16`). The release is 1–5 task
  reasoning steps (P0), 6+ is P2, and rich near-miss distractors are P2
  (`dataset PRD:195–220, 311–329`; `DS-REQ-25`). The 0-hop and 1-hop tiers are not
  generated for the release: the project PRD says "0/1-hop — not generated
  (synthesis floors at `hop≥2`)" (`PRD.md:56`), and the training docs say the
  graph-first release has no 0/1-hop rows (`data.md:382–388`).
- **"We evaluate open-source LLMs in three harnesses"** (`paper:17`). Only the
  `numpy` harness is P0; `no_tools` and `cadquery` are P2, and `cadquery` is
  unimplemented (`PRD.md:90–93`; `harness.md:59–80, 162–179`).
- **"measuring accuracy by reasoning hop count, task family, and LLM harness
  mode"** (`paper:17`). The PRD measures by hop, relation family, and
  measurement scope (`PRD.md:99–101`). The dataset explicitly has no task
  families (`task-structure.md:195–205`; `DS-REQ-03`). "Task family" is still an
  undefined proposed term (`glossary.md:790`).

The abstract's "multi-hop geometry reasoning gap" claim is aligned. The scope
around it is not.

## Direct contradictions

### 1. The hop range is 0–10 in the paper, 1–5 in the release

**Paper:** "3~10 hops" (`paper:220`), "up to ten" (`paper:107`), and the
comparison table says `0–10` (`paper:129`).

**Docs:** the dataset PRD makes 1–5 the first-release range and 6+ optional P2
(`dataset PRD:195–220`). The project PRD's release ladder is `{2,3,4,5}` and says
0/1-hop is not generated (`PRD.md:56, 72`). The task structure says the lowest
step count is 1 and there are no 0-step tasks (`task-structure.md:193`), and
`DS-REQ-11` records dropping 0-step tasks. The development plan keeps `{2,3,4,5}` as
the working ladder and admits 6–10 only if a selection pilot supports it
(`development-plan.md:55`). The training docs state the release has no 0/1-hop
rows and the resolver floors at 2 (`data.md:382–388`).

**Why it bites:** the paper's headline "up to ten" and its "0-hop / 1-hop"
definitions describe a dataset the release will not contain. The 0-hop example
in the paper is a direct lookup; the current docs fold that into a 1-step answer
step, and the release does not generate it.

**Recommendation:** state the actual ladder, for example "1–5 task reasoning
steps in the first release; 6–10 are P2/aspirational and depend on a selection
pilot". Remove the 0-hop claim or label it as a calibration row outside the
release. Reconcile the dataset PRD's 1-step warmup with the training docs'
floor at 2 before promising a warmup entry point.

### 2. Three harnesses are presented as the method; only one is P0

**Paper:** the abstract says three harnesses (`paper:17`), and §3.4 proposes
`no_tools`, `numpy`, and `cadquery` (`paper:248–264`).

**Docs:** the evaluation contract makes `numpy` primary and the other two P2
upper bounds (`PRD.md:90–93`). The harness doc says `numpy` is P0, `no_tools` is
P2, and `cadquery` is P2 and unimplemented (`harness.md:59–80, 162–179`). The
development plan lists `no_tools`/`cadquery` as P2 (`development-plan.md:63`).

**Why it bites:** a reader expects three-harness results; the first paper can
only produce `numpy` results. The `cadquery` mode is not just deferred; its tool
implementation raises `NotImplementedError`.

**Recommendation:** describe `numpy` as the primary harness and present the other
two as P2 upper bounds. If the paper keeps "three harnesses", say "we define
three modes; the first release evaluates the primary mode and leaves the other
two as P2".

### 3. Entity-reference and enum answer formats are removed or re-scoped

**Paper:** entity references such as `wp3`, `feature:wp3`, `path:wp2:point:6`,
and `selector:sel_all_faces_all` (`paper:182–184`); enums for coordinate frames,
point membership including `on_boundary` and `ambiguous`, and selector labels
(`paper:191–193`); validity booleans (`paper:190`).

**Docs:** `DS-REQ-05` removes the variable-name answer format and makes identity
answers multiple choice (`decisions.md:218–231`). The answer-format table has
multiple choice, number, integer, yes/no, 3D coordinate, bounding box, and
structured object (`task-structure.md:127–135`). Identity is returned as a
multiple-choice label (`task-structure.md:149, 174`). Membership is inside or
outside; a point within the clear-case margin is not used, so "on the boundary"
is never an answer (`release-dataset-contract.md:330`). Workplane state is P1
structured object; validity is P2 (`task-structure.md:160, 163`).

**Why it bites:** the paper's answer-format list is the interface contract. Two
of its entries are not in the current interface (entity references and enums),
and two are narrower than the paper implies (booleans include P2 validity;
structured JSON includes P1 workplane state). The paper's
`on_boundary`/`ambiguous` examples contradict the membership rule. There is also
an internal docs contradiction: `03b` still lists
`on the boundary` in `same_answer` (`03b-construct-task-definitions.md:320`)
while the release contract and the membership section exclude it.

**Recommendation:** replace the paper's list with the current answer-format
table, mark workplane state P1 and validity P2, and remove entity references and
the enum format. If entity references are still wanted, they are a new answer
format and need a decision; they are not a wording change.

### 4. The ontology is presented as exhaustive; the docs define a P0 subset

**Paper:** "We extract this CAD ontology" with a long node and relation list
(`paper:197–213`), and "The goal is to create an exhaustive CAD ontology
extraction" (`paper:213`).

**Docs:** the graph must contain "at least" the listed entities and relations
(`graph-content.md:28–46, 76–129`), and it is explicitly "not a full dump of
every OpenCascade object" and "not a copy of the geometry"
(`graph-content.md:305–319`). The current relation list has `before`, `after`,
`creates`, `uses`,
`derived_from`, the topology relations, `parallel_to`, `perpendicular_to`,
`coplanar_with`, `coaxial_with`, the material-change relations, and the selector
relations. It does not have `input_to`, `combines`, `modified_by`, `deleted_by`,
`parameter_of`, `located_on`, `bounded_by`, `has_centroid`, `has_coordinate`,
`has_normal`, `distance_to`, `nearest_tangent_to`, `not_parallel_to`,
`orthogonal_to`, `opposite_to`, or `contained_in`; `intersects` is explicitly
rejected as a relation (`graph-content.md:111–114`).

Several paper node types are also not graph entities: `parameter`, `axis`,
`direction`, `centroid` (a measurement), and `centerline`. `source` is the
program, `solid` is a solid state, `selector` is a selector result, and
`material_region`/`void_region` are one region entity.

**Why it bites:** the paper's list is copied from `specs/paper-spec.md:81–129`,
which says "start small but use the right ontology shape from the beginning".
The rebuilt docs deliberately narrowed it. A reviewer can check the paper's
relation list against `graph-content.md` and find about half of it absent.

**Recommendation:** present the graph vocabulary as the P0 subset with P1/P2
additions, not as an exhaustive extraction. Remove `intersects` (explicitly not
a relation), and either remove the absent relations or label them P1/P2 future
work.

### 5. Rich distractors are P2, not a P0 property

**Paper:** "rich distractors" (`paper:15–16`) and "distractor-rich clues"
(`paper:220`).

**Docs:** P0 and P1 require real candidates, not padding; plausible near-miss
distractors are P2 (`DS-REQ-25`; `dataset PRD:188–191`; `prompt-content.md:141–149`).
The multiple-choice check requires at least five real candidates from the
penultimate answer set (`03b-construct-task-definitions.md:209–223`), but not
examiner-style near misses.

**Why it bites:** the abstract's difficulty claim rests on distractors that the
first release does not require.

**Recommendation:** say "real candidate choices; plausible near-miss distractors
are P2" or make near-miss distractors a P0 requirement, which is a larger change.

### 6. "Task family" is not a current metric; the docs use relation family and measurement scope

**Paper:** accuracy by "task family" (`paper:17`) and "task families being
equally distributed in solve rates" (`paper:224`).

**Docs:** the dataset does not use task families, task types, or task patterns
(`task-structure.md:195–205`; `DS-REQ-03`). The PRD metrics are accuracy by hop,
relation family, and measurement scope (`PRD.md:99–101`). "Task family" is still
an undefined proposed addition in the glossary (`glossary.md:790`).

**Why it bites:** the paper's evaluation breakdown names a dimension the dataset
does not have. The intended dimension is probably relation family or measurement
scope, but the paper never says so.

**Recommendation:** replace "task family" with "relation family and measurement
scope", or define a task family as a new grouping and add it to the release. Do
not use both terms.

### 7. Graphs and the critical path are not in the release contract

**Paper:** "The dataset can be reused for training of models for conciseness …
as graphs are provided; one can train the LLM to follow the shortest/critical
path necessary to achieve the result" (`paper:57`), and Table 1 says "critical
path" (`paper:129`).

**Docs:** the release contract's required artifacts are `release.parquet`,
`manifest.json`, `dataset-card.md`, `failures.parquet`, and the support tables
(`release-dataset-contract.md:32–40`). The release table carries
`answer_evidence_json` with `evidence_refs` and `answer_equivalent_set`
(`03b:290–305`), but not the CAD graph, the Gold query program, or the
candidate-set trace, so the release has no per-step intermediate answers either.
The old row schema had `query_program`, `candidate_trace`, and `clue_map`; the
new release contract does not.

The project PRD also contradicts itself: it lists "The dataset exposes the
critical reasoning path, so it can also train conciseness" as a contribution
(`PRD.md:71`) and then says "conciseness is deferred to future work"
(`PRD.md:65`).

**Why it bites:** the paper's second contribution and the "critical path" column
in Table 1 are not backed by the consumer contract. A user who downloads the
release does not get the graph or the shortest path, only the answer evidence.

**Recommendation:** decide whether the graph and candidate-set trace are release
artifacts. If yes, add them to the release contract and the manifest. If no,
rewrite the contribution as "the generator retains the derivation path
internally; conciseness training is future work". Resolve the PRD's
contribution-versus-scope contradiction at the same time.

### 8. "Exact match" contradicts the numeric tolerance

**Paper:** Table 1 says "exact match" (`paper:129`); §3.1 says numbers are
"graded to a 4-significant-figure tolerance" (`paper:186`).

**Docs:** `scoring_rule` is `exact`, `numeric_tolerance`, or `structured_exact`
(`release-dataset-contract.md:103`), and a numeric answer has an explicit
tolerance, typically absolute `0.005` (`:170–172`). The answer precision is four
significant figures by default (`:331`).

**Why it bites:** "exact match" is false for numbers and coordinates, and the
paper contradicts itself one page later.

**Recommendation:** say "exact structured-answer accuracy, with numeric answers
graded at the stated tolerance (four significant figures by default)".

### 9. The flagship example is not a valid task under the uniqueness rule

**Paper:** the example asks for the Z difference between "the topmost vertex of
the final part" and "the topmost vertex of the cylinder", and derives
`12 - 5 == 7` (`paper:137–175`).

**Docs:** R-2 requires exactly one correct answer and rejects ties
(`dataset PRD:231`). The task structure rejects a target binding that is not
unique (`task-structure.md:253–254`; `03b:351`).

**Why it is invalid:**

- `wp3` is a cylinder from z=0 to z=5. Its top is a circular face at z=5. A
  smooth cylinder has no unique "topmost vertex"; the circular edge is a curve,
  and any seam vertex is not unique by z.
- `result` is the union of the cylinder and the box. The box top is a 4×3
  rectangle at z=12, so there are four top vertices at z=12. "The topmost vertex"
  is not unique.
- The derivation silently uses the top plane of the cylinder and one of four
  top vertices of the box. That is exactly the tie the paper says it resolves
  with classifiers such as "2nd highest on Y and lowest on X" (`paper:211`), but
  the example does not apply one.
- "Z difference" is not a current answer meaning. The answer meanings are
  identity, volume, area, length, distance, angle, count, rank, membership,
  position, extent, workplane state, material change, topology change, and
  validity (`task-structure.md:147–163`). `distance` is the shortest distance,
  not a signed axis difference (`graph-content.md:144`).

**Recommendation:** change the example to a unique target (for example, "the
top face of the cylinder" and "the top face of the final part") and use a
supported answer meaning, or add "coordinate difference" as an answer meaning
with its own rule. Apply the tie-break the paper already describes. This is a
good example to fix before submission because it is the reader's first concrete
task.

## Paper-internal inconsistency

One claim is wrong regardless of which document wins.

- **No Docker vs Harbor.** §3.1 says the offline tabular layout needs no Docker
  setup (`paper:178`); §3.4 says the evaluation uses Harbor coding environments
  (`paper:264`). Both can be true only if the first sentence is about the
  dataset/release and the second is about a separate Harbor harness. Say which
  harness the claim applies to. The current docs do exactly that: the local
  `numpy` harness is the live one; Harbor is deferred P2 (`harness.md:3–5,
  154–160`).

The other internal inconsistencies are already covered above: "exact match"
versus four-significant-figure tolerance (#8), and the 0–10 range versus the
0/1/2/3–10 taxonomy (#1).

## Planned but not first-release

These are not contradictions; the paper presents them as core, while the docs
make them P1/P2 or defer them.

| Promise | Current status | Evidence |
|---|---|---|
| 6–10 hops | P2/aspirational; depends on a selection pilot | `dataset PRD:206`; `development-plan.md:55` |
| `no_tools` and `cadquery` harnesses | P2; `cadquery` unimplemented | `PRD.md:90–93`; `harness.md:59–80` |
| Harbor/TerminalBench | Deferred P2; end-to-end unverified | `harness.md:3–5, 154–160` |
| Near-miss distractors | P2 | `DS-REQ-25` |
| Workplane-state answer | P1 structured object | `task-structure.md:160` |
| Validity answer | P2 | `task-structure.md:163` |
| Aggregation/rank classifiers | P1 | `task-structure.md:85, 156` |
| Conciseness / critical-path training | Deferred; release does not ship the path | `PRD.md:65`; `release-dataset-contract.md:82–106` |
| 1-step warmup | P0 in the dataset PRD, but contradicted by the release floor at 2 | `dataset PRD:311–329`; `data.md:382–388` |

## Stale details

- **TRL or Unsloth** (`paper:228`). The current stack is LFM2.5 plus
  `liquid-finetune`; the training doc says "Do not write a trainer. Use
  `liquid-finetune` configs" (`training.md:140`; `FT-D11`).
- **Gemma4-E2B or Qwen3.5-2B** (`paper:230–233`). Gemma was the earlier base
  (`FT-D1`); `FT-D11` moves to LFM2.5-1.2B/2.6B. Qwen is not in the plan.
- **NemoTron super** (`paper:224`). The baselines doc lists it as a planned model
  with no run found (`baselines.md:73`).
- **`deepseek-v4-flash`** (`paper:224`). The recorded 63% is the older v4
  preview on the rc10 0-hop slice; the docs say it must be re-run on v4.1 before
  it is quoted (`baselines.md:71, 78–80`).
- **`xiaomi-mimo-v2.5`** (`paper:224`). The recorded 65% is on the rc10 0-hop
  easy slice, not the hard target slice (`baselines.md:70`).
- **"Task family" and "hop count"**. The current terms are "relation family",
  "measurement scope", and "task reasoning step count". "Reasoning hop count" is
  the older row-level measure (`glossary.md:260–275`). Pick one vocabulary.

## What is aligned

- Research questions and hypotheses: the primary question, the three secondary
  questions, H2/H3/H4, and the P0/P1/P2 result hierarchy match (`PRD.md:14–41,
  62–65`).
- Dataset source and pipeline: CADEvolve programs, AST plus runtime extraction,
  graph construction, offline precomputed labels, and a tabular release match
  (`paper:137–178`; `graph-content.md`; `release-dataset-contract.md`).
- Answer formats that are P0: number, integer, yes/no, 3D coordinate, bounding
  box, and multiple choice match (`task-structure.md:127–135`).
- Measurement scopes: all five scopes are defined (`glossary.md:437–445`).
- Fine-tuning direction: SFT then RL, rejection sampling, trace editing, and the
  teacher-surpass P2 stretch match (`paper:226–246`; `training.md:78`;
  `evaluation/plan.md`).
- The benchmark-gap claim and the exact structured-answer goal are aligned
  (`paper:11–19`; `PRD.md:9–12`).

## Schema gap the evaluation contract will not fix

The PRD asks for accuracy by relation family and measurement scope
(`PRD.md:99–101`). The evaluation harness expects `relation_families` and
`measurement_scopes` in the public row (`harness.md:18–23`). The new release
contract does not have either column (`release-dataset-contract.md:82–106`), and
the dataset coverage dimensions are target category, clue type, clue operand
form, answer meaning, answer format, and step count (`task-structure.md:207–218`).

This is not the known "no polished evaluation contract" gap. Even with a perfect
grader, the release cannot report the PRD's breakdown unless the fields are
added to the release or derived from `answer_evidence_json` by a documented
rule. The paper's "task family" metric is a third variant and has no owner.

**Recommendation:** add `relation_families` and `measurement_scopes` to the
release contract (or define a derivation from `answer_evidence_json`), then make
the paper use those names. This also gives the paper's Table 1 and §3.2 a
measurable basis.

## Other audit dependencies

These are already recorded in `plans/nov-21/dataset-architecture-audit.md`; they
affect the paper's claims but are not re-litigated here.

- `DA-2` — evaluation material and grader have no owner. Known; excluded from
  this audit.
- `DA-4` — `same_answer` and scoring tolerance disagree. The paper's "exact
  match" claim inherits this. There is an additional membership contradiction:
  `03b:320` allows `on the boundary` while the release contract excludes it.
- `DA-6` — the test split has no per-split coverage or balance. The paper's
  benchmark claim depends on it.
- `DA-7` — R-5 has no mechanism. The paper's "trivial shortcuts do not win"
  claim depends on it.
- `DA-9` — license and attribution are open. The paper's "no risks expected"
  claim is premature for a public release.

## Recommended order

1. **Choose the paper's scope.** Is it a P0 proposal or the full vision? If it is
   a proposal, add a P0/P1/P2 table to §3 and label every feature. If it is the
   full vision, the PRD and release contract need to grow; do not leave the
   paper describing a different dataset.
2. **Fix the abstract.** Replace "three harnesses", "task family", "rich
   distractors", and the implied 0–10 range with the current scope: `numpy`
   primary, relation family/measurement scope, real candidates, 1–5 steps P0.
3. **Fix the hop range.** 1–5 P0, 6–10 P2/aspirational; remove 0-hop; reconcile
   the 1-step warmup with the release floor at 2.
4. **Fix the answer-format table.** Remove entity references and the enum
   format; mark workplane state P1 and validity P2; remove `on_boundary` and
   `ambiguous`.
5. **Fix the ontology.** Replace "exhaustive" with "P0 graph vocabulary"; remove
   `intersects` and the relations that are not in `graph-content.md`, or label
   them future work.
6. **Fix the metrics.** Replace "task family" with relation family and
   measurement scope; add the two fields to the release contract or define their
   derivation.
7. **Fix the graph/critical-path claim.** Either add the graph and candidate-set
   trace to the release, or rewrite the contribution as internal and future
   work.
8. **Fix the example.** Give the target a unique tie-break and a supported
   answer meaning.
9. **Refresh the model and stack names.** LFM2.5 plus `liquid-finetune`;
   re-run `deepseek-v4.1-flash`; record or drop NemoTron.
10. **Fix the two lint hits.** `tools/check_dont_say.py` reports `frozen` and
    bare `model` at `paper:234–235`.

## What not to change

The core dataset idea, the research questions, the H2/H3/H4 hierarchy, the
CADEvolve-backed offline release, the P0 answer formats that survive, the
measurement scopes, and the SFT/RL/transfer plan are all consistent. The paper's
problem is scope drift, not a missing project.
