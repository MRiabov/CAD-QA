# Task generation decisions

**Parent:** [`README.md`](README.md).

**Status:** active, 2026-11-20.

This document records decisions scoped to the `03` task-generation module. A
decision here explains why the module contract has its current shape; the
contract remains normative. An accepted decision is not silently rewritten. A
change adds a new decision and marks the old one superseded.

Requirements-level decisions belong in
[`../../../requirements/decisions.md`](../../../requirements/decisions.md) and
implementation decisions that span pipeline stages in
[`../../../implementation/decisions.md`](../../../implementation/decisions.md).
Unanswered questions belong in the `## Open questions` section of the document
that owns them.

## TG-1 — Every task clue must be necessary

- **Status:** accepted (2026-11-20).
- **Context:** A clue that narrows at its position can still be redundant:
  dropping it may leave the task answer-unique, so the chain is longer than the
  reasoning it encodes. The weaker rule "each non-final clue leaves at least two
  answers" constrains only where the chain ends, and a redundant middle clue
  passes it.
- **Decision:** Every task clue must be necessary. Removing it from the chain
  must leave at least two distinct answers, or change the answer. Distinct
  answers are compared with `same_answer` at the stated precision. A redundant
  clue is dropped and the task shortened, or the chain is rejected.
- **Consequences:** The achievable step count is the number of necessary clues
  plus the answer step, so a quota target above it is a deficit. Long chains over
  continuous answers need a candidate set that shrinks gradually, so
  continuous-answer tasks are shorter on average than identity tasks.

## TG-2 — Fill targets by priority, then scarcity, and reject overfill

- **Status:** accepted (2026-11-20).
- **Context:** One task counts toward several quota targets at once: target
  category, clue type, answer meaning, answer format, and task reasoning step
  count. `03a` defines a minimum, a target count, and a maximum for each target,
  plus a priority tier (coverage, then balance, then volume), but it does not
  define the order in which targets are filled or what to do when one acceptance
  would affect several targets at once.
- **Decision:** Fill targets in the `03a` priority order, and within a tier
  process the scarcest targets first, where scarcity is the number of active
  programs whose graph can support the target. A task is accepted when it fills
  an unfilled target and does not push any cell past its maximum. An acceptance
  that would overfill is rejected and recorded.
- **Consequences:** The scheduler is deterministic given the plan, the ledger,
  and the program order. Scarcity-first takes rare targets early, so a later
  supply-driven sweep cannot starve them. Overfill is visible in the ledger
  rather than silently absorbed.

## TG-3 — Definition identity excludes assignment

- **Status:** accepted (2026-11-20).
- **Context:** A definition carries both content and assignment. The content is
  the task: state scope, binding, clues, answer, evidence, choices. The
  assignment is which plan version, family, split, and subset the task landed
  in. `03a` re-enters with a new plan version whenever a deficit is resolved,
  and accepted definitions must stay valid across that re-entry. Hashing the
  whole record would change every `definition_sha256` on every replan, so the
  immutability rule in `03a` could never hold.
- **Decision:** `definition_sha256` covers the content and the inputs that
  change it — program hash, graph schema version, runtime extraction hash,
  constructor version, definition schema version, and construction seed. It
  excludes `plan_version`, the program family, the split, and the subset.
  `task_id` covers the canonical task identity only, so it is stable across a
  replan. `answer_sha256` covers the answer and scoring fields and excludes
  answer evidence.
- **Consequences:** A replan preserves accepted definitions and their hashes. A
  hash mismatch means the content or one of its inputs changed, and the
  provenance block names which. Assignment changes are visible in the plan and
  the release row, not in the definition hash.

## TG-4 — `03` writes task definitions; task reasoning step support tables are a QA projection

- **Status:** accepted (2026-10-21).
- **Context:** The task reasoning step support tables had become a hand-authored
  generator input and crowded out the actual task-definition contract. That
  inverted the source of truth: a value is feasible because the task rules can
  construct it, not because a support row allows it.
- **Decision:** `03` defines task definitions and emits persisted
  `TaskDefinition` records. The task reasoning step support tables are derived
  from those rules as a separate QA baseline. They are not a pipeline stage and
  not a generator input; `03a` plans, `03b` constructs, `04` renders, and
  `03a`/`05` use the tables to check the release.
- **Consequences:** `03` does not read the task reasoning step support tables as
  data. `03a` calls the same derivation that writes them, so the plan and the QA
  projection cannot disagree; `05` reads the persisted tables. A supported value
  missing from the dataset is a coverage gap; a released value the table marks
  unsupported is a specification or generator defect. Dataset quantity remains a separate
  coverage question.

## TG-5 — Plan quotas before constructing task definitions

