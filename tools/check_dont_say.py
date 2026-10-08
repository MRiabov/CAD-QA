#!/usr/bin/env python3
"""Don't-say checker for CAD-QA docs.

Reads the ``## Don't say`` table from ``docs/glossary.md`` and fails when a
banned term appears in a scanned doc. A Say term covers its own Don't-say
tokens (``Gold query program`` covers ``query program``); a ``dont-say: allow``
marker exempts a line. Local run, no CI.
"""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("cadqa.check_dont_say")

DONT_SAY_HEADING = "## Don't say"
SKIP_DIRS = frozenset(
    {
        ".git",
        ".venv",
        ".worktrees",
        "__pycache__",
        "_archive",
        "_audit",
        "data",
        "dist",
        "node_modules",
        "runs",
    }
)
SKIP_FILES = frozenset({"glossary.md", "check_dont_say.py"})
ALLOW_MARKER = re.compile(r"dont-say:\s*allow", re.IGNORECASE)
ALLOW_LINE = re.compile(r"don'?t say|do not say|never say|banned:", re.IGNORECASE)
CODE_FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`]*`")
SAY_SEPARATORS = (" / ", ";", ",", " or ", ": ")


class Rule(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    dont_say: str = Field(min_length=1)
    say: str = Field(min_length=1)
    why: str = Field(default="")
    pattern: re.Pattern[str]

    @classmethod
    def build(cls, dont_say: str, say: str, why: str = "") -> Rule:
        words = [re.escape(word) for word in dont_say.split()]
        pattern = re.compile(r"(?i)\b" + r"[ \t]+".join(words) + r"\b")
        return cls(dont_say=dont_say, say=say, why=why, pattern=pattern)

    def covers(self) -> list[str]:
        return covering_phrases(self.say)


class Hit(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Path
    line: int = Field(ge=1)
    rule: Rule
    text: str = Field(min_length=1)


def dont_say_section(src: str) -> str:
    if src.startswith(DONT_SAY_HEADING):
        start = 0
    else:
        index = src.find("\n" + DONT_SAY_HEADING)
        if index < 0:
            raise ValueError(f"glossary is missing {DONT_SAY_HEADING!r}")
        start = index + 1
    rest = src[start + len(DONT_SAY_HEADING) :]
    end = rest.find("\n## ")
    if end < 0:
        raise ValueError("glossary Don't-say section does not end at a '## ' heading")
    return rest[:end].strip()


def split_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def is_header(cells: list[str]) -> bool:
    return (
        len(cells) >= 2
        and cells[0].lower() == "don't say"
        and cells[1].lower() == "say"
    )


def is_separator(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("|") or "---" not in stripped:
        return False
    return all(ch in "-: " for cell in stripped.strip("|").split("|") for ch in cell)


def split_synonyms(cell: str) -> list[str]:
    parts: list[str] = []
    buffer: list[str] = []
    depth = 0
    index = 0
    while index < len(cell):
        char = cell[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        if depth == 0 and char == ",":
            parts.append("".join(buffer))
            buffer = []
            index += 1
            continue
        if depth == 0 and cell.startswith(" / ", index):
            parts.append("".join(buffer))
            buffer = []
            index += 3
            continue
        buffer.append(char)
        index += 1
    parts.append("".join(buffer))
    return [part.strip() for part in parts if part.strip()]


def normalize_phrase(raw: str) -> str:
    text = raw.replace("`", "").strip().strip("'\"")
    out: list[str] = []
    skip = False
    for char in text:
        if char == "(":
            skip = True
        elif char == ")":
            skip = False
        elif not skip:
            out.append(char)
    return " ".join("".join(out).split())


def covering_phrases(say: str) -> list[str]:
    normalized = say.replace("—", ",").replace("–", ",")
    parts = [normalized]
    for separator in SAY_SEPARATORS:
        parts = [piece for part in parts for piece in part.split(separator)]
    seen: set[str] = set()
    phrases: list[str] = []
    for part in parts:
        phrase = part.strip().strip("`").lower()
        if phrase and phrase not in seen:
            seen.add(phrase)
            phrases.append(phrase)
    return phrases


def parse_rules(src: str) -> list[Rule]:
    lines = dont_say_section(src).splitlines()
    header = -1
    for index, line in enumerate(lines):
        cells = split_cells(line)
        if cells and is_header(cells):
            header = index
            break
    if header < 0:
        raise ValueError("Don't-say table is missing a 'Don't say | Say' header")
    if header + 1 >= len(lines) or not is_separator(lines[header + 1]):
        raise ValueError("Don't-say table is missing a separator row")
    rules: list[Rule] = []
    for line in lines[header + 2 :]:
        cells = split_cells(line)
        if cells is None:
            continue
        why = cells[2] if len(cells) > 2 else ""
        for raw in split_synonyms(cells[0]):
            phrase = normalize_phrase(raw)
            if phrase:
                rules.append(Rule.build(phrase, cells[1], why))
    if not rules:
        raise ValueError("Don't-say table has no data rows")
    return rules


def covers_match(line_lower: str, start: int, end: int, phrases: list[str]) -> bool:
    for phrase in phrases:
        for variant in (phrase, phrase.replace(" ", "-"), phrase.replace(" ", "_")):
            search_from = 0
            while True:
                found = line_lower.find(variant, search_from)
                if found < 0:
                    break
                if found <= start and end <= found + len(variant):
                    return True
                search_from = found + 1
    return False


def in_code_span(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(
        span_start <= start and end <= span_end for span_start, span_end in spans
    )


def scan_file(path: Path, rules: list[Rule]) -> list[Hit]:
    hits: list[Hit] = []
    in_fence = False
    for line_no, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if CODE_FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or ALLOW_MARKER.search(line) or ALLOW_LINE.search(line):
            continue
        lower = line.lower()
        spans = [(match.start(), match.end()) for match in INLINE_CODE.finditer(line)]
        for rule in rules:
            if rule.pattern.search(line) is None:
                continue
            phrases = rule.covers()
            for match in rule.pattern.finditer(line):
                if in_code_span(match.start(), match.end(), spans):
                    continue
                if covers_match(lower, match.start(), match.end(), phrases):
                    continue
                hits.append(Hit(path=path, line=line_no, rule=rule, text=line.strip()))
                break
    return hits


def iter_files(roots: list[str]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        path = Path(root)
        if path.is_file():
            files.append(path)
            continue
        if not path.exists():
            logger.warning("skipping missing root %s", root)
            continue
        for candidate in sorted(path.rglob("*.md")):
            if candidate.name in SKIP_FILES:
                continue
            if SKIP_DIRS.intersection(candidate.parts):
                continue
            files.append(candidate)
    return files


def collect_hits(roots: list[str], rules: list[Rule]) -> list[Hit]:
    hits = [hit for path in iter_files(roots) for hit in scan_file(path, rules)]
    return sorted(hits, key=lambda hit: (str(hit.path), hit.line, hit.rule.dont_say))


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Fail on Don't-say terms in CAD-QA docs."
    )
    parser.add_argument("--glossary", type=Path, default=Path("docs/glossary.md"))
    parser.add_argument("--roots", nargs="+", default=["docs"])
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    try:
        rules = parse_rules(args.glossary.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.error("check_dont_say: %s", exc)
        return 2

    hits = collect_hits(args.roots, rules)
    for hit in hits:
        logger.warning(
            '%s:%d: don\'t say "%s" (say %s)',
            hit.path,
            hit.line,
            hit.rule.dont_say,
            hit.rule.say,
        )
    if hits:
        logger.error("%d Don't-say hit(s)", len(hits))
        return 1
    if not args.quiet:
        logger.info("check_dont_say: clean (%d rules)", len(rules))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
