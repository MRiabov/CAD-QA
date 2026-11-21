# Missing-contracts audit — 2026-11-20 pass
<!-- dont-say: allow-file: point-in-time audit; findings are quoted and not rewritten -->

**Status:** audit, 2026-11-20. Snapshot: commit `0a3be5c`
(`docs: assign the release projection to 04 and map every column`).
**Applied:** `c5535e1`. The findings below are the record; the current state is
`docs/dataset/implementation/missing-contracts.md`.

**Scope:** the closed entries in
`docs/dataset/implementation/missing-contracts.md`, plus the contracts they
name. The audit asks three questions per entry:

1. Is the claimed contract actually in the owner document?
2. Does the closure sentence match what the document says?
3. Did the decision propagate to the requirements, decisions, planning math,
   test contracts, and adjacent stage docs, or does a stale statement remain?

This is a review document, not a source of truth. The owner documents remain
authoritative.

## Snapshot note

The tree moved while this audit was being written. The pass started at
`e314486` and ended at `0a3be5c`; `MC-13`, `MC-25`, and `MC-12` landed during
the audit. The findings below are pinned to `0a3be5c`. If `main` has moved,
re-check the entries whose owner files changed after that commit before acting
on a finding.

The work is on local `main`, 118 commits ahead of `origin/main`. This audit
document is on the `audit-missing-contracts` branch so it does not race the
agent still committing to `main`.

## Method

- Read each closed entry's owner document and compared it with the closure
  sentence in `missing-contracts.md`.
- Searched the requirements, `decisions.md`, `planning-math.md`, the test
  contracts, and the stage docs for statements that still describe the old
  contract.
- Checked every relative Markdown link under `docs/` with a small script.
- Ran `tests/test_prompt_templates.py`.
- Read the closure commits' `--stat` output to see which files a closure
  actually touched.

## Verdict summary

There are 26 substantive closures in the 2026-11-20 pass (the three merge
entries are counted separately). The result:

| Verdict | Count | Entries |
|---|---|---|
| Clean | 14 | `MC-25`, `MC-14`, `MC-40`, `MC-31`, `MC-17`, `MC-23`, `MC-28`, `MC-47`, `MC-35`, `MC-43`, `MC-08`, `MC-39`, `MC-36`, `MC-34` |
| Clean with a caveat | 9 | `MC-13`, `MC-38`, `MC-37`, `MC-09`, `MC-16`, `MC-48`, `MC-45`, `MC-12`, `MC-46` |
| Not actually closed | 3 | `MC-44`, `MC-27`, `MC-32` |

The three not-closed entries are the highest priority because the backlog now
claims a contract that is absent or contradicted. `MC-13` is the largest single
risk among the caveats: it is written, but five parts of the contract do not
hold together.

## Not actually closed

### `MC-32` — the shallow path is still there

The original entry was "Manifest link path points one directory too shallow."
The closure says "the external manifest has no link field; the repo-wide link
check passes." The manifest-link-field question is real, but the original path
defect was not fixed.

`docs/dataset/implementation/pipeline/01e-write-external-dataset-manifest.md:27`
still says:

```text
It is not the release manifest defined in `../requirements/release-dataset-contract.md`.
```

From `docs/dataset/implementation/pipeline/`, the correct path is
`../../requirements/release-dataset-contract.md`. The closing commit
(`1d0af2b`) changed only `missing-contracts.md`, `implementation/README.md`,
and `00-end-to-end.md`; `01e` was not touched.

The repo-wide link check does not catch this because the path is a code span,
not a Markdown link. The link check itself passes: the only broken relative
link under `docs/` is
`docs/_archive/paper/cadqa_draft.md -> CA2Img-GanttChart-mermaid.png`, which is
in the excluded archive.

**Disposition:** fix the path, then re-close the entry. The "no link field"
statement can stay, but it is not the whole entry.

### `MC-27` — the Q1 premise is false

The closure says "Q1 is retired for PRD Q7, and the benchmark is pinned in the
manifest, in `05`." The benchmark half is done; the Q1 half is not supported by
the documents.

