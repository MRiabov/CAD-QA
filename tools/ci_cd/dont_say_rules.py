"""The Don't-say rules and the matching policy.

The glossary owns the terms; this module turns the ``## Don't say`` table into
rules and decides whether a piece of prose or a declared name breaks one.
Scanning lives in ``dont_say_scan.py``; syntax extraction lives in
``dont_say_names.py``.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from tools.ci_cd.dont_say_names import name_segments

DONT_SAY_HEADING = "## Don't say"
TOKEN = re.compile(r"[a-z0-9_]+")
SAY_SEPARATORS = (" / ", ";", ",", " or ", ": ")

HOMES: dict[str, tuple[str, ...]] = {
    # The dataset term's home is the dataset docs tree, ``docs/dataset/``.
    "dataset": ("dataset",),
    "dataset_generation": ("cadqa_dataset_generator",),
    "docs": ("docs",),
    "tools": ("tools",),
}

ALLOWLIST = (
    # Pydantic's reserved attribute, not a CAD-QA name.
    "model config",
    "open-source",
    "open source",
    "source of truth",
    "source code",
    "data source",
    "source variable",
    "surface area",
    "type: ignore",
)

BARE_QUALIFIER_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "this",
        "that",
        "these",
        "those",
        "any",
        "some",
        "one",
        "all",
        "both",
        "each",
        "every",
        "another",
        "such",
        "same",
        "own",
        "its",
        "their",
        "our",
        "your",
        "my",
        "his",
        "her",
        "it",
        "we",
        "you",
        "they",
        "i",
        "he",
        "she",
        "of",
        "in",
        "on",
        "at",
        "for",
        "with",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "not",
        "no",
        "than",
        "then",
        "so",
        "too",
        "very",
        "more",
        "most",
        "less",
        "least",
        "only",
        "also",
        "just",
        "from",
        "to",
        "by",
        "into",
        "over",
        "under",
        "about",
        "after",
        "before",
        "between",
        "through",
        "during",
        "without",
        "within",
    }
)


# A leading verb says what a function does, not what the term is: ``get_type``
# does not say which term it names, so a verb before a bare term does not
# qualify it.
QUALIFIER_VERBS = frozenset(
    {
        "add",
        "build",
        "check",
        "collect",
        "count",
        "create",
        "delete",
        "emit",
        "execute",
        "extract",
        "find",
        "from",
        "get",
        "has",
        "is",
        "list",
        "load",
        "make",
        "normalize",
        "parse",
        "read",
        "remove",
        "render",
        "run",
        "save",
        "select",
        "set",
        "to",
        "update",
        "validate",
        "write",
    }
)


class Rule(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    phrase: str = Field(min_length=1)
    say: str = Field(min_length=1)
    why: str = Field(default="")
    pattern: re.Pattern[str]
    homes: tuple[str, ...] = ()
    allowed: tuple[str, ...] = ()
    bare: bool = False
    keys: tuple[str, ...] = Field(default=())

    @classmethod
    def build(cls, raw: str, say: str, why: str = "") -> Rule:
        phrase = normalize_phrase(raw)
        keys = rule_keys(phrase)
        if not keys:
            raise ValueError(f"Don't-say phrase has no word token: {phrase!r}")
        return cls(
            phrase=phrase,
            say=say,
            why=why,
            pattern=compile_phrase(phrase),
            homes=home_prefixes(parentheticals(raw)),
            allowed=tuple(covering_phrases(say)) + ALLOWLIST,
            bare=any(part.lower() == "bare" for part in parentheticals(raw)),
            keys=keys,
        )


class Hit(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Path
    line: int = Field(ge=1)
    rule: Rule
    text: str = Field(min_length=1)
    form: str = Field(default="")
    name: str = Field(default="")


class RuleIndex(BaseModel):
    """Rules that apply to one file, bucketed by a word each rule must contain.

    ``blocked_by_home`` and the bucket build run once per file instead of once
    per rule per line. ``candidates`` is a superset of the rules that can match
    the line: a pattern needs every word of its phrase, so a rule whose words
    are absent cannot match. The exact pattern still decides.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    rules: tuple[Rule, ...]
    buckets: dict[str, tuple[Rule, ...]]

    @classmethod
    def build(cls, rules: list[Rule], path: Path) -> RuleIndex:
        applicable = tuple(rule for rule in rules if not blocked_by_home(rule, path))
        buckets: dict[str, list[Rule]] = {}
        for rule in applicable:
            for key in rule.keys:
                buckets.setdefault(key, []).append(rule)
        return cls(
            rules=applicable,
            buckets={key: tuple(bucket) for key, bucket in buckets.items()},
        )

    def candidates(self, lower: str) -> tuple[Rule, ...]:
        found: list[Rule] = []
        seen: set[str] = set()
        for token in TOKEN.findall(lower):
            for rule in self.buckets.get(token, ()):
                if rule.phrase not in seen:
                    seen.add(rule.phrase)
                    found.append(rule)
        return tuple(found)


