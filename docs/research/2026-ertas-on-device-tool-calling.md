# ert.as: Phi-4-Mini vs Gemma 4 vs Qwen3-4B for on-device tool calling (2026)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations.

## Citation

Yang, E.X. (2026) 'Phi-4-Mini vs Gemma 4 vs Qwen3-4B: Tool Calling', *ert.as*, 10 May, updated
7 August. Available at: `ertas.ai/blog/on-device-tool-calling-2026-qwen3-gemma4-phi4`.

- Reference: `prior-art.md`, reference [5].

## What it is

A three-way comparison of the credible on-device tool-calling bases — Qwen3-4B-Instruct-2507,
Gemma 4 E4B (4B effective parameters), Phi-4-Mini-Instruct (3.8B) — on out-of-the-box BFCL v4,
mobile latency, and post-fine-tune accuracy on a five-tool customer-support agent. The author
flags the numbers as illustrative ranges synthesized from public benchmarks and vendor cards,
not first-party measurements.

## Findings

- Out of the box: Qwen3-4B leads (high 80s on BFCL v4 composite), Gemma 4 E4B close behind
  (mid-to-high 80s, native function-call special tokens), Phi-4-Mini low-to-mid 80s but with a
  noticeably stronger reasoning chain.
- After QLoRA fine-tuning (rank 32, three epochs, ~600 examples) all three typically clear the
  ~95% joint-accuracy bar on the held-out tool set; the composite spread collapses by roughly
  70%.
- All three shipped with llama.cpp tool-call parser support as of March 2026. Licenses: Qwen3-4B
  Apache 2.0, Gemma 4 E4B Apache 2.0, Phi-4-mini MIT.
- Phi-4-Mini is the smallest and fastest (~15–20% faster than Qwen3-4B); Gemma 4 E4B produces
  ~15–20% fewer output tokens per tool call because of its native tokens.

## Why it matters for CAD-QA

Another instance of post-fine-tune parity: the choice between these bases is dominated by
latency, license, and reasoning quality rather than raw base accuracy. Also a concrete data
point that native function-call tokens (Gemma 4) reduce output variance, which matters when a
harness parses structured tool calls.

## Related

- `2026-distil-labs-tool-calling-families.md`
- `2026-slm-agentic-tool-calling.md`