`docs/dataset/requirements/PRD.md:430` says:

```text
Q1 (P0). Resolved 2026-10-21. The first benchmark dataset release targets
ten thousand tasks.
```

That is a size question, not the same-CAD-model check. The same-CAD-model
question is `Q7` at `PRD.md:448`:

```text
Q7 (P0/P1). P0 uses Option A: compare normalized CadQuery program text.
P1 uses Option B: normalize variable names and formatting with an AST, hash
the result, and run CadQuery to compare the shape only for candidates that
survive the cheap check or for a final audit.
```

No `Q1` anywhere under `docs/dataset/` asks how the P1 same-CAD-model check
works, and no closure commit edited the PRD to retire one. The original entry
appears to have confused `Q1` with `Q7`.

The benchmark pinning is in
`docs/dataset/implementation/pipeline/05-validate-and-export-release.md:40-41`:

```text
Record the external benchmark identity and revision in `manifest.json`.
No program from that benchmark appears in training or evaluation (R-16).
```

But the `05` input list at `05-validate-and-export-release.md:15-19` still does
not include the external benchmark. The check has no declared source for the
benchmark programs.

**Disposition:** replace the Q1 sentence with the actual decision (`Q7` is the
transfer-comparison definition), add the external benchmark to the `05` input
model (or record it as a `MC-26` input gap), and keep the manifest pinning.

### `MC-44` — the support definition contradicts the requirements

`MC-44` closed on:

> feasibility is the constructor's output over a committed coverage fixture
> set, not an abstraction of the grammar.

`docs/dataset/implementation/task-step-support.md:47-60` says that:

```text
A dimension value is supported at a task reasoning step count when the
constructor produces at least one valid definition of exactly that many steps
for it, over the coverage fixture set.

Support is an observation, not an abstraction of the grammar. There is one
implementation, the constructor, and the table records what it did.
```

The requirements and planning docs still say the opposite:

- `docs/dataset/requirements/task-structure.md:279-281`: "Supported is a
  property of the task structure, not of the current generator: a value may be
  marked unsupported only when no valid task can express it at that step
  count."
- `docs/dataset/implementation/planning-math.md:41-42`: "Support is structural:
  a value is unsupported only when no valid task can express it at that step
  count."
- `docs/dataset/implementation/pipeline/testing/task-step-support.md:15`: the
  structural tier proves "every absent cell has a forbidding rule; every
  present cell is not forbidden". That is the grammar abstraction `MC-44`
  rejected.

The closing commit `fd8dd8d` changed `task-step-support.md`, the testing docs,
and `missing-contracts.md`; it did not change `task-structure.md` or
`planning-math.md`.

The artifacts the closure names are also absent: `pipeline/testing/` has no
`support-table.json`, and `pipeline/testing/fixtures/` contains only
`README.md`. The contract is written; the "committed coverage fixture set" and
"checked-in expected table" it refers to are not.

**Disposition:** decide which definition wins. If support is observed, restate
`task-structure.md` section 5 and `planning-math.md`; reconcile the structural
tier (it currently proves a grammar claim) or rename it. Add the fixtures and
the expected table, or soften the closure sentence to "contract written;
artifacts pending".

## `MC-13` — five holes in the release check contract

`MC-13` is the largest contract in the pass. The check list is a real
improvement, but five parts do not hold together.

### 1. `reported` is not an outcome

`docs/dataset/implementation/pipeline/05-validate-and-export-release/release-checks.md:150`
gives `clue_operand_form_step_mix` the first-release disposition `reported`.

The outcomes table at `release-checks.md:206-212` has only `pass`, `miss`,
`superseded`, `not_applicable`, and `deferred`, and `:214` says "Every in-scope
miss blocks until the owner accepts it."

`DS-REQ-18` and `task-structure.md:318-323` say the narrow clue-operand-form check
is computed and reported **without blocking**. There is no outcome that
represents a computed, non-blocking miss. A row that is `reported` and fails
cannot be represented: `miss` would block, and `deferred` would deny that the
check ran.