- **Status:** accepted (2026-10-21).
- **Context:** The valid-task set is combinatorial. Enumerating every task and
  selecting afterward wastes work and can exceed any practical budget.
- **Decision:** Plan task quotas first with independent quota targets, family
  profiles, split assignment, and attempt budgets. Construct and sample task
  definitions into that plan. Use `03c` to replan or expand the program data when quotas
  cannot be filled.
- **Consequences:** There is no separate post-construction release-selection
  pipeline stage. `03c` is a bounded loop back through supplemental `01b` selection,
  `01c`/`01d` delta processing, `02` graph building, and an updated plan.
  Deficits are recorded and either filled or accepted.

## TG-6 — Task generation is supply-driven with capability-aware deficits

- **Status:** accepted (2026-11-20).
- **Revised by:** `TG-9`; the census is derived from the graph, not emitted by
  `02c`.
- **Context:** A full demand-driven planner would specify a task cell up front and
  query a capability index for programs that can support it. The capability
  census needs the graph, but `01b` selects the program pool before `02` builds
  graphs, so the planner either reverses pipeline stage order or forces a larger
  execution pass. A capability in the pool is also not a constructed task.
- **Decision:** `03b` constructs tasks supply-driven by default, from the facts a
  graph actually has. The census is derived from the graph; `TG-9` supersedes
  the earlier sentence that had `02c` emit it as a by-product. `03a` and `03c` use
  that census only for deficits: when a
  quota target is underfilled, they query it for capable programs and request
  supplemental programs through the existing slow loop. A cell-level demand query
  is a last resort and carries a `forced` flag and a naturalness check.
- **Consequences:** `01b` stays metadata-based. `capability_deficit` becomes a
  deficit reason. Forced tasks are confined to the deficit path, where review can
  see them, and a miss is recorded rather than filled with an unnatural task.

## TG-7 — Canonical clue order is identity-bearing; prompt order is a permutation

- **Status:** accepted (2026-11-20).
- **Context:** Clues are conjunctive conditions on one target, so the prompt can
  present them in any order that respects references. The construction record
  needs a stable order, because identity, deduplication, the narrowing record,
  and the strict-narrowing check all depend on it. Treating the two as one order
  either freezes the prompt, which leaks that the last clue is the
  discriminator, or makes identity depend on rendering.
- **Decision:** The task definition stores a canonical clue order: dependency
  order first, then broad-to-narrow by the size of the narrowed set, descending,
  with a stable hash as the tie-break. Validity checks, the narrowing record, and
  `task_id` use this order. The prompt may render a permutation that respects
  reference dependencies. P0 renders the canonical order; P1 may render a seeded
  permutation recorded as the render seed.
