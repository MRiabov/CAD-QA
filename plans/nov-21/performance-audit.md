# Dataset pipeline performance audit — 2026-11-21

**Status:** audit, 2026-11-21. Pinned at commit `e8dc137`.

This is a review document, not a source of truth. The owner documents remain
authoritative. Findings are pinned to the commit above; if `main` has moved,
re-check the owner file named in each finding before acting on it.

**Scope:** `docs/dataset/` — requirements, implementation docs, pipeline stage
docs, extraction contracts, `decisions.md`, and the run contract. Read-only: no
owner document was changed.

**Question:** where does the documented pipeline spend work it could avoid, and
which of those costs should be designed out before implementation rather than
measured afterwards?

**Verdict:** the artifact layer is performance-aware and mostly right; the
*work-multiplication* layer is not. The docs already measure and reject the two
classic mistakes (JSON rows, a relational graph store) and they cache, resume,
stream, and project columns. What is missing is a cost budget for the things
that multiply: process lifecycle per program, unit identity across a replan,
construction attempts per quota target, and pair rows per solid state. Those are
the costs that decide whether a run takes an hour or a day, and they are decided
in the contracts, not in the code.

## Method

- Read every pipeline stage doc (`01`–`05`), the extraction contracts that carry
  cost (`runtime.md`, `graph-construction.md`, `graph-persistence.md`,
  `geometry-classification.md`), `run-contract.md`,
  `artifacts.md`, `planning-math.md`, `task-step-support.md`,
  `failure-record.md`, `missing-contracts.md`, and `decisions.md`.
- Cross-checked the cost claims against the numbers the docs already publish
  (`DS-39`, `DS-40`, `DS-44`) and against the measured artifact in
  `runs/current_cadevolve1000_10k_regen_20260613`.