**Disposition:** add a `reported` outcome with `Blocks export: no`, or add a
separate `blocking` flag per check. The report's `outcome` field should not be
the only carrier of the blocking rule.

### 2. The per-step bound arithmetic is reversed

`release-checks.md:162-165` says:

```text
absolute range: minimum_count = ceil(minimum_share * denominator)
                maximum_count = floor(maximum_share * denominator)
per-step range: minimum_count = max(1, floor(0.5 * conditional_release_share * denominator))
                maximum_count = ceil(2 * conditional_release_share * denominator)
```

The absolute range is tight; the per-step range is loose. For a conditional
share of `1/3` and denominator `10`:

- the lower bound is `floor(1.66) = 1`, so a value at `1/10 = 0.3x` passes a
  `0.5x` lower bound;
- the upper bound is `ceil(6.66) = 7`, so `7/10 = 2.1x` passes a `2x` upper
  bound.

The tight directions are `ceil` for the lower bound and `floor` for the upper
bound, which is what the absolute range already does.

**Disposition:** use `max(1, ceil(0.5 * ...))` and `floor(2 * ...)`; keep the
`max(1, ...)` rule for the one-task floor.

### 3. R-10's 1% cap is deferred although R-10 is P0

`release-checks.md:100` marks `cad_model_share_cap` as `deferred`, citing R-10.

`PRD.md:249` has R-10 as P0:

```text
R-10. The dataset is diverse. It draws from at least one thousand distinct
CAD models, and no single CAD model is above 1% of tasks.
```

`PRD.md:285` says the same cap is P1, and `Q11` says P1. `balance.yaml:25`
keeps `cad_model_max_share` under the P0 marker, and `03a:258-261` plans the
cap:

```text
per_program_task_quota = min(max(1, floor(0.01 * dataset_release_task_count)),
                             max(1, ceil(dataset_release_task_count / usable_program_count)))
```

The paragraph added at `release-checks.md:113-115` says the first-release column
"follows the requirement priority, not the `# p0` and `# p1` markers". R-10 is
P0, so that rule makes the deferral self-contradictory.

**Disposition:** decide the priority once. Either enforce the cap in the first
release, or split R-10 into a P0 count clause and a P1 cap clause and update
`PRD.md` section 8 and Q11. Do not leave the check labelled R-10 and deferred.

### 4. R-9's "most benchmark tasks" and section 8's 80% are only reported

`release-checks.md:130-134` says:

```text
R-9 also says that steps 3 and 4 carry most benchmark tasks, and PRD section 8
says at least 80% of tasks need three or more steps. Both are sums of
`step_share` rows ... Neither is a second check.
```

`planning-math.md:53` lists "Three or more steps | At least 80%" as a
plan-level target. If the policy mix changes, a release can fall below 80% and
no row blocks. The new `step_count_range` check at `release-checks.md:98`
covers "steps 1 through 5 all appear", not the 80% share.

The new check also has no report row shape: the report schema at
`release-checks.md:240-263` defines coverage rows (`scope: step_<n>`) and
balance rows (`count`/`denominator`), but a set-equality check over step counts
is neither.

**Disposition:** add an explicit `steps_three_or_more_share` check (or record
the 80% target as an accepted miss when it is not met), and give
`step_count_range` a defined report row.

### 5. The "one implementation" claim contradicts `MC-48`

`release-checks.md:25-26` says the shared `conditional_release_share` takes
`supported_values` "from the task reasoning step support tables", and that
`03a` and `05` both call it.

`docs/dataset/decisions.md:451-453` (`TG-4`) says `03a` does **not** read the
tables as data; it calls the derivation that writes them. `03a:166-167` says
supported values come from the `03b` rules and the release implementation
scope. `03a:11-14` still lists "the release implementation scope" as an input.

The shared function cannot take its input from the tables for `03a` and from
the derivation for `05` while being one implementation. The three descriptions
must be reconciled.

**Disposition:** define `supported_values` as the derivation's output, called
in-process by `03a` and read from the persisted table by `05`, and say so in
both docs.

## Clean with a caveat

