"""File walking and scanning for the Don't-say checker.

Prose scanners report what a reader reads; name scanners report what a reader
navigates by. Policy lives in ``dont_say_rules.py``.
"""

from __future__ import annotations

import ast
import io
import logging
import re
import tokenize
from pathlib import Path

from pydantic import BaseModel, Field

from tools.ci_cd.dont_say_names import (
    Declaration,
    Fragment,
    comment_text,
    file_declaration,
    folder_declaration,
    go_declarations,
    json_declarations,
    json_prose,
    name_segments,
    python_declarations,
)
from tools.ci_cd.dont_say_rules import Hit, Rule, RuleIndex, matched_line, name_match

logger = logging.getLogger("cadqa.dont_say_scan")

SCAN_ROOTS = (
    "contracts",
    "docs",
    "generator",
    "plans",
    "tests",
    "tools",
)
# External study notes quote other fields' vocabulary verbatim (set cover,
# psychometrics, RL), so the project glossary does not apply to them. They are
# still scanned by rumdl and the documentation gates.
SKIP_PATH_SUFFIX = ("docs", "research")


def in_skipped_tree(candidate: Path) -> bool:
    parts = candidate.resolve().parts
    return any(
        parts[index : index + len(SKIP_PATH_SUFFIX)] == SKIP_PATH_SUFFIX
        for index in range(len(parts) - len(SKIP_PATH_SUFFIX) + 1)
    )
SCAN_SUFFIXES = frozenset({".go", ".json", ".md", ".py", ".tex"})
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
        "dont_say_baseline.txt",
    }
)
ALLOW_MARKER = re.compile(r"dont-say:\s*allow", re.IGNORECASE)
ALLOW_FILE_MARKER = re.compile(
    r"^\s*(?:<!--|%|#)\s*dont-say:\s*allow-file\b", re.IGNORECASE | re.MULTILINE
)
FILE_MARKER_SCAN_LINES = 10
HOME_MARKER = re.compile(r"dont-say:\s*home", re.IGNORECASE)
ALLOW_LINE = re.compile(r"don'?t say|do not say|never say|banned:", re.IGNORECASE)
CODE_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
INLINE_CODE = re.compile(r"`[^`]*`")
LATEX_VERBATIM = re.compile(
    r"\\(?:begin|end)\{(?:verbatim|Verbatim|lstlisting|minted)\}"
)
LATEX_COMMENT = re.compile(r"(?<!\\)%")
LATEX_TEXT_TT = re.compile(r"\\texttt\{[^}]*\}")
LATEX_VERB = re.compile(r"\\verb(.)(.*?)\1")
# Fields that hold statements. A docstring owner (module, class, def) can only be
# reached through these, so the docstring walk never has to visit expressions.
STATEMENT_FIELDS = ("body", "orelse", "finalbody", "handlers", "cases")


class Fence(BaseModel):
    """An open code fence: its delimiter character and its run length."""

    char: str = Field(min_length=1, max_length=1)
    length: int = Field(ge=3)

    def closes(self, line: str) -> bool:
        """True when ``line`` is this fence's closing delimiter.

        A closing delimiter repeats the opening character at least as many
        times as the opener and carries no info string, so a shorter delimiter
        inside a longer fence is content.
        """

        delimiter = line.strip()
        return len(delimiter) >= self.length and delimiter == self.char * len(delimiter)


def opening_fence(line: str) -> Fence | None:
    """Return the fence ``line`` opens; None for prose and for closing lines."""

    match = CODE_FENCE.match(line)
    if match is None:
        return None
    delimiter, info = match.group(1), match.group(2)
    if delimiter[0] == "`" and "`" in info:
        # A backtick fence's info string cannot hold a backtick, so this is
        # inline code at the start of a line.
        return None
    return Fence(char=delimiter[0], length=len(delimiter))