- **Consequences:** The render seed and the presentation order belong to
  provenance, not to `task_id`. Clue wording uses presentation positions ("the
  face from clue 2"), never canonical positions. Strict narrowing is checked in
  canonical order only, so a permuted prompt may contain a clue that does not
  narrow at its position; the conjunction is unchanged. The multiple-choice pool
  stays the canonical penultimate set, so after a shuffle the choices are no
  longer "what the prompt's last clue discriminated between".

## TG-8 — Multiple-choice options come from the penultimate answer candidate set

- **Status:** accepted (2026-11-20).
- **Context:** `prompt-content.md` fixes the count (at least five, seven as the
  goal), the labels, uniqueness, leakage, and ordering. It does not say which
  candidates become options, so a renderer could draw from anywhere in the graph,
  including entities the last clue already excluded.
- **Decision:** Identity answers draw options from the penultimate answer
  candidate set, the entities the last clue discriminated between. Numeric answers
  draw options from the distinct answers of that set, so the options are
  comparable numbers. If fewer than five real options exist, the task is
  rejected; options are never padded.
- **Consequences:** The choice pool is a construction output, not a rendering
  choice: `03b` orders it and assigns its labels, so a multiple-choice task's
  `gold_answer` is a label before the definition is hashed. `04` renders that
  order and must not reorder, relabel, re-bind, or extend it. A task whose
  penultimate set is smaller than five is a deficit, not a padded task.

## TG-9 — The capability census is derived, not emitted

- **Status:** accepted (2026-11-20).
- **Context:** `TG-6` said `02c` emits a capability census as a by-product of
  graph construction. That implied an artifact, and left open whether it was a
  fourth graph table or a sidecar. The census is a pure function of the graph, so
  a stored copy can only be stale or redundant. The graph tables are per-entity
  and the census is per-program, so it also has no existing row to extend.
- **Decision:** The census is a typed function of the graph, derived on demand. It
  is not an artifact and has no schema version of its own. `03a` derives it for
  all active programs and stores the union per family in
  `TaskQuotaPlan.family_profiles`; `03b` derives it for the program it is
  constructing; `03c` reads `family_profiles`.
- **Consequences:** One fewer artifact, schema, and staleness rule, and no change
  to `io-contracts.md` or `artifacts.md`. The cost is one pass per graph batch plus a
  pass over the programs a slow-loop round adds. A replan derives nothing, because
  the graph batch has not changed and `family_profiles` is already in the plan.

## TG-10 — One construction pass per program, budgeted per family and step

- **Status:** accepted (2026-11-21).
- **Context:** `03a` budgeted `ceil(target_count * 1.5)` construction attempts for
  every quota target, while one accepted definition fills several targets. The
  budgets therefore summed to roughly 1.2–1.5 × 10^5 attempts for a 10^4-task
  release. `03-task-generation.md` also made construction parallel per quota
  target, which invites a graph re-read per target, and `03a` and `03b` each
  derived the capability census. The cover search had no bound beyond
  `max_state_entities`, which bounds one input, not the search.
- **Decision:** Construction is one pass per program and plan revision: load the
  graph and census once and fill every target assigned to the program at that
  step count. The attempt budget is per `(family, task reasoning step count)` and
  is `ceil(family_task_reasoning_step_quota * construction_attempt_multiplier)`;
  one acceptance decrements every target it fills. The plan carries the
  per-program census (`program_census`) and `03b` reads it. The cover search runs
  under count-based scope constants (`max_construction_candidates`,
  `max_construction_facts`, `max_cover_expansions`, `max_validity_rechecks`), and
  exhaustion is a `construction_deficit` with detail `construction_budget`. The
  constants are part of `constructor_version`.
- **Consequences:** A 10,000-task release budgets on the order of 20,000–30,000
  attempts instead of 1.2 × 10^5. Each program graph is read once per revision.
  The census is derived once per graph version. The search has a deterministic
  bound, so a pathological graph becomes a recorded deficit rather than an
  unbounded run. A budget change is a new `constructor_version`, so it cannot
  silently change an accepted definition.

## TG-11 — One pass projects candidate answers once

- **Status:** accepted (2026-11-25).
- **Context:** The cover search compares every candidate's answer with the
  witness. Resolving the answer per comparison turns one pass into quadratic
  graph reads, and `DS-REQ-15` allows several candidates to share one answer, so
  the comparison is needed for every candidate. `DS-REQ-35` also needs one
  definition per prompt identity.
- **Decision:** A pass projects the candidate rows once: stable row order, fact
  bitsets, and, for each answer meaning in the plan, the canonical answer and its
  `same_answer` group. The witness loop and the cover search read masks over the
  same rows; answer uniqueness and clue necessity are group counts over the
  surviving mask. The pass dedups accepted definitions by prompt identity.
- **Consequences:** Answer resolution is linear in candidates per answer meaning;
  `max_cover_expansions` remains the only super-linear bound. Candidate row order
  is the stable hash order, so the projection is deterministic and part of
  `constructor_version`.

## TG-12 — R-5 is a P1 quality gate, not a symbolic engine

- **Status:** accepted (2026-11-25).
- **Context:** R-5 was P0 and phrased as LLM-model behaviour. A per-task check of
  whether an answer is text-derivable would need closed forms for booleans,
  CadQuery selectors, and topology, which is a symbolic CAD kernel. The CAD graph already
  records the operation that produced each entity and the state chain, so the
  answer's dependency depth is available without a second geometry engine. The
  check must reject before the definition is persisted; an audit after `03b`
  would persist a task it already knows is shortcut-prone.
- **Decision:** `03b` runs a P1 `shortcut_resistance` validity rule. It calls the
  standalone `evaluate_shortcut_resistance(definition, graph, policy)` function
  in `shortcut_resistance.go`. The function resolves the answer dependency chain
  from the graph, records the operation count and topology flag, and returns
  `pass`, `fail`, `not_applicable`, or `unknown`. `fail` and `unknown` reject a
  shape-required definition; the failure row names the check and carries the
  count, the topology flag, and the reason. No chain is stored and CadQuery is
  not executed. A P0 run does not evaluate the rule.
- **Consequences:** A shortcut-prone definition is a failure row, not a
  `TaskDefinition`. The release schema and the release-check policy are unchanged. The P1
  release report counts the rejections and records the threshold and topology
  list. The function stays in `03b` until a second consumer appears; only then
  does it move to a shared package.

## Pending

The module-scoped decisions are accepted, and no module-scoped question is
pending. Requirements-level decisions live in
[`../../../requirements/decisions.md`](../../../requirements/decisions.md);
implementation decisions that span pipeline stages live in
[`../../../implementation/decisions.md`](../../../implementation/decisions.md).