### `MC-12` — the projection is assigned, but `answer_sha256` has no field

`MC-12` closed on `0a3be5c`. The closure is mostly right:

- `04` now owns the projection (`04-render-prompt-and-choices.md:24-44`);
- the release contract has a `Carries` row per column
  (`release-dataset-contract.md:82-105`);
- `answer_schema_version` is now a `TaskDefinition` field
  (`03b-construct-task-definitions.md:39`);
- `clue_types` comes from `clue_operand_form_profile`;
- `prompt_sha256` is defined over the prompt bytes;
- `answer_sha256` is copied, not recomputed.

The remaining gap: the release contract says `answer_sha256` carries
`TaskDefinition.answer_sha256` (`release-dataset-contract.md:104`), and `04`
says "Copy `answer_sha256`" (`04-render-prompt-and-choices.md:39`), but the
`TaskDefinition` field table (`03b:22-45`) does not list `answer_sha256`.
`03b:407` defines it in the "Three hashes" table, but a hash definition is not
a persisted field. The projection's source is undefined.

**Disposition:** add `answer_sha256` to the `TaskDefinition` field table, or
change the release contract to say `04` derives it from the definition's answer
fields (which would contradict "copied, not recomputed"). The first is
consistent with the rest of the closure.

### `MC-45` — PRD R-12 still says the target is empirical

`MC-45` closed on "the P1 balance row is an equal share among supported forms".
`task-structure.md:312` says that, and `balance.yaml:86` sets `target: equal`.

`PRD.md:251` still says:

```text
In P1, clue operand form is balanced once its target is set from the first
release distribution.
```

That is an empirical target, not an equal share. `release-checks.md:109` uses
`dimensions.clue_operand_form.target` (equal).

**Disposition:** restate R-12 to say the P1 target is an equal share, or change
the target to the first-release distribution. One of the two docs is wrong.

### `MC-38` — the check is per form, the decisions are per pair

`MC-38` closed on the release table carrying `clue_operand_form_profile` and
`05` reading it for clue operand form coverage. That is true:
`release-checks.md:75` checks every supported **form**.

But `decisions.md:511-512` (`DS-REQ-04`) says "Coverage is reported over clue type
× clue operand form for reference-bearing clues only", and `decisions.md:652-653`
(`DS-REQ-19`) says "`05` reports coverage per `(clue_type, clue_operand_form)`".
The support table stores one `clue_operand_form` per row
(`task-step-support.md:136-137`), with no clue type.

**Disposition:** add the pair breakdown to the report (the release data has it
in `clue_operand_form_profile`), or restate `DS-REQ-04` and `DS-REQ-19` to say the
check is per form and the pair is descriptive.

### `MC-09` — the provenance sentence is wrong

`03b:25` says `definition_sha256` is a "Hash of the canonical task content and
the inputs that change it. Assignment and provenance are excluded."

`03b:409-414` says the hash covers `runtime_extraction_sha256`,
`constructor_version`, and `construction_seed`. All three are provenance
fields (`03b:437-439`). `TG-3` is correct; the field-table sentence is not.

**Disposition:** say "the serialized provenance block is excluded; the inputs
that change the content are covered". The `answer_schema_version` part of the
old finding is fixed by `0a3be5c`.

### `MC-16` / `MC-48` — `03a` still presents scope as an input

`03a:11-14` lists "the release implementation scope" as an input, and
`03a:166-167` says supported values come from the `03b` rules and that scope.
`TG-4:451-453` and `task-step-support.md:23-27` say the support-table
derivation is the scope filter and `03a` calls it. `03a` never says it calls
the derivation.

This is a wording gap, not a contradiction: the scope is a product priority,
not a file. But it is exactly the distinction `MC-16` and `MC-48` were closing.

**Disposition:** make `03a` say it calls the support-table derivation, and
remove or define the "release implementation scope" input.

### `MC-37` — the release description is thinner than the definition

