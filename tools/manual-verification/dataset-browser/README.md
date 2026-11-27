# CAD-QA dataset browser

Vite+ app for the dataset browser. The contract is
[`docs/dataset/implementation/devtools/dataset-browser.md`](../../../docs/dataset/implementation/devtools/dataset-browser.md).

```bash
pnpm install
pnpm dev
```

The dev server proxies `/api` to `http://127.0.0.1:8765`. Start the API from the
repository root:

```bash
uv run python tools/manual-verification/dataset_browser.py \
  --release runs/run0001/05-validate-and-export-release/current
```

`pnpm build` writes `dist/`, which the API serves at its own origin. Run
`vp check` for formatting, lint, and type checks.
