# Dataset browser

**Status:** available, 2026-11-23; broadened from a task-list viewer into the one
human review frontend on 2026-11-27. Browsing a release table or the checked-in
gold task oracles is `available`; the review queue, the clue-coloured scene, and
the dataset release task review ledger write are `planned` for `P0-W2`. Gold mode
stays read-only.

`tools/manual-verification/dataset_browser.py` serves a local JSON API over one
release `release.parquet`, one directory of
[task-construction oracles](../pipeline/testing/oracles/task-construction/README.md),
or one release run's review inputs. `tools/manual-verification/dataset-browser/`
is a Vite+ app that lists, filters, and opens tasks; the 3D view is three.js.

It is the one human frontend for dataset review. A sample is a view over the
release, not a second tool: the browser selects and orders the tasks and records
the verdicts, and `05` reads the same ledger. There is no separate batch
renderer, contact sheet, or per-task PNG.

## Views

The primary view is **Tasks**. A top-level **Other** menu opens the review
documents that are not task rows:

| View | Input | What a person does |
|---|---|---|
| Tasks | release table, or gold oracles | Opens one task: prompt, gold answer, and the final solid state with the target and clue-bound entities in distinct colours. |
| Review queue | release table and the five support tables | Works the sample in coverage-gap order. It is a sort over the Tasks view, not a second list. |
| Dataset release absence ledger | `absence-ledger.parquet` | Reads why each absent program, capability, or capacity was dropped. Read-only. |
| Dataset release geometry residual ledger | `residual-ledger.parquet` | Reads the CAD graph kernel-oracle differential result per drawn program. Read-only. |

The absence and residual ledgers have no human verdict. Their rows are derived
from upstream artifacts, so the browser shows them and never asks for a `pass`
or a `defect`. A person who needs to question one of those rows does it outside
this contract, against the evidence the row cites. The task review ledger is the
only ledger the browser writes.

## Invocation

Development uses two terminals, so the frontend hot-reloads while the API keeps
the task rows and the scene cache in memory:

```bash
uv run python tools/manual-verification/dataset_browser.py \
  --release runs/run0001/05-validate-and-export-release/current

cd tools/manual-verification/dataset-browser
pnpm install
pnpm dev
```

`--release` and `--oracles` are mutually exclusive and one is required.
`--oracles` takes the directory of gold records, so the gold set is reviewable
before any release exists:

```bash
uv run python tools/manual-verification/dataset_browser.py \
  --oracles docs/dataset/implementation/pipeline/testing/oracles/task-construction
```

Open the Vite URL (default `http://localhost:5173`). Vite proxies `/api` to
`http://127.0.0.1:8765`.

For one command, build the app once and serve the build from the API origin:

```bash
cd tools/manual-verification/dataset-browser && pnpm build
uv run python tools/manual-verification/dataset_browser.py \
  --release runs/run0001/05-validate-and-export-release/current
```

Open `http://127.0.0.1:8765`. `--host`, `--port`, `--cache-dir`, and
`--web-dist` override the defaults. `--review-ledger` moves the ledger path,
`--reviewer` names the reviewer and defaults to the local user, and
`--definitions` and `--graph` supply the `TaskDefinition` set and the CAD graph
that colour clue-bound entities. `--definitions` and `--graph` are `planned`;
without them the scene is one neutral colour and the clue labels are absent.

## Inputs

One of:

- the release `release.parquet` row set, with the Python fence in each row's
  prompt as the program the reviewer reads;
- the gold-oracle directory, one `<slug>.json` per record; the record's
  `program.text` is the program and its answer, clues, gold query, coverage,
  and exclusions are the review material.

The release table carries no separate program column, and the prompt is the
reviewer's own view of the program, so the fence is the right input. The API
executes the program: run it only on a release you generated, or on the
checked-in gold records. Gold rows take their split and subset from the input
(`gold`/`oracle`), not from a release column.

The review queue also reads the five support tables under `support/`, which the
release carries. The clue-coloured scene additionally reads the `TaskDefinition`
set and the CAD graph: the release row does not carry the clue-to-entity binding.
The browser matches a graph entity to the shape by the geometric fingerprint —
face centroid, area, normal, and bounding box; edge endpoints and length; vertex
point — and two entities in one state and category with the same fingerprint are
rejected at graph build, so the match is unique.