`03b:217-225` defines `answer_evidence` with `evidence_kind`,
`evidence_rule`, `evidence_refs`, `answer_equivalent_set`, and `point_probe`.
The release contract's `Meaning` column at
`release-dataset-contract.md:105` still summarizes only "measured or derived,
references, and rule". The new `Carries` column maps the whole
`TaskDefinition.answer_evidence`, so the data is carried; the description is
incomplete.

**Disposition:** update the `Meaning` column to name the equivalent set and the
point probe. This matters because `05`'s review pack reads bound entity ids
from the evidence (`05-validate-and-export-release.md:110-111`).

### `MC-46` — `TG-6` still contains the superseded sentence

`TG-9` says the census is derived, and `TG-6` has a `Revised by: TG-9`
header. But `TG-6`'s decision body still says "`02c` emits a program capability
census as a by-product of graph construction" (`decisions.md:547`).

The decisions document says an accepted decision is not silently rewritten, and
a change marks the old one superseded, so this is allowed by convention. It is
still a trap for a reader who reads the body and not the header.

**Disposition:** either leave it (the header is the convention) or add a
one-line note in the body pointing at `TG-9`. No contract change is needed.

## Clean

These have the claimed contract in the owner document, and no contradicting
statement elsewhere:

- `MC-14` — `failure-record.md` owns the row, dedupe key, merge, order,
  reconciliation, and aggregation; `artifacts.md:28` says one partition per
  stage.
- `MC-40` — `03c:62-116` has the seven `DeficitClass` values, the allocation
  detail mapping, the census routing, the local probe rule, and the
  non-emitted-pair rule.
- `MC-31` — `00-end-to-end.md:43` and `03c:33-43` include `01d` in the slow
  loop.
- `MC-17` — `01c:26-31` and `01d:10-11` keep reserve rows fetched but not
  normalized or graphed; promotion is the slow loop.
- `MC-23` — `03c:50-58` has three rounds, the 20% growth cap, and
  `AcceptedMiss`; `balance.yaml:47-49` supplies the numbers.
- `MC-28` — `05:94-114` has the blocking review gate and the P0 sample.
- `MC-47` — `task-structure.md:55,61`, `construction.md:34-42`, and
  `03b:70-74` all make a scalar target a measurement instance.
- `MC-35` — `graph-persistence.md:49-69` carries relation `tolerance` and
  evidence; `:319-321` excludes both from `relation_id`.
- `MC-43` — `graph-construction.md:120-171` has named endpoints, pair rows, and
  the `max_state_entities` rejection.
- `MC-08` — `03b:181-193` has the resolver table; `release-dataset-contract.md:38`
  makes the dataset card state the conventions.
- `MC-39` — `03a:129-135` is coverage-only in P0, one occurrence per supported
  form per step count, no share.
- `MC-36` — `graph-content.md:215-224` defines the scope constant and says not
  to recompute it; `graph-construction.md:169-171` reads the recorded number.
- `MC-34` — `implementation/README.md:28-29` lists `pipeline/testing/` and
  `pipeline/streamlined/`.
- `MC-25` — see "Notes on clean entries" for the two minor notes.

## Notes on clean entries

### `MC-25` — clean, with two notes

`MC-25` is the strongest closure in the pass:

- `prompts.yaml` exists and has the dataset and evaluation namespaces;
- `prompt-templates.md` defines the schema, IDs, placeholder forms, label
  tables, selection rules, and validation;
- `04` and `io-contracts.md` name `PromptTemplateSet`;
- `05` records the version and hash;
- `tests/test_prompt_templates.py` passes (4 tests);
- the shell's frame line matches `prompt-content.md:33` exactly.

Two notes:

1. The P0 template set includes `dataset.question.material_change` and
   `dataset.question.topology_change`, but `DS-REQ-08` says effect answers that
   need a second state wait for P2 (`decisions.md:564-572`). The templates are
   harmless, but the validator's "required P0 IDs" will require copy no P0 task
   can use.
2. The membership question's `point` has no named source field. It lives in
   `answer_evidence.point_probe` (`03b:225`), and `04` can read it, but the
   template schema does not say so. This belongs to `MC-11` (rendering inputs).

## Open-entry drift

### `MC-11` — the open entry is stale on the template version