def compile_phrase(phrase: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in phrase.split()]
    return re.compile(r"(?i)\b" + r"[ \t]+".join(parts) + r"\b")


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


def rule_keys(phrase: str) -> tuple[str, ...]:
    """Words that must be on a line before the rule's patterns can match it.

    A pattern needs every word of its phrase, and an identifier pattern needs
    its snake, kebab, Pascal, or camel variant; a line with none of those words
    cannot match. The check is a superset filter, so the exact pattern still
    decides whether the line is a hit.
    """

    texts = [phrase, *identifier_variants(phrase)]
    return tuple(
        dict.fromkeys(token for text in texts for token in TOKEN.findall(text.lower()))
    )


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


def preceding_word(text: str, start: int) -> str | None:
    match = re.search(r"([A-Za-z][A-Za-z0-9_-]*)\s+$", text[:start])
    return match.group(1).lower() if match else None


def is_qualified_bare(text: str, start: int) -> bool:
    word = preceding_word(text, start)
    return word is not None and word not in BARE_QUALIFIER_STOPWORDS


def blocked_by_home(rule: Rule, path: Path) -> bool:
    posix = path.as_posix()
    for folder in rule.homes:
        if posix == folder or posix.startswith(folder + "/") or f"/{folder}/" in posix:
            return True
    return False


def segments_cover(segments: list[str], phrases: tuple[str, ...]) -> bool:
    """True when any allowed phrase appears as consecutive name segments."""

    for phrase in phrases:
        words = name_segments(phrase)
        if not words or len(words) > len(segments):
            continue
        for start in range(len(segments) - len(words) + 1):
            if segments[start : start + len(words)] == words:
                return True
    return False


def qualifies(segments: list[str], start: int) -> bool:
    """True when the segment before a bare term qualifies it."""

    if start == 0:
        return False
    preceding = segments[start - 1]
    return (
        preceding not in BARE_QUALIFIER_STOPWORDS and preceding not in QUALIFIER_VERBS
    )


def name_match(name: str, rule: Rule) -> bool:
    """True when the rule's words appear as consecutive segments of ``name``."""

    segments = name_segments(name)
    if not segments:
        return False
    if segments_cover(segments, rule.allowed):
        return False
    words = rule.phrase.lower().split()
    size = len(words)
    for start in range(len(segments) - size + 1):
        if segments[start : start + size] != words:
            continue
        if rule.bare and qualifies(segments, start):
            continue
        return True
    return False


def matched_line(
    patterns: tuple[re.Pattern[str], ...],
    line: str,
    lower: str,
    spans: list[tuple[int, int]],
    allowed: tuple[str, ...],
    *,
    bare: bool = False,
) -> bool:
    for pattern in patterns:
        for match in pattern.finditer(line):
            if in_code_span(match.start(), match.end(), spans):
                continue
            if bare and is_qualified_bare(lower, match.start()):
                continue
            if covers_match(lower, match.start(), match.end(), allowed):
                continue
            return True
    return False
