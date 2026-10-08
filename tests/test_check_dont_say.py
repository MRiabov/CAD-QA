from __future__ import annotations

from pathlib import Path

from tools.check_dont_say import (
    Rule,
    collect_hits,
    covering_phrases,
    iter_files,
    parse_rules,
    scan_file,
)

GLOSSARY = """# Glossary

## Domain

### CadQuery program

A program.

## Don't say

| Don't say | Say | Why |
|---|---|---|
| source | CadQuery program | bare noun |
| ontology graph | CAD ontology graph | unqualified |
| ontology (bare) | CAD ontology | generic |
| query program | Gold query program | conflated |

## Proposed additions

none
"""


def write_glossary(tmp_path: Path) -> Path:
    glossary = tmp_path / "glossary.md"
    glossary.write_text(GLOSSARY, encoding="utf-8")
    return glossary


def test_parse_rules_splits_synonyms_and_strips_parentheticals() -> None:
    rules = parse_rules(GLOSSARY)
    phrases = {rule.dont_say for rule in rules}
    assert phrases == {"source", "ontology graph", "ontology", "query program"}
    assert (
        next(rule for rule in rules if rule.dont_say == "source").say
        == "CadQuery program"
    )


def test_covering_phrases_splits_say_alternatives() -> None:
    assert covering_phrases("Gold query program") == ["gold query program"]
    assert "cad ontology" in covering_phrases("CAD ontology")


def test_say_term_covers_its_dont_say_token(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text("Run the gold query program.\n", encoding="utf-8")
    assert scan_file(doc, rules) == []


def test_bare_dont_say_token_is_a_hit(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text("Run the query program.\n", encoding="utf-8")
    hits = scan_file(doc, rules)
    assert [hit.rule.dont_say for hit in hits] == ["query program"]


def test_bare_ontology_is_covered_by_cad_ontology(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text(
        "The CAD ontology node and the CAD ontology graph.\n", encoding="utf-8"
    )
    assert scan_file(doc, rules) == []


def test_allow_marker_exempts_line(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text("the source <!-- dont-say: allow -->\n", encoding="utf-8")
    assert scan_file(doc, rules) == []


def test_iter_files_skips_archive_and_glossary(tmp_path: Path) -> None:
    write_glossary(tmp_path)
    (tmp_path / "doc.md").write_text("hi\n", encoding="utf-8")
    archive = tmp_path / "_archive"
    archive.mkdir()
    (archive / "old.md").write_text("the source\n", encoding="utf-8")
    found = {path.name for path in iter_files([str(tmp_path)])}
    assert found == {"doc.md"}
    assert collect_hits([str(tmp_path)], parse_rules(GLOSSARY)) == []


def test_rule_builds_word_boundary_pattern() -> None:
    rule = Rule.build("source", "CadQuery program")
    assert rule.pattern.search("the source") is not None
    assert rule.pattern.search("sources") is None