`MC-11` says the `04` input "omits program text, render seed, and template
version". `io-contracts.md:21` now lists `TaskDefinition, PromptTemplateSet`,
and `prompt-templates.md:66-72` says the set carries `version`. The template
version is no longer wholly omitted; program text and render seed still are.

**Disposition:** update `MC-11` to drop the template-version clause. This is an
open-entry edit, not a re-close.

## Merges

- `MC-19` merged into `MC-18`: only the backlog mentions it; the open `MC-18`
  says "It absorbs `MC-19`".
- `MC-24` merged into `MC-15`: only the backlog mentions it; the open `MC-15`
  says "It absorbs `MC-24`".
- `MC-10` merged into `MC-09`: only the backlog mentions it.

No dangling references remain outside the backlog.

## Cross-cutting observations

- **The pass is still moving.** Six commits landed between `e314486` and
  `0a3be5c`. `MC-13` alone received its initial contract and three follow-ups in ten
  minutes (`04b0796`, `039f95d`, `c9afb01`, `f2ca1a2`). Re-audit after the next batch.
- **`MC-13`'s "one check per requirement statement" is the strongest
  overstatement in the pass.** The check list covers R-7, R-8, R-11, and most
  of R-12, but it misses R-10's cap and R-9's 80% sum, and it has no outcome
  for the one row that is deliberately non-blocking.
- **The `# p0` / `# p1` markers are now defined as "when a number is used", not
  "when a check blocks"** (`balance.yaml:11-14`, `039f95d`). That is a good
  clarification, but it makes the R-10 deferral a requirements problem rather
  than a marker problem.
- **The support-table definition is the one place where two product documents
  and two implementation documents disagree.** It is not a wording nit: the
  structural tier and the observed-constructor definition test different
  things.
- **The work is on `main`.** The pass is 118 commits ahead of `origin/main`;
  no PR exists. That is outside this audit's scope, but it means the snapshot
  is local-only.

## Recommended next actions

1. Fix the three false closures: `MC-32` path, `MC-27` Q1/benchmark input,
   `MC-44` support definition and fixtures.
2. Fix `MC-13`: add a `reported` outcome or a `blocking` flag; reverse the
   per-step `floor`/`ceil`; decide R-10's priority; add the 80% check or record
   it as an accepted miss; reconcile the `conditional_release_share` input with
   `TG-4` and `03a`; give `step_count_range` a report row.
3. Add `answer_sha256` to the `TaskDefinition` field table (`MC-12`).
4. Restate `PRD.md` R-12 or change the clue-operand-form target (`MC-45`).
5. Add the `(clue_type, clue_operand_form)` breakdown or restate `DS-REQ-04` and
   `DS-REQ-19` (`MC-38`).
6. Fix the `03b:25` provenance sentence (`MC-09`), and make `03a` say it calls
   the support-table derivation (`MC-16` / `MC-48`).
7. Update `MC-11` to drop the template-version clause.
8. Decide whether the P0 template set should require the P2 effect questions,
   and name the membership point source (`MC-25` notes).
9. Add a test that reads the R-7..R-12 statements and the `release-checks.md`
   table and fails when a statement has no check row. The current table is
   good, but it is hand-maintained.

## Verification performed

- Snapshot: `git rev-parse HEAD` = `0a3be5c`.
- Link check: one broken relative Markdown link under `docs/`, in
  `docs/_archive/paper/cadqa_draft.md`; all `docs/dataset` links resolve.
- `tests/test_prompt_templates.py`: 4 passed.
- Closure commits inspected: `1d0af2b` (`MC-32`), `0825f5b` (`MC-27`),
  `fd8dd8d` (`MC-44`), `04b0796` + `039f95d` + `c9afb01` + `f2ca1a2`
  (`MC-13`), `eb2ed4d` (`MC-25`), `0a3be5c` (`MC-12`).
- Citation check: 83/83 source-line checks matched at `0a3be5c`.
- `rumdl check` on this file: no issues.
- Each cited line was read at `0a3be5c`; the line numbers in this document are
  from that commit.
