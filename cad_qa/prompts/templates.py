"""Rule-based prompt templates."""

PROMPT_VERSION = "cadqa_prompt_v2"


def checklist_prompt(source_code: str, clues: list[str], answer_format: str) -> str:
    clue_lines = "\n".join(f"- {clue}" for clue in clues)
    return (
        "Given the CadQuery script below, answer the question by reasoning "
        "about the CAD construction.\n\n"
        "```python\n"
        f"{source_code.rstrip()}\n"
        "```\n\n"
        "Identify the target that satisfies all of these constraints:\n"
        f"{clue_lines}\n\n"
        f"Return exactly one {answer_format}."
    )
