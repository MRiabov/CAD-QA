# Task browser

**Status:** available, 2026-11-23. The first owner-review tool for a whole
release table or the checked-in gold task oracles: a task list, a filter bar,
and an interactive 3D view.

`tools/manual-verification/task_browser.py` serves a local JSON API over one
release `release.parquet` or one directory of
[task-construction oracles](../pipeline/testing/oracles/task-construction/README.md).
`tools/manual-verification/task-browser/` is a Vite+ app that lists, filters,
and opens tasks; the 3D view is three.js.

## Invocation

Development uses two terminals, so the frontend hot-reloads while the API keeps
the task rows and the scene cache in memory:

```bash
uv run python tools/manual-verification/task_browser.py \
  --release runs/run0001/05-validate-and-export-release/current

cd tools/manual-verification/task-browser
pnpm install
pnpm dev
```

`--release` and `--oracles` are mutually exclusive and one is required.
`--oracles` takes the directory of gold records, so the gold set is reviewable
before any release exists:

```bash
uv run python tools/manual-verification/task_browser.py \
  --oracles docs/dataset/implementation/pipeline/testing/oracles/task-construction
```

Open the Vite URL (default `http://localhost:5173`). Vite proxies `/api` to
`http://127.0.0.1:8765`.

For one command, build the app once and serve the build from the API origin:

```bash
cd tools/manual-verification/task-browser && pnpm build
uv run python tools/manual-verification/task_browser.py \
  --release runs/run0001/05-validate-and-export-release/current
```

Open `http://127.0.0.1:8765`. `--host`, `--port`, `--cache-dir`, and
`--web-dist` override the defaults.

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

## Outputs

The tool writes no release file. It caches one tessellation per program under
`runs/manual_verification/task_browser/cache/<program_sha256>-v1.json`, so tasks
that share a program share a scene. `node_modules/` and `dist/` are ignored; the
frontend code and `pnpm-lock.yaml` are checked in.

## API

| Route | Returns |
|---|---|
| `GET /api/facets` | Task count, the input (`release` or `gold`), and the filter values the data contains. |
| `GET /api/tasks?offset=&limit=&search=&split=&subset=&target_category=&answer_meaning=&order=&seed=` | One page of task summaries. `order=random` with a `seed` is stable. |
| `GET /api/tasks/<task_id>` | Prompt (null for a gold row), program, answer, choices, diagnostics, and the gold record. |
| `GET /api/tasks/<task_id>/scene` | Tessellated triangles and line segments, bounds, legend, and counts. |

`limit` is capped at 200. The scene is cached by `program_sha256` and
`scene_version`, so a change to the tessellation invalidates it.

## Frontend

The app is three columns: the task list with the filter bar, the 3D view, and
the detail panel. The detail panel groups its content into `Task`, `Solution`,
and `Other`, in that order. `Task` holds the `Full prompt`, the question, the
program, and, for a gold record, the clue chain; `Solution` holds the answer,
the verification, and the gold query; `Other` holds the metadata panels behind
disclosures. The answer sits after the clue chain, so the reviewer reads what
narrows the target before seeing the answer. Panel open state lives in the
detail pane, so a panel the reviewer opened stays open when they switch tasks.
The `Full prompt` panel is the release prompt for a release row; a gold record
has no `04` render, so it assembles the record as one plain block: the program
in a Python fence, the question, and the clue statements. The program and gold
query are syntax-highlighted with `prism-react-renderer`. The 3D view uses
three.js `OrbitControls` with `Z` up, so the view matches the program frame, and
a corner `ViewHelper` shows the axes.

`vp check` formats, lints, and checks the app; `vp build` writes `dist/`. The
workflow is the `vite-plus` skill. `vp test` is available for component tests
when they are added.

## Gold oracles

It is read-only. It writes no record and changes no verification status; the
reviewer edits the JSON through the documented procedure in
[`task-construction/README.md`](../pipeline/testing/oracles/task-construction/README.md).

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

The reviewer filters to a slice, opens a task, reads the prompt, orbits the
final solid state, and checks that the gold answer is defensible and that the
prompt names the entity the answer measures. A defect is recorded in the review
ledger with the task and the note.

In gold mode the reviewer opens each record, orbits the program's final solid
state, and checks that the answer is the one a careful human would give, that
the clue chain is true, narrowing, and necessary, and that the coverage cell is
the one intended. The reviewer then follows the record procedure in
[`task-construction/README.md`](../pipeline/testing/oracles/task-construction/README.md#6-how-to-add-a-record)
to record the check and set `verified`.

## What this does not prove

- that the answer is true; the answer checks are in
  [`../pipeline/03-task-generation/03b-construct-task-definitions/README.md`](../pipeline/03-task-generation/03b-construct-task-definitions/README.md);
- that the prompt is natural or unambiguous;
- that the sampled slice is representative of the release.

In gold mode it also does not prove that the gold query still prints the
recorded stdout: that is the machine check in
[`verify_task_oracles.py`](../../../../tools/manual-verification/verify_task_oracles.py),
and the panel shows the date it was recorded. It does not prove that `03b`
reproduces the record; that test lands with the constructor.

The release table carries no clue-to-entity binding, so the 3D view shows the
final solid state in one neutral colour. Clue colours need the `TaskDefinition`
and the CAD graph, which the review pack reads when it lands.
