# Manual verification scripts

Owner-run checks whose output a person looks at or reads: a render, a task card,
a sampled slice of a release. Nothing here is imported by the pipeline, run in
CI, or a substitute for a test.

## When a script belongs here

When the check needs human judgement — is the highlighted entity the one the
clue names, does this prompt read clearly, does this answer match the geometry —
and an automated check cannot make it. A script that becomes load-bearing moves
into the package and gets a test.

## Conventions

- One file per check, named `<verb>_<object>.py` (`render_task.py`).
- Run it by hand: `uv run python scripts/manual-verification/<name>.py --help`.
- Take the dataset path and the row selector as arguments; never hardcode a run.
- Write output under `runs/manual_verification/<name>/`, which git ignores.
- Print the inputs next to the output path. A render without the prompt it came
  from is not verifiable.
- Build against the contracts in `docs/`, not against the code being replaced.

## Scripts

| Script | What it shows | Status |
|---|---|---|
| `render_task.py` | One release row's program rendered from its final solid state, with the prompt, gold answer, and clue bindings printed beside it. | `missing` |

`render_task.py` is the first-release fallback for the
[visual review pack](../../docs/dataset/implementation/devtools/review-pack.md):
it renders the solid state, and the reviewer reads the task from the printed
card.