def code_prose_lines(text: str) -> list[tuple[int, str]]:
    """Return ``(line_number, text)`` for comments and docstrings in a Python module."""

    lines = text.splitlines()
    prose: list[tuple[int, str]] = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type == tokenize.COMMENT:
                prose.append((token.start[0], token.string))
    except tokenize.TokenError:
        pass
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return prose
    stack: list[ast.AST] = [tree]
    while stack:
        current = stack.pop()
        if isinstance(
            current, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = getattr(current, "body", [])
            if body:
                first = body[0]
                if (
                    isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)
                ):
                    start = first.lineno
                    end = getattr(first, "end_lineno", start)
                    for line_no in range(start, end + 1):
                        if 1 <= line_no <= len(lines):
                            prose.append((line_no, lines[line_no - 1]))
        for field in STATEMENT_FIELDS:
            children = getattr(current, field, None)
            if children:
                stack.extend(children)
    return sorted(prose)


def allows_file(text: str) -> bool:
    """True when a comment line in the first ten lines exempts the whole file."""

    header = "\n".join(text.splitlines()[:FILE_MARKER_SCAN_LINES])
    return bool(ALLOW_FILE_MARKER.search(header))


def scan_file(
    path: Path, rules: list[Rule], *, go: dict[Path, list[Declaration]] | None = None
) -> list[Hit]:
    """Scan one file's prose. Names are scanned separately, in ``scan_names``."""

    text = path.read_text(encoding="utf-8")
    if allows_file(text):
        return []
    match path.suffix:
        case ".py":
            return _scan_python_prose(path, text, rules)
        case ".go":
            return _scan_go_prose(path, text, rules, go or {})
        case ".json":
            return _scan_json_prose(path, text, rules)
        case _:
            return _scan_markdown(path, text, rules)


def _scan_python_prose(path: Path, text: str, rules: list[Rule]) -> list[Hit]:
    if HOME_MARKER.search(text):
        return []
    index = RuleIndex.build(rules, path)
    hits: list[Hit] = []
    seen: set[tuple[int, str]] = set()
    for line_no, segment in code_prose_lines(text):
        if ALLOW_MARKER.search(segment) or ALLOW_LINE.search(segment):
            continue
        lower = segment.lower()
        for rule in index.candidates(lower):
            if matched_line(
                (rule.pattern,),
                segment,
                lower,
                [],
                rule.allowed,
                bare=rule.bare,
            ):
                key = (line_no, rule.phrase)
                if key not in seen:
                    seen.add(key)
                    hits.append(
                        Hit(path=path, line=line_no, rule=rule, text=segment.strip())
                    )
    return hits


def _scan_go_prose(
    path: Path, text: str, rules: list[Rule], go: dict[Path, list[Declaration]]
) -> list[Hit]:
    if HOME_MARKER.search(text):
        return []
    fragments = [
        Fragment(line=declaration.line, text=comment_text(declaration.value))
        for declaration in go.get(path.resolve(), ())
        if declaration.form == "comment" and comment_text(declaration.value)
    ]
    return _scan_fragments(path, fragments, rules)


def _scan_json_prose(path: Path, text: str, rules: list[Rule]) -> list[Hit]:
    return _scan_fragments(path, json_prose(text), rules)


def _scan_fragments(
    path: Path, fragments: list[Fragment], rules: list[Rule]
) -> list[Hit]:
    """Scan prose that is not one line of a file, such as a JSON description."""

    index = RuleIndex.build(rules, path)
    hits: list[Hit] = []
    for fragment in fragments:
        if ALLOW_MARKER.search(fragment.text) or ALLOW_LINE.search(fragment.text):
            continue
        lower = fragment.text.lower()
        for rule in index.candidates(lower):
            if matched_line(
                (rule.pattern,),
                fragment.text,
                lower,
                [],
                rule.allowed,
                bare=rule.bare,
            ):
                hits.append(
                    Hit(
                        path=path,
                        line=fragment.line,
                        rule=rule,
                        text=fragment.text,
                    )
                )
    return hits