When a release has already exported, `release.parquet`, the three ledgers, and
`support/` sit in the release directory. The browser reads them from there;
`--absence-ledger` and `--residual-ledger` override the paths while the release
is still being reviewed.

## Review queue

The queue applies the sampling matrix in the
[`05` review gate](../pipeline/05-validate-and-export-release.md#review-gate):
the cross product of clue type, answer meaning, answer format, and task
reasoning step count, restricted to the cells the support tables support and the
release contains. The matrix rule has one home in `05`; the browser only orders
the tasks the rule selects.

The order is the coverage gap, largest first:

1. a task whose required cell has no current `pass`;
2. then a task in a reasoning step tier of 6–10 that is below the 30-pass target,
   the tier with the larger remaining count first;
3. then the higher task reasoning step count;
4. then a stable hash of the release seed and `task_id`, so two runs open the
   same queue.

A task with a current `pass` stays in the list with its verdict and review date;
the queue never hides reviewed work. A `defect` stays in the cell's gap until
the task is re-reviewed.

## Outputs

The tool writes no release file. It writes the
[dataset release task review ledger](../../requirements/release-dataset-contract.md#dataset-release-task-review-ledger)
for a release row the reviewer approves or rejects, at
`runs/manual_verification/dataset_browser/<release_id>/review-ledger.parquet`;
`--review-ledger` overrides the path and `--reviewer` names the reviewer. `05`
copies the ledger into the release and never renders.

It caches one tessellation per program under
`runs/manual_verification/dataset_browser/cache/<program_sha256>-v1.json`, so
tasks that share a program share a scene. It writes no PNG and no per-task card.
`node_modules/` and `dist/` are ignored; the frontend code and `pnpm-lock.yaml`
are checked in.

## Dataset release task review ledger

The approval action appends the row the
[release contract](../../requirements/release-dataset-contract.md#dataset-release-task-review-ledger)
defines: `task_id`, `definition_sha256`, `prompt_sha256`, `verdict`, `reviewer`,
`reviewed_at`, `defect_note`, `scene_sha256`, and `scene_version`. The key is
`(task_id, definition_sha256, prompt_sha256)`; a later row with the same key
supersedes an earlier one, and `pending` never satisfies the review gate. The
browser writes release rows only; a gold record's verification stays in its JSON
record.

`scene_sha256` is SHA-256 over the canonical scene payload the browser served, so
the evidence is the scene the reviewer orbed, not a screenshot. The scene is
reproducible from `program_sha256`, the `TaskDefinition`, the CAD graph, and
`scene_version`.

## API

| Route | Returns |
|---|---|
| `GET /api/facets` | Task count, the input (`release` or `gold`), and the filter values the data contains. |
| `GET /api/tasks?offset=&limit=&search=&split=&subset=&target_category=&answer_meaning=&order=&seed=` | One page of task summaries. `order=random` with a `seed` is stable. |
| `GET /api/tasks/<task_id>` | Prompt (null for a gold row), program, answer, choices, diagnostics, and the gold record. |
| `GET /api/tasks/<task_id>/scene` | Tessellated triangles and line segments, bounds, legend, and counts. |
| `GET /api/review-queue?offset=&limit=` | The review queue in coverage-gap order, with each task's cell, tier, and latest verdict. `planned`. |
| `GET /api/reviews?task_id=` | The latest verdict for the task, or none. |
| `POST /api/reviews` | Appends one ledger row; the body carries `task_id`, `verdict`, `defect_note`, `scene_sha256`, and `scene_version`. |
| `GET /api/absence-ledger?offset=&limit=` | Rows from the dataset release absence ledger. Read-only. `planned`. |
| `GET /api/residual-ledger?offset=&limit=` | Rows from the dataset release geometry residual ledger. Read-only. `planned`. |

`limit` is capped at 200. The scene is cached by `program_sha256` and
`scene_version`, so a change to the tessellation invalidates it.

## Frontend

The app is three columns: the task list with the filter bar, the 3D view, and the
detail panel. The detail panel groups its content into `Task`, `Solution`, and
`Other`, in that order. `Task` holds the `Full prompt`, the question, the
program, and, for a gold record, the clue chain; `Solution` holds the answer,
the verification, and the gold query; `Other` holds the metadata panels behind
disclosures. The answer sits after the clue chain, so the reviewer reads what
narrows the target before seeing the answer. Panel open state lives in the
detail pane, so a panel the reviewer opened stays open when they switch tasks.
The `Full prompt` panel is the release prompt for a release row; a gold record
has no `04` render, so it assembles the record as one plain block: the program
in a Python fence, the question, and the clue statements. A release row's
detail pane carries the approval control: `pass` and `defect`, a note required
on `defect`, and the task's latest verdict. The program and gold query are
syntax-highlighted with `prism-react-renderer`. The 3D view uses three.js
`OrbitControls` with `Z` up, so the view matches the program frame, and a corner
`ViewHelper` shows the axes. The target and each clue-bound entity are drawn in a
distinct colour and labelled with the clue number.

`vp check` formats, lints, and checks the app; `vp build` writes `dist/`. The
workflow is the `vite-plus` skill. `vp test` is available for component tests
when they are added.

## Gold oracles

Gold mode is read-only. It writes no record and changes no verification status;
the reviewer edits the JSON through the documented procedure in
[`task-construction/README.md`](../pipeline/testing/oracles/task-construction/README.md).
The approval action above applies to release rows, not to a record's
`verification` block.

The gold set has no rendered prompt. Each record carries a hand-authored
`question`, which is the list preview and the first block of the `Task` group.
The detail panel then shows these groups when the row is a gold record:

- `Task`: the `Full prompt`, the question, the program, and the `Clue chain`,
  each clue's order, clue type, reduction form, statement, and narrowing counts;
- `Solution`: the answer, then `Verification` (the record status, who verified
  it and when, the rationale, and the recorded gold-query status, stdout, and
  date), then `Gold query` (the code, its expected stdout, and its hash);
- `Other`: `Task description` (target category, possible-answer count, reasoning
  steps, answer meaning and format, geometry requirement, and the uniqueness
  rule), `Coverage` (the vocabulary cell the record pins), `Excluded` (each
  expected absence and its reason), `Notes`, and `Environment`.

Every panel is a disclosure. The question starts closed because the selected
task's question is already visible in the task list. `Verification` is the one
panel open on first render; the rest open when the reviewer opens them and stay
that way across task switches. The 3D view renders the record's program the same
way it renders a release program.

## Human step

The reviewer opens the review queue, opens a task, reads the prompt, orbits the
final solid state, and checks that each highlighted entity is the one the clue
names, that the answer matches the geometry, and that the wording is clear. The
verdict is recorded with the approval control, which appends `pass` or `defect`
(with the note) and the scene hash to the dataset release task review ledger.
The reviewer does not hand-edit the ledger.

In gold mode the reviewer opens each record, orbits the program's final solid
state, and checks that the answer is the one a careful human would give, that
the clue chain is true, narrowing, and necessary, and that the coverage cell is
the one intended. The reviewer then follows the record procedure in
[`task-construction/README.md`](../pipeline/testing/oracles/task-construction/README.md#6-how-to-add-a-record)
to check, record, and accept the record.

## What this does not prove

- that the answer is true; the answer checks are in
  [`../pipeline/03-task-generation/03b-construct-task-definitions/README.md`](../pipeline/03-task-generation/03b-construct-task-definitions/README.md);
- that the prompt is natural or unambiguous;
- that the sample is representative beyond the matrix;
- that the reviewer looked at the scene `scene_sha256` names; the hash proves
  which scene the browser served, not what the reviewer did with it;
- that a derived absence disposition is right; the browser shows the row and its
  evidence and cannot re-derive the upstream rejection;
- that the geometry residual bound covers a defect class the CAD graph
  kernel-oracle differential cannot detect.

In gold mode it also does not prove that the gold query still prints the
recorded stdout: that is the machine check in
[`verify_task_oracles.py`](../../../../tools/manual-verification/verify_task_oracles.py),
and the panel shows the date it was recorded. It does not prove that `03b`
reproduces the record; that test lands with the constructor.

The scene shows clue colours only when `--definitions` and `--graph` name a
`TaskDefinition` set and CAD graph built from the same program; the release table
alone has no clue-to-entity binding.
