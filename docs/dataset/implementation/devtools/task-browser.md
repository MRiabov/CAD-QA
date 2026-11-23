# Task browser

**Status:** available, 2026-11-23. The first owner-review tool for a whole
release table: a task list, a filter bar, and an interactive 3D view.

`tools/manual-verification/task_browser.py` serves a local JSON API over one
release `release.parquet`. `tools/manual-verification/task-browser/` is a Vite+
app that lists, filters, and opens tasks; the 3D view is three.js.

## Invocation

Development uses two terminals, so the frontend hot-reloads while the API keeps
the release table and the scene cache in memory:

```bash
uv run python tools/manual-verification/task_browser.py \
  --release runs/run0001/05-validate-and-export-release/current

cd tools/manual-verification/task-browser
pnpm install
pnpm dev
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

- the release `release.parquet` row set;
- the Python fence in each row's prompt, which is the program the reviewer
  reads.

The release table carries no separate program column, and the prompt is the
reviewer's own view of the program, so the fence is the right input. The API
executes that fence: run it only on a release you generated.

## Outputs

The tool writes no release file. It caches one tessellation per program under
`runs/manual_verification/task_browser/cache/<program_sha256>-v1.json`, so tasks
that share a program share a scene. `node_modules/` and `dist/` are ignored; the
frontend code and `pnpm-lock.yaml` are checked in.

## API

| Route | Returns |
|---|---|
| `GET /api/facets` | Task count and the filter values the release contains. |
| `GET /api/tasks?offset=&limit=&search=&split=&subset=&target_category=&answer_meaning=&order=&seed=` | One page of task summaries. `order=random` with a `seed` is stable. |
| `GET /api/tasks/<task_id>` | Prompt, program, answer, choices, and diagnostics. |
| `GET /api/tasks/<task_id>/scene` | Tessellated triangles and line segments, bounds, legend, and counts. |

`limit` is capped at 200. The scene is cached by `program_sha256` and
`scene_version`, so a change to the tessellation invalidates it.

## Frontend

The app is three columns: the task list with the filter bar, the 3D view, and
the detail panel. The detail panel keeps the answer visible and puts the prompt,
diagnostics, usage, and program behind disclosures. The 3D view uses three.js
`OrbitControls` with `Z` up, so the view matches the program frame, and a corner
`ViewHelper` shows the axes.

`vp check` formats, lints, and checks the app; `vp build` writes `dist/`. The
workflow is the `vite-plus` skill. `vp test` is available for component tests
when they are added.

## Human step

The reviewer filters to a slice, opens a task, reads the prompt, orbits the
final solid state, and checks that the gold answer is defensible and that the
prompt names the entity the answer measures. A defect is recorded in the review
ledger with the task and the note.

## What this does not prove

- that the answer is true; the answer checks are in
  [`../pipeline/03-task-generation/03b-construct-task-definitions/README.md`](../pipeline/03-task-generation/03b-construct-task-definitions/README.md);
- that the prompt is natural or unambiguous;
- that the sampled slice is representative of the release.

The release table carries no clue-to-entity binding, so the 3D view shows the
final solid state in one neutral colour. Clue colours need the `TaskDefinition`
and the CAD graph, which the review pack reads when it lands.