def scan_names(
    path: Path, text: str, rules: list[Rule], declarations: list[Declaration]
) -> list[Hit]:
    """Scan the names a file declares, and its own file and folder names."""

    if HOME_MARKER.search(text):
        return []
    if allows_file(text):
        return []
    index = RuleIndex.build(rules, path)
    if not index.rules:
        return []
    allowed_lines = {
        line_no
        for line_no, line in enumerate(text.splitlines(), start=1)
        if ALLOW_MARKER.search(line) or ALLOW_LINE.search(line)
    }
    hits: list[Hit] = []
    seen: set[tuple[int, str, str, str]] = set()
    for declaration in declarations:
        if declaration.line in allowed_lines:
            continue
        segments = name_segments(declaration.value)
        if not segments:
            continue
        for rule in index.candidates(" ".join(segments)):
            if not name_match(declaration.value, rule):
                continue
            key = (
                declaration.line,
                declaration.form,
                declaration.value,
                rule.phrase,
            )
            if key in seen:
                continue
            seen.add(key)
            hits.append(
                Hit(
                    path=path,
                    line=declaration.line,
                    rule=rule,
                    text=declaration.value,
                    form=declaration.form,
                    name=declaration.value,
                )
            )
    return hits


def _scan_markdown(path: Path, text: str, rules: list[Rule]) -> list[Hit]:
    latex = path.suffix == ".tex"
    index = RuleIndex.build(rules, path)
    hits: list[Hit] = []
    fence: Fence | None = None
    in_verbatim = False
    for line_no, line in enumerate(text.splitlines(), start=1):
        if latex:
            if LATEX_VERBATIM.search(line):
                in_verbatim = not in_verbatim
                continue
            if in_verbatim:
                continue
            probe = LATEX_COMMENT.split(line, 1)[0]
        else:
            if fence is not None:
                if fence.closes(line):
                    fence = None
                continue
            opened = opening_fence(line)
            if opened is not None:
                fence = opened
                continue
            probe = line
        if ALLOW_MARKER.search(line) or ALLOW_LINE.search(line):
            continue
        lower = probe.lower()
        spans = (
            [(m.start(), m.end()) for m in INLINE_CODE.finditer(probe)]
            if "`" in probe
            else []
        )
        if latex:
            spans += [(m.start(), m.end()) for m in LATEX_TEXT_TT.finditer(probe)]
            spans += [(m.start(), m.end()) for m in LATEX_VERB.finditer(probe)]
        for rule in index.candidates(lower):
            if matched_line(
                (rule.pattern,),
                probe,
                lower,
                spans,
                rule.allowed,
                bare=rule.bare,
            ):
                hits.append(Hit(path=path, line=line_no, rule=rule, text=line.strip()))
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
        for candidate in sorted(path.rglob("*")):
            if candidate.suffix not in SCAN_SUFFIXES:
                continue
            if candidate.name in SKIP_FILES:
                continue
            if SKIP_DIRS.intersection(candidate.relative_to(path).parts):
                continue
            if in_skipped_tree(candidate):
                continue
            files.append(candidate)
    return files


def iter_folders(roots: list[str]) -> list[Path]:
    """Every folder under each root."""

    folders: list[Path] = []
    for root in roots:
        path = Path(root)
        if not path.is_dir():
            continue
        for candidate in sorted(path.rglob("*")):
            if not candidate.is_dir():
                continue
            if SKIP_DIRS.intersection(candidate.relative_to(path).parts):
                continue
            if in_skipped_tree(candidate):
                continue
            folders.append(candidate)
    return folders


def collect_hits(
    roots: list[str], rules: list[Rule], *, names: bool = True
) -> list[Hit]:
    """Scan every file's prose, and every name CAD-QA declares."""

    files = iter_files(roots)
    go: dict[Path, list[Declaration]] = {}
    if names:
        go_paths = [path.resolve() for path in files if path.suffix == ".go"]
        for declaration in go_declarations(go_paths):
            go.setdefault(declaration.path, []).append(declaration)

    hits: list[Hit] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        hits.extend(scan_file(path, rules, go=go))
        if not names:
            continue
        declarations = [file_declaration(path)]
        match path.suffix:
            case ".py":
                declarations.extend(python_declarations(path, text))
            case ".go":
                declarations.extend(
                    declaration
                    for declaration in go.get(path.resolve(), ())
                    if declaration.form != "comment"
                )
            case ".json":
                declarations.extend(json_declarations(path, text))
        hits.extend(scan_names(path, text, rules, declarations))

    if names:
        seen: set[Path] = set()
        for folder in iter_folders(roots):
            resolved = folder.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            hits.extend(scan_names(folder, "", rules, [folder_declaration(folder)]))

    return sorted(
        hits, key=lambda hit: (str(hit.path), hit.line, hit.form, hit.rule.phrase)
    )
