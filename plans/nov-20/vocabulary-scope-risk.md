# Vocabulary scope risk

**Status:** open risk, 2026-11-20. This is not a decision. It records a concern
about how the dataset vocabulary is being designed, with a proposed mitigation
and a way to test it.

**Related:** `plans/nov-19/03b-task-construction-design.md`,
`docs/dataset/requirements/graph-content.md`,
`docs/dataset/implementation/missing-contracts.md`.

## The concern

The dataset generator is engineer-decision-heavy. Every relation, every
measurement, every clue form, and every chain of them appears to need its own
thought, its own contract, and its own validation, because the code has to
implement it case by case. If that is literally true, the decision count grows
with the square of the vocabulary, and the project has no natural end.

The concern is not that the work is large. It is that the work does not appear
to converge: answering one question produces two more.

## Three readings of the concern

1. **No stopping rule.** Every answer expands the design surface. `D3` was withdrawn,
   but it produced `MC-36` and a new section 4.1. `distance` was one row and
   became a family of procedures. `contains` still carries the defect that
   `distance_to` had.
2. **No cost signal.** Every decision looks equally load-bearing while it is
   being written, so the schedule is a guess. `DS-31` (clue model) and `D6`
   (minimum narrowing) are not the same size of decision, but the record gives
   them the same weight.
3. **The documents are becoming the deliverable.** The dataset does not exist
   yet, while the contracts, the decision record, and the backlog do. If the
   documents are the product, their growth is the work, and there is no
   acceptance test.

## What the evidence says

The vocabulary is large:

| Layer | Count |
|---|---|
| entity categories | 16 |
| relations | 20 |
| measurements | 13 |
| clue types | 5 |
| clue operand forms | 4 |
| answer meanings | 14 |
| answer formats | 7 |

If every cell needed its own decision, the open backlog would be in the
hundreds. It is 25 missing contracts, 14 kernel issues, and 8 open decisions.

That is not proof of convergence, because the backlog records only what has been
noticed. It does support a three-class reading:

| Class | Example | Cost | Scaling |
|---|---|---|---|
| Mechanical | endpoint entity kinds, evidence fields, IDs | one rule applied many times | O(n) applications, O(1) decisions |
| Patterned | partiality, tolerance, frame, provenance | one decision per pattern, reused | O(k) decisions |
| Per-case | distance, angle, intersection, containment, effect | decision plus test per case | O(m), and m is unknown |

`distance_to` and `contains` look like two decisions but are one pattern:
declare endpoint entity kinds. `coplanar_with` and `coaxial_with` are the same
pattern again. The clue operand form was one decision and then applied to all
five clue types.

## Why it still feels quadratic

The current phase is breadth-first. The vocabulary is being enumerated before
any of it has been executed once, so nothing says which of the twenty relations
matters. All twenty look equally urgent, and the twenty-first keeps appearing.

Breadth-first design has no feedback signal. It therefore feels unbounded even
when the underlying structure is linear, and it produces exactly the symptom
described above: every answer expands the design surface.

A depth-first milestone behaves differently. One program, one solid state, one clue,
one answer, executed end to end. It produces a checkable number, and it shows
which parts of the vocabulary the milestone actually touched. The other relations
stop being urgent because nothing in the milestone needed them.

So the concern is probably about **process**, not about the domain. The domain is
not quadratic; breadth-first development of an undocumented vocabulary is.

## Proposed mitigation

**Build the plumbing milestone first. The release scope stays P0 as the PRD
defines it.** The plumbing milestone proves the construction path end to end; it does not
redefine what the first release must contain.

The operating rule:

> If a decision does not unblock the next milestone, defer it. Record the deferral as
> a state, not as an omission.

Concretely:

- `graph-content.md`: keep the P0 rows as P0. The P1 and P2 rows stay deferred as
  already marked, and no P0 row moves.
- distance and angle: both are P0 answer meanings in the PRD, so the pair domain
  (`MC-36`) is on the critical path rather than deferred.
- `03-task-generation/decisions.md`: accept module decisions when a milestone or a
  P0 requirement forces them.

## How to test the mitigation

The mitigation is falsified if any of these happen:

1. **The plumbing milestone needs most of the vocabulary.** If it alone requires more
   than a handful of relations and measurements, the vocabulary was justified
   and the concern was about sequencing, not size.
2. **A milestone exposes a new decision per entity kind.** If every entity
   category needs its own rule for the same question, the per-case class is
   larger than estimated, and the vocabulary should shrink rather than grow.
3. **Deferred rows keep reopening.** If three different quota targets each need
   a deferred row, the deferral was wrong and the row belongs in P0.

If none of those happen, the mitigation holds and the concern is answered by
evidence rather than by argument.

## Current position

No construction decision remains open in
`plans/nov-19/03b-task-construction-design.md`. `D3` was withdrawn into graph
completeness, and `D4` was folded into the answer equality defined by `DS-32`.
Two of the original eleven decisions dissolved into contracts that already
existed, which is evidence that the open count shrank by consolidation rather
than by omission.