- Measured the CadQuery/OCP import cost on this host (section "Measurement
  log"), because several findings turn on it.
- Did not implement or profile the replacement generator; it does not exist
  yet. Estimates are labelled as estimates.

## Findings

| ID | Finding | Severity |
|---|---|---|
| `PA-1` | One fresh Python child per program pays the CadQuery/OCP import every time | **High** |
| `PA-2` | A replan changes every `03b`/`04` unit identity, so "residual" replanning rebuilds the release | **High** |
| `PA-3` | Construction attempt budgets are per quota target, so a task is budgeted 8–10× | **High** |
| `PA-4` | The cover search has no stated cost bound and is multiplied by `PA-3` | **High, design now** |
| `PA-5` | `03b` work is parallel per quota target, which invites a graph re-read per target | Medium |
| `PA-6` | `03a` and `03b` both derive the capability census for the same graphs | Medium |
| `PA-7` | Pair rows are emitted for every solid state, but P0 binds one state per task | Medium |
| `PA-8` | One-row Parquet parts for cheap per-program units amplify files and resume scans | Medium |
| `PA-9` | Answer evidence is canonical JSON per row, and its size has no bound | Medium |
| `PA-10` | `02c` recomputes hashes `02b` already produced | Low |
| `PA-11` | `04` names the program text as a per-task input, inviting a lookup per task | Low |
| `PA-12` | The runtime result is written by the child, read by the parent, and written again | Low |
| `PA-13` | `01c` batch parts and `01d` per-program identity have mismatched granularity | Low |
| `PA-14` | The `02b` cache key's "execution environment identifier" is undefined | Low, but correctness-adjacent |

---

## `PA-1` — One fresh child process per program pays the OCP import every time

**Evidence:** `implementation/pipeline/extraction/cadquery/algorithm/runtime.md:11`
("Run one accepted program in a fresh child Python process");
`implementation/pipeline/02b-execute-cadquery.md:17`; the worker protocol in
`implementation/python-and-golang.md:120-125` describes one start, one request,
and one response, which reads as one process per request.

**What the docs say.** Each program runs in its own child process, and the Go
orchestrator starts a Python worker process per request. Nothing in the contract
preloads CadQuery, reuses an interpreter, or says the child is forked from a
preloaded parent.

**Cost.** Measured on this host: `import cadquery` is 2.1–2.8 s and 451 MiB peak
RSS; bare Python is 18 ms. At 1,500 active programs that is roughly **50–70
minutes of CPU and 451 MiB of resident memory per concurrent worker**, spent
before any geometry is evaluated. It is also inside the 30-second wall clock if
the timer starts at spawn, so about 7–9% of every execution budget is import.
Because `--jobs` defaults to `min(NumCPU, available_memory / per_worker_memory)`,
the resident cost also caps concurrency on a memory-limited host, and the
2 GiB address-space limit leaves about 1.5 GiB for the shape after import.

**Why it is avoidable.** Process isolation is the requirement, not a fresh
interpreter. A long-lived worker that imports CadQuery/OCP once and forks a
child per program keeps isolation (each child is a fresh address space), keeps
the timeout and memory limit, and keeps `PYTHONHASHSEED=0`; only the import is
amortized. A worker that runs a small batch and is replaced on a crash is
equally isolated.

**Recommendation.** Make the execution boundary "a fresh *address space* per
program", and require the worker to preload CadQuery/OCP before forking. State
that the 30-second limit starts after the child signals ready. Record the
measured import cost in `02b` so the decision is not re-litigated.

---

## `PA-2` — A replan changes every `03b`/`04` unit identity

**Evidence:** `implementation/run-contract.md:328-330` (`03a` identity includes
the whole `02c` pipeline stage parts hash; `03b` identity includes the `03a`
plan part hash; `04` identity includes the `03b` part hash);
`implementation/run-contract.md:359` ("A unit whose part identity does not match
the current identity is stale and is recomputed");
`implementation/pipeline/03-task-generation/03a-allocate-task-quotas.md:446-449`
("Accepted definitions are immutable … `03b` resumes with the new plan version
and the same `DeficitLedger`; accepted definitions are not regenerated");
`implementation/pipeline/03-task-generation/03b-construct-task-definitions.md:549-553`
("A `task_id` already present in the parts … is skipped").

**What the docs say.** Two incompatible things. `03a`/`03b` promise that a fast
or slow loop reuses accepted definitions and only constructs the residual. The
run contract says any unit whose identity changed is stale and is recomputed.

**Why it bites.** A plan revision writes a new plan part. Every `03b` unit's
identity includes that part hash, so every per-program part becomes stale, and
the run contract's rule says recompute. `03b`'s own resume rule says skip the
`task_id`s, which is the opposite instruction for the same unit. Whichever rule
wins, the design is wrong: if identity wins, one supplemental delta or one
re-executed program rebuilds all 10,000 definitions and all 10,000 prompts; if
the skip rule wins, a part can hold rows from two plan versions under one
identity, which breaks the "a part is immutable for its identity" invariant.

The trigger is not exotic. `03c` allows three expansion rounds, each adding up
to 20% of the pool; a single re-executed program changes the `02c` parts hash;
and a changed tolerance policy changes every graph. Any of these currently
cascades to a full `03`/`04` rebuild, which is exactly the cost the fast loop
exists to avoid.

**Recommendation.** Split identity from assignment. Give `03b` a unit identity
of `(program_sha256, 02c part hash, constructor version, definition schema
version, construction seed)` and make the plan a *separate* input: its targets
steer what is constructed, but they are not part of an accepted definition's
identity. `TG-3` already excludes assignment from `definition_sha256`, so this
is the same principle applied to the unit. Then a replan changes the plan part
and nothing else, and `03b` genuinely resumes. Do the same for `04`: its identity
should be the set of `definition_sha256` values it consumed for that program,
not the whole per-program part hash, or accept that appending a task re-renders
that program. Add one paragraph to `run-contract.md` stating which identity
changes are expected to invalidate work and which must not.

---

## `PA-3` — Construction attempt budgets are per quota target, so a task is budgeted 8–10×

**Evidence:** `implementation/pipeline/03-task-generation/03a-allocate-task-quotas.md:104`
("One construction batch per quota target and family");
`:353` (`ceil(family_quota_target_count * construction_attempt_multiplier)`);
`:382` ("Construct one whole batch per plan revision"); `03b:556`.

**Why it bites.** A released task counts toward one target category, one answer
format, one answer meaning, one step count, and one or more clue types and clue
operand forms. The plan's target counts therefore sum to roughly 8–10× the task
count; at the default 1.5 multiplier the budgets sum to roughly **1.2–1.5 × 10^5
construction attempts, an order of magnitude more than the 10^4 released
tasks**, even though `TG-2` accepts one definition into
several targets at once. The docs never reconcile the two: budgets are sized
per target, acceptance is multi-target.

The second-order cost is worse than the first. Every attempt is a cover search
(`PA-4`), and the contract says not to top up inside a revision, so the
over-provisioned batches are all constructed before anyone notices that the
targets were already filled.

**Recommendation.** Budget attempts per `(family, task reasoning step count)`
or per family, not per quota target, and let one accepted definition decrement
every target it fills. If per-target budgets are kept, state the expected
multiplier and subtract targets already filled by an earlier batch in the same
revision. The honest number for a 10,000-task release is on the order of
20,000–30,000 attempts, not 1.2 × 10^5.

---

## `PA-4` — The cover search has no stated cost bound

**Evidence:** `implementation/pipeline/03-task-generation/algorithm/construction.md`
(`possible_answers = all entities of the target category`, then `cover` per
candidate witness); `requirements/graph-content.md` (`max_state_entities`
provisional at 500); `03b` (`clue_narrows`, `clue_necessary`,
`answer_equivalence`).

**What the docs say.** Construction is "a bounded set-cover search" that "never
enumerates the task space". The only stated bound is `max_state_entities = 500`,
which bounds one input, not the search.

**Why it bites.** The search is per candidate witness, over all other
candidates, with a fact extension per candidate; the validity gates then remove
each clue and re-check the remainder. Cost is roughly
`|candidates| × |facts| × |clues|` set operations per target, times the number
of attempts (`PA-3`) and the number of quota targets a program is asked to fill
(`PA-5`). With 500 candidates and ~30 operations this is tens of millions of set
operations per program per target, in Go, on every attempt. It is the dominant
CPU cost of `03` and nothing in the contract budgets it.

**Recommendation.** State a cost budget and a per-program limit: candidate cap
for construction (separate from `max_state_entities`), fact cap, cover
iterations, and a deadline after which the target becomes a deficit rather than
a slow success. The contract already prefers a recorded miss to a padded task;
apply the same rule to a search that exceeds its budget. Also record measured
attempts and milliseconds per target in the deficit ledger so the budget can be
tuned from data instead of guesswork.

---

## `PA-5` — `03b` is parallel per quota target, which invites a graph re-read per target

**Evidence:** `implementation/pipeline/03-task-generation.md:46` ("parallel per
program, family, and quota target"); `03a:390`; `run-contract.md:249` (the durable
part is per program, but the unit and the flush trigger are per task batch).

**Why it bites.** The graph for one program is the input to every target that
program serves. If the scheduler parallelizes by quota target, the natural
implementation opens and hydrates the same program graph once per target —
5–8 times, plus once per attempt batch. The docs never say "load the program
graph once and construct all of that program's targets from it".

**Recommendation.** Make the construction unit a `(program, plan revision)`
pair that fills every target assigned to that program in one pass, and make the
per-target batches a scheduling detail inside it. One graph read per program per
revision is the floor; state it.

---

## `PA-6` — `03a` and `03b` both derive the capability census

**Evidence:** `implementation/pipeline/03-task-generation/algorithm/program-capability-census.md:48`
(`03a` derives it for every active program) and its Consumers table (`03b`
derives it for the program it is constructing); `DS-43`.

**Why it bites.** The census is one pass over a graph, and it is run twice: once
by `03a` over the whole pool, once by `03b` per program. `DS-43` is right that a
stored census can go stale and that one implementation must serve both callers,
but "derived on demand" was read as "derived again by every caller".

**Recommendation.** Keep the one function and let `03a` persist the per-program
census in the plan part (not only the per-family union), then have `03b` read
its program's entry and re-derive only when the entry is absent or its graph
hash does not match. That keeps `DS-43`'s no-staleness rule — the entry is keyed
by the graph hash — while removing a second pass. If the plan part is judged too
large, persist the census as a per-program sidecar keyed by `program_sha256`;
either way it is derived once per graph version.

---

## `PA-7` — Pair rows are emitted for every solid state, but P0 binds one state per task

**Evidence:** `requirements/graph-content.md` §4.1 (pair emission rule);
`implementation/pipeline/extraction/graph-construction.md` ("take the named
endpoints of the state"); `DS-34` (P0 tasks refer to the final solid state only;
P1 adds one named intermediate state).

**Measured context.** In
`runs/current_cadevolve1000_10k_regen_20260613`, 20,135,608 relations for 1,000
programs. Pairwise comparison relations are 16,465,614 of them (82%):
`perpendicular_to` 5.07M, `parallel_to` 3.12M, `longer_than` 2.53M,
`shorter_than` 2.53M, `same_length_as` 1.43M, `opposite_to` 1.35M,
`distance_to` 0.44M. Containment, selection, and kernel-ID relations are the
remaining 18%. The same artifact holds 2,310 solid states for 1,000 programs,
so roughly 2.3 states per program.

**Why it bites.** The new pair emission rule already fixes most of the old
quadratic mass — named endpoint × candidates is linear, and the length
comparisons become search-time computations. What it does not fix is *state
scope*: pair rows are emitted for every solid state, while a P0 task can only
bind the final state and a P1 task binds one named intermediate state. Pair rows
for the other states are written, sorted, hashed, read by `03`, and never used.
At 2.3 states per program that is roughly half or more of the dominant relation
mass, and a matching share of the `02c` write and the `03` read.

**Recommendation.** Make pair emission state-scoped by implementation scope:
final state only in P0; final plus the one named intermediate state in P1.
Per-entity rows, containment rows, and effect measurements stay total over all
states, because `DS-34` and the topology-change answers need them. This is a
requirement-level sentence in `graph-content.md` §4.1, not an implementation
tuning knob, and it changes `graph_schema_version` semantics — decide it now,
before any graph is written.

---

## `PA-8` — One-row Parquet parts for cheap per-program units

**Evidence:** `implementation/run-contract.md:141-152` (run directory) and
`:243-247` (one part per program for `01d`, `02a`, `02b`; a three-file directory
per program for `02c`).

**Why it bites.** A 1,500-program run writes 1,500 one-row Parquet files for
`01d`, 1,500 for `02a`, 1,500 for `02b`, and 4,500 for `02c` — about 9,000 files
per run, each with a footer and page overhead, before failures. A one-row part
whose payload is a few kilobytes is mostly metadata. Resume also opens every
part to collect unit keys. The docs' own measured artifact used 10 shards of
100 programs for 164 MB of graph, which is the shape that works.

**Why it is only Medium.** The absolute bytes are small and local filesystems
handle 10^4 files. The cost becomes real on object storage, on network
filesystems, and in `05`'s hash-everything pass.

**Recommendation.** Keep the part-is-completion-marker rule for expensive units
(`02b`, `02c`) where losing a part costs 30 seconds of execution, and allow
*batched* parts for cheap units (`01d`, `02a`) — one part per 100 programs, with
a `unit_key` column and per-unit row groups so resume can still skip at unit
granularity. A crash then loses at most 100 normalizations or AST extractions,
which are milliseconds each, not 100 executions.

---

## `PA-9` — Answer evidence is canonical JSON per row, and its size has no bound

**Evidence:** `requirements/release-dataset-contract.md:100-106`
(`gold_answer_json`, `tolerance_json`, `answer_evidence_json`);
`:176-181` ("the answer evidence is small enough to keep with the task");
`03b` (`answer_equivalent_set` is "one entry per remaining candidate");
`05` re-parses `gold_answer_json` and `answer_evidence_json` per row;
`implementation/artifacts.md:53,60` ("not one JSON string per row", "JSON parsing
is not used on a bulk data path"); `DS-23`; `DS-39` (41× size, 57× read).

**Why it bites.** Two separate problems. First, a policy inconsistency: the docs
ban per-row JSON on bulk paths and then put three JSON columns in the release
table, which `05` parses per row. At 10,000 rows the cost is small, but the
release is meant to grow, and the rule exists precisely to stop this pattern
from being re-adopted. Second, the unbounded field: `answer_equivalent_set` has
one entry per remaining candidate. For a numeric answer, the remaining set is
every candidate that produces the same value — up to `max_state_entities` (500)
entries of `{subject, answer}` per task. "Small enough" is an assumption, not a
bound, and the release contract does not state a maximum.

**Recommendation.** Give the answer columns typed Parquet schemas, the
way the graph already is, and hash a canonical byte form produced by the
serializer rather than storing that byte form in the row. Keep
`answer_evidence_json` only if a consumer genuinely needs the bytes, and then
state a maximum size and a behaviour when it is exceeded. For the release,
`answer_equivalent_set` can be reduced to the shared answer plus its size; the
full set belongs in the task-definition artifact, which `05` can read when it
needs to recheck uniqueness.

---

## `PA-10` — `02c` recomputes hashes `02b` already produced

**Evidence:** `implementation/pipeline/extraction/graph-persistence.md:421`
("When `02b` provides only `entity_id`, `02c` recomputes the hash from the
canonical entity table") and `:424` (`runtime_extraction_result_sha256` is
computed by `02c`); `02b`'s success result already carries
`runtime_extraction_result_sha256`, and `02b` derived `entity_id` from the
fingerprint.

**Why it bites.** Two implementations of the same canonical hash across Python
and Go must agree byte for byte, and the contract makes a mismatch a graph
rejection. That is a determinism risk disguised as validation. The cost is
secondary: re-hashing each topology entity's geometric fingerprint and the whole
runtime result in Go is a few seconds per 1,000 programs, but it is pure
duplication.

**Recommendation.** Require `02b` to emit `fingerprint_sha256` alongside
`entity_id`, and require `02c` to copy `runtime_extraction_result_sha256` rather
than recompute it. Keep recomputation as a `--force`/test check, not the normal
path. This removes the second implementation from the critical path.

---

## `PA-11` — `04` names the program text as a per-task input

**Evidence:** `implementation/pipeline/04-render-prompt-and-choices.md:52-57`
("`04` renders one task from three inputs", one of which is `NormalizedProgram`,
"selected by the definition's `program_sha256`"); `run-contract.md:251` (the
unit is a task).

**Why it bites.** Parts are keyed by program, so a per-task read re-opens the
same file once per task. With ~7 tasks per program that is a small constant, but
it is a constant that scales with task count rather than program count, and it
invites a hash lookup against the whole normalized-program table.

**Recommendation.** Make the render unit a program: load its text and its
definitions once, render every task, flush. This also matches the flush rule
(`04` already writes one part per program).

---

## `PA-12` — The runtime result is written, read, and written again

**Evidence:** `implementation/pipeline/extraction/cadquery/algorithm/runtime.md`
("The child writes the runtime tables … The parent reads nothing until the child
exits, then validates the status, schema, and hashes");
`run-contract.md` §4.1 (temp file, fsync, rename).

**Why it bites.** The child writes Parquet to a temp directory, the parent reads
it, validates it, and writes the artifact part — a full re-encode of every
runtime capture. The runtime capture is the largest per-program artifact before
the graph, so this is the largest avoidable I/O in `02b`.

**Recommendation.** Have the child write directly under
`<target>.tmp-<uuid>`; the parent validates schema and hashes and then performs
the rename and the directory fsync. The write rule is unchanged, the validation
is unchanged, and the re-encode disappears.

---

## `PA-13` — `01c` batch parts and `01d` per-program identity

**Evidence:** `run-contract.md:322-323` (`01c` writes
`part-<sequence>-<sha256>.parquet`; `01d` identity is "`01c` pool part hash for
the program").

**Why it bites.** `01c` batches many programs into one part, but `01d`'s
identity names that batch's hash. Re-fetching one batch — which a supplemental
delta or a repair does — invalidates the normalization of every program in the
batch, not just the refetched one. The mismatch is invisible at 1,500 programs
and becomes a real recompute when a batch is large.

**Recommendation.** Either key `01d` on the program's row hash rather than the
part hash, or write `01c` deltas as their own parts so a delta cannot rewrite an
existing batch.

---

## `PA-14` — The `02b` cache key's "execution environment identifier" is undefined

**Evidence:** `run-contract.md:74` (`execution_environment` is `platform`,
`timeout_seconds`, `memory_limit_bytes`) and `:326` ("execution environment
identifier" in the `02b` cache key); `run-contract.md` §2 ("a resume on a
different machine reuses the run directory and recomputes only the `02b` units
whose environment changed").

**Why it bites.** If `platform` means `linux/amd64`, a cross-machine resume
reuses all 1,500 executions, which is the intent. If it includes hostname,
kernel, CPU model, or a container ID, a cross-machine resume recomputes all
1,500 executions — about 12.5 hours of CPU — and the sentence in §2 is false.
The docs do not say which fields are in the identifier.

**Recommendation.** Enumerate the exact fields in the environment record, forbid
host-specific values, and state that a cross-machine resume is a cache hit when
the enumerated fields match. This is one sentence, and it prevents the most
expensive possible mistake in the resume rule.

---

## What the docs already get right

Do not re-open these; they are the reason the audit is short.

- **Parquet everywhere, with measurements.** `DS-23`, `DS-39`, `DS-40` reject
  JSON rows and a relational graph store with numbers, not taste, and
  `DS-40` already chooses streaming reads over whole-table materialization.
- **Column projection and row-group/shard reads** in `01a`, and reserve rows
  fetched but not normalized in `01c`.
- **No full enumeration** of the task space (`03`), a bounded 20%/3-round
  expansion (`03c`), and a recorded miss instead of a padded task.
- **One derivation, two readers** for the conditional share and the support
  tables, so `03a` and `05` cannot disagree.
- **A run is incremental** with atomic parts, a shared cache, and hardlinked
  cache hits (`DS-44`).
- **The pair emission rule** is already linear per named endpoint; `PA-7` asks
  only for state scope on top of it.
- **Tolerance resolved once per run**, not per measurement.
- **Dictionary encoding** for closed enums, fixed-width UUID keys, and native
  UUID logical types (`DS-41`).

## Cost budget

Order-of-magnitude only; the point is which term dominates and which finding
addresses it.

| Cost | Driver | Order of magnitude | Finding |
|---|---|---|---|
| `02b` execution | 1,500 programs × 30 s | 12.5 h CPU ceiling | `PA-1` |
| `02b` process lifecycle | 1,500 × 2.1–2.8 s import | ~1.2 h CPU, 451 MiB/worker | `PA-1` |
| `02c` graph rows | ~20 k relations/program | ~30 M rows, ~250 MB | `PA-7` |
| `03b` construction | 1.2–1.5 × 10^5 attempts | 10^5 cover searches | `PA-3`, `PA-4` |
| `03b` graph reads | 5–8 targets per program | 5–8 × graph bytes | `PA-5` |
| Replan rebuild | one delta, all units stale | 10^4 definitions + 10^4 renders | `PA-2` |
| `05` export | 10^4 rows, one pass each | seconds to a minute | `PA-9` |

## Priority order

1. `PA-2` — decide unit identity vs replan before any per-program part is
   written; it is the difference between a cheap loop and a full rebuild.
2. `PA-1` — fix the execution boundary in `02b`/`runtime.md`; it is a measured
   7–9% tax on every execution and a concurrency cap.
3. `PA-3`, `PA-4`, `PA-5` — give `03b` one budget, one graph read, and one cost
   budget. These three are one design change.
4. `PA-7` — state-scope pair emission, before `graph_schema_version` is fixed.
5. `PA-6`, `PA-8`, `PA-9` — remove the second census pass, batch the cheap
   parts, and bound the answer evidence.
6. `PA-10`–`PA-14` — clean up duplication and ambiguity; each is a paragraph or
   a small contract change.

## Measurement log

- `import cadquery`: 2,772.8 ms (cold child, `pass` baseline 18.4 ms).
- `import cadquery` + one box + `Volume()`: 2,077.6 ms.
- Peak RSS of a child that only imports CadQuery: 451 MiB.
- Command shape:
  `python -c 'import time,subprocess,sys; ... subprocess.run([sys.executable,"-c","import cadquery"])'`
  from the repository `.venv`.
- Graph counts from `runs/current_cadevolve1000_10k_regen_20260613/graph/graph_report.json`:
  677,937 nodes; 20,135,608 relations; 10,205,884 measurements; 2,310 solid
  states; the breakdown by CAD graph relation type is quoted in `PA-7`.
