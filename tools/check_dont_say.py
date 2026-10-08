#!/usr/bin/env python3
"""Don't-say checker for CAD-QA docs and code.

Reads the ``## Don't say`` table from ``docs/glossary.md`` and fails when a
banned term appears in a scanned doc or code file. A Say term covers its own
Don't-say tokens; a ``(home)`` annotation allows the token under that tree; the
allowlist and ``dont-say: allow`` / ``dont-say: home`` markers exempt specific
text. In code only identifier-shaped tokens are matched, so bare English words
stay prose-only. ``--ratchet`` enforces that the hit count never rises.
"""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("cadqa.check_dont_say")

REPO = Path(__file__).resolve().parents[1]
DONT_SAY_HEADING = "## Don't say"
SCAN_ROOTS = ("docs", "cad_qa", "train_and_eval", "tools")
SCAN_SUFFIXES = frozenset({".md", ".py"})
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
SKIP_FILES = frozenset(
    {
        "glossary.md",
        "check_dont_say.py",
        "test_check_dont_say.py",
        "test_dont_say_ratchet.py",
        "dont_say_baseline.txt",
    }
)
ALLOW_MARKER = re.compile(r"dont-say:\s*allow", re.IGNORECASE)
HOME_MARKER = re.compile(r"dont-say:\s*home", re.IGNORECASE)
ALLOW_LINE = re.compile(r"don'?t say|do not say|never say|banned:", re.IGNORECASE)
CODE_FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`]*`")
SAY_SEPARATORS = (" / ", ";", ",", " or ", ": ")

HOMES: dict[str, tuple[str, ...]] = {
    "cad_qa": ("cad_qa",),
    "dataset_generation": ("dataset_generation",),
    "train_and_eval": ("train_and_eval",),
    "fine_tuning": ("fine_tuning",),
    "docs": ("docs",),
    "tools": ("tools",),
}

ALLOWLIST = (
    "open-source",
    "open source",
    "source of truth",
    "source code",
    "data source",
)


