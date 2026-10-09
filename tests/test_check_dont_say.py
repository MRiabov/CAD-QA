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
    phrases = {rule.phrase for rule in rules}
    assert phrases == {"source", "ontology graph", "ontology", "query program"}
    assert (
        next(rule for rule in rules if rule.phrase == "source").say
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
    assert [hit.rule.phrase for hit in hits] == ["query program"]


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


def test_inline_code_is_skipped(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text("See `source` and `dataset/source_ingestion.py`.\n", encoding="utf-8")
    assert scan_file(doc, rules) == []


def test_fenced_block_is_skipped(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text("```\nthe source\n```\n", encoding="utf-8")
    assert scan_file(doc, rules) == []


def test_bare_word_is_not_scanned_in_code(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    code = tmp_path / "mod.py"
    code.write_text("source = 1\n", encoding="utf-8")
    assert scan_file(code, rules) == []


def test_comment_prose_is_scanned_in_code(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    code = tmp_path / "mod.py"
    code.write_text("# the source builder\n", encoding="utf-8")
    hits = scan_file(code, rules)
    assert [hit.rule.phrase for hit in hits] == ["source"]


def test_docstring_prose_is_scanned_in_code(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    code = tmp_path / "mod.py"
    code.write_text('"""The source builder."""\n', encoding="utf-8")
    hits = scan_file(code, rules)
    assert [hit.rule.phrase for hit in hits] == ["source"]


def test_say_term_in_comment_is_covered(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    code = tmp_path / "mod.py"
    code.write_text("# the CadQuery program builder\n", encoding="utf-8")
    assert scan_file(code, rules) == []


def test_identifier_mode_matches_single_word_names(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    code = tmp_path / "mod.py"
    code.write_text("source = 1\n", encoding="utf-8")
    assert scan_file(code, rules) == []
    hits = scan_file(code, rules, identifiers=True)
    assert [hit.rule.phrase for hit in hits] == ["source"]


def test_identifier_variant_is_scanned_in_code(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    code = tmp_path / "mod.py"
    code.write_text("query_program = build()\n", encoding="utf-8")
    hits = scan_file(code, rules)
    assert [hit.rule.phrase for hit in hits] == ["query program"]


def test_home_annotation_exempts_tree(tmp_path: Path) -> None:
    glossary = GLOSSARY.replace(
        "| query program | Gold query program |",
        "| query program (dataset) | Gold query program |",
    )
    rules = parse_rules(glossary)
    home_code = tmp_path / "dataset" / "mod.py"
    home_code.parent.mkdir()
    home_code.write_text("QueryProgram()\n", encoding="utf-8")
    other_code = tmp_path / "other" / "mod.py"
    other_code.parent.mkdir()
    other_code.write_text("QueryProgram()\n", encoding="utf-8")
    assert scan_file(home_code, rules) == []
    assert [hit.rule.phrase for hit in scan_file(other_code, rules)] == [
        "query program"
    ]


def test_latex_prose_is_scanned(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "paper.tex"
    doc.write_text("The source builder.\n", encoding="utf-8")
    hits = scan_file(doc, rules)
    assert [hit.rule.phrase for hit in hits] == ["source"]


def test_latex_code_verbatim_and_comments_are_skipped(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "paper.tex"
    doc.write_text(
        "A \\texttt{source:value} is literal.\n"
        "\\begin{verbatim}\n"
        "source = 1\n"
        "\\end{verbatim}\n"
        "% the source comment\n"
        "The source builder.\n",
        encoding="utf-8",
    )
    hits = scan_file(doc, rules)
    assert [hit.rule.phrase for hit in hits] == ["source"]
    assert hits[0].line == 6


def test_iter_files_scans_paper_and_tex(tmp_path: Path) -> None:
    write_glossary(tmp_path)
    paper = tmp_path / "paper"
    paper.mkdir()
    (paper / "draft.tex").write_text("The source builder.\n", encoding="utf-8")
    found = {path.name for path in iter_files([str(tmp_path)])}
    assert "draft.tex" in found
