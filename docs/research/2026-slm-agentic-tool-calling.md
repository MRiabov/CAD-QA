# Small LLMs for agentic tool calling: targeted SFT on OPT-350M (2026)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations.

## Citation

Jhandi, P., Kazi, O., Subramanian, S. and Sendas, N. (2026) 'Small Language Models for
Efficient Agentic Tool Calling: Outperforming Large Models with Targeted Fine-tuning', arXiv
preprint arXiv:2512.15943. Accepted at the AAAI 2026 Workshop on Agentic AI Benchmarks and
Applications for Enterprise Tasks. Available at: `arxiv.org/abs/2512.15943`.

- Reference: `prior-art.md`, reference [6].

## What it is

A feasibility study on replacing large general-purpose LLM models in tool-calling workflows with
a fine-tuned small LLM model. The student is `facebook/opt-350m`, fine-tuned for a **single
epoch** with the
Hugging Face TRL `SFTTrainer`, over tasks including summarization, query answering, and
structured data interpretation.

## Findings

- The fine-tuned OPT-350M reaches **77.55%** pass on ToolBench.
- Baselines: ChatGPT-CoT 26.00%, ToolLLaMA-DFS 30.18%, ToolLLaMA-CoT 16.27%.
- The authors frame this as evidence that thoughtful design and targeted training of small LLM
  models can replace much larger general-purpose LLM models on narrow tasks at much lower cost.

## Why it matters for CAD-QA

The strongest small-case point that targeted fine-tuning can dominate base size on a narrow
tool-calling task. It is a single-epoch, single-task result, so it is a proof of possibility,
not a recipe; but it is the counterweight to "small means no gain" and supports fixing the
recipe before changing the base.

## Related

- `2026-distil-labs-tool-calling-families.md`
- `2026-learning-what-to-learn.md`