class Rule(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    phrase: str = Field(min_length=1)
    say: str = Field(min_length=1)
    why: str = Field(default="")
    pattern: re.Pattern[str]
    identifiers: tuple[re.Pattern[str], ...] = ()
    homes: tuple[str, ...] = ()
    covers: tuple[str, ...] = ()

    @classmethod
    def build(cls, raw: str, say: str, why: str = "") -> Rule:
        phrase = normalize_phrase(raw)
        identifiers = tuple(
            re.compile(r"\b" + re.escape(variant) + r"\b")
            for variant in identifier_variants(phrase)
        )
        return cls(
            phrase=phrase,
            say=say,
            why=why,
            pattern=compile_phrase(phrase),
            identifiers=identifiers,
            homes=home_prefixes(parentheticals(raw)),
            covers=tuple(covering_phrases(say)),
        )


class Hit(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Path
    line: int = Field(ge=1)
    rule: Rule
    text: str = Field(min_length=1)


def compile_phrase(phrase: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in phrase.split()]
    return re.compile(r"(?i)\b" + r"[ \t]+".join(parts) + r"\b")


def has_identifier_shape(phrase: str) -> bool:
    return "_" in phrase or "-" in phrase or any(ch.isupper() for ch in phrase[1:])


def identifier_variants(phrase: str) -> list[str]:
    words = phrase.lower().split()
    if len(words) < 2:
        return []
    snake = "_".join(words)
    kebab = "-".join(words)
    pascal = "".join(word[:1].upper() + word[1:] for word in words)
    camel = words[0] + "".join(word[:1].upper() + word[1:] for word in words[1:])
    variants: list[str] = []
    for variant in (snake, kebab, pascal, camel):
        if variant and variant not in variants:
            variants.append(variant)
    return variants


def parentheticals(raw: str) -> list[str]:
    return [segment.strip() for segment in re.findall(r"\(([^)]*)\)", raw)]


def home_prefixes(annotations: list[str]) -> tuple[str, ...]:
    prefixes: list[str] = []
    for annotation in annotations:
        for name in annotation.split(","):
            for folder in HOMES.get(name.strip().lower(), ()):
                if folder not in prefixes:
                    prefixes.append(folder)
    return tuple(prefixes)


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
                rules.append(Rule.build(raw, cells[1], why))
    if not rules:
        raise ValueError("Don't-say table has no data rows")
    return rules


def in_code_span(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(
        span_start <= start and end <= span_end for span_start, span_end in spans
    )


def covers_match(
    line_lower: str, start: int, end: int, phrases: tuple[str, ...]
) -> bool:
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


def blocked_by_home(rule: Rule, path: Path) -> bool:
    posix = path.as_posix()
    for folder in rule.homes:
        if posix == folder or posix.startswith(folder + "/") or f"/{folder}/" in posix:
            return True
    return False


def patterns_for(rule: Rule, code: bool) -> tuple[re.Pattern[str], ...]:
    if not code:
        return (rule.pattern,)
    patterns = list(rule.identifiers)
    if "_" in rule.phrase or "-" in rule.phrase:
        patterns.append(rule.pattern)
    return tuple(patterns)


def scan_file(path: Path, rules: list[Rule]) -> list[Hit]:
    text = path.read_text(encoding="utf-8")
    code = path.suffix == ".py"
    if code and HOME_MARKER.search(text):
        return []
    hits: list[Hit] = []
    in_fence = False
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not code and CODE_FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or ALLOW_MARKER.search(line) or ALLOW_LINE.search(line):
            continue
        lower = line.lower()
        spans = (
            [] if code else [(m.start(), m.end()) for m in INLINE_CODE.finditer(line)]
        )
        for rule in rules:
            if blocked_by_home(rule, path):
                continue
            patterns = patterns_for(rule, code)
            if not patterns:
                continue
            allowed = rule.covers + ALLOWLIST
            if matched_line(patterns, line, lower, spans, allowed):
                hits.append(Hit(path=path, line=line_no, rule=rule, text=line.strip()))
    return hits


def matched_line(
    patterns: tuple[re.Pattern[str], ...],
    line: str,
    lower: str,
    spans: list[tuple[int, int]],
    allowed: tuple[str, ...],
) -> bool:
    for pattern in patterns:
        for match in pattern.finditer(line):
            if in_code_span(match.start(), match.end(), spans):
                continue
            if covers_match(lower, match.start(), match.end(), allowed):
                continue
            return True
    return False


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
        for candidate in sorted(path.rglob("*")):
            if candidate.suffix not in SCAN_SUFFIXES:
                continue
            if candidate.name in SKIP_FILES:
                continue
            if SKIP_DIRS.intersection(candidate.parts):
                continue
            files.append(candidate)
    return files


def collect_hits(roots: list[str], rules: list[Rule]) -> list[Hit]:
    hits = [hit for path in iter_files(roots) for hit in scan_file(path, rules)]
    return sorted(hits, key=lambda hit: (str(hit.path), hit.line, hit.rule.phrase))


def load_baseline(path: Path) -> int | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return int(text) if text else None


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Fail on Don't-say terms in CAD-QA docs and code."
    )
    parser.add_argument("--glossary", type=Path, default=REPO / "docs/glossary.md")
    parser.add_argument(
        "--roots", nargs="+", default=[str(REPO / root) for root in SCAN_ROOTS]
    )
    parser.add_argument(
        "--ratchet", type=Path, help="baseline hit-count file to enforce"
    )
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    try:
        rules = parse_rules(args.glossary.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.error("check_dont_say: %s", exc)
        return 2

    hits = collect_hits(args.roots, rules)
    if not args.quiet:
        for hit in hits:
            logger.warning(
                '%s:%d: don\'t say "%s" (say %s)',
                hit.path,
                hit.line,
                hit.rule.phrase,
                hit.rule.say,
            )

    if args.ratchet is None:
        if hits:
            logger.error("%d Don't-say hit(s)", len(hits))
            return 1
        if not args.quiet:
            logger.info("check_dont_say: clean (%d rules)", len(rules))
        return 0

    baseline = load_baseline(args.ratchet)
    if args.update_baseline or baseline is None:
        args.ratchet.write_text(f"{len(hits)}\n", encoding="utf-8")
        logger.info("check_dont_say: baseline %d -> %s", len(hits), args.ratchet)
        return 0
    if len(hits) > baseline:
        logger.error("check_dont_say: %d hit(s) > baseline %d", len(hits), baseline)
        return 1
    if len(hits) < baseline:
        logger.error(
            "check_dont_say: %d hit(s) < baseline %d; run --update-baseline",
            len(hits),
            baseline,
        )
        return 1
    if not args.quiet:
        logger.info("check_dont_say: %d hit(s), at baseline", len(hits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
