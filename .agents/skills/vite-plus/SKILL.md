---
name: vite-plus
description: Use Vite+ (`vp`) for the task-browser frontend and any Vite-based app in this repository: install, dev, check, test, build, and the built-in-command vs package-script distinction. Use when working in `tools/manual-verification/task-browser/` or adding a Vite+ app.
---

# Vite+

This repository's task browser is a Vite+ app. Vite+ is the unified toolchain
behind the `vp` CLI: one tool combining Vite, Rolldown, Vitest, tsdown, Oxlint,
Oxfmt, and Vite Task, plus runtime and package-manager management.

Docs are local at `node_modules/vite-plus/docs` (inside the app) or online at
https://viteplus.dev/guide/. Run `vp help` and `vp <command> --help`.

## Built-in commands vs scripts

`vp <name>` runs a built-in command. `vp run <name>` runs a `package.json`
script or a `vite.config.ts` task. Scripts cannot overwrite built-ins, so
`vp dev` and `vp run dev` may do different things. Check `package.json` and
`vite.config.ts` first.

## Task browser

From `tools/manual-verification/task-browser/`:

```bash
pnpm install       # first checkout
pnpm dev           # Vite dev server, proxies /api to 127.0.0.1:8765
pnpm build         # tsc -b && vp build, writes dist/
vp check           # format, lint, and check the code
```

Start the API from the repository root:

```bash
uv run python tools/manual-verification/task_browser.py \
  --release runs/run0001/05-validate-and-export-release/current
```

The API serves `dist/` at `http://127.0.0.1:8765` when the app is built. The app
contract is `docs/dataset/implementation/devtools/task-browser.md`.

## Running scripts

Run TypeScript and JavaScript files with `vpx <file>`, for example
`vpx ./scripts/seed.ts --dry-run`. It handles enums, decorators, JSX, and
tsconfig `paths`, so do not add `tsx` or `ts-node`. `vpx --watch <file>` reruns
the file when a file it uses changes. `vp node <file>` runs plain Node.js.

## Tool versions

Run `vp toolchain` to show versions and relationships in the active Vite+
release. Add a tool name to select part of the graph, for example
`vp toolchain vite`. Use `--global` to ignore the local `vite-plus` package. Use
`vp why <package>` to show the package-manager dependency graph.

## Review checklist

- [ ] Run `vp install` after pulling remote changes and before getting started.
- [ ] Run `vp check` and `vp test` to format, lint, and check the code.
- [ ] Check for `vite.config.ts` tasks or `package.json` scripts needed for
      validation; run them with `vp run <script>`.
- [ ] If setup, runtime, or package-manager behavior looks wrong, run
      `vp env doctor` and include its output when asking for help.
