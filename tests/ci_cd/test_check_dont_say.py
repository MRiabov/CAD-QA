from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tools.ci_cd.check_dont_say import format_hit, main
from tools.ci_cd.dont_say_names import (
    Declaration,
    file_declaration,
    json_declarations,
    json_prose,
    name_segments,
    python_declarations,
)
from tools.ci_cd.dont_say_rules import Rule, covering_phrases, name_match, parse_rules
from tools.ci_cd.dont_say_scan import (
    collect_hits,
    iter_files,
    scan_file,
    scan_names,
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
| type (bare) / types (bare) | clue type | raw noun |
| kind (bare) / kinds (bare) | predicate kind | raw noun |

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
    assert phrases == {
        "source",
        "ontology graph",
        "ontology",
        "query program",
        "type",
        "types",
        "kind",
        "kinds",
    }
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


def test_qualified_bare_type_is_allowed(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text("The clue type and the task type are clear.\n", encoding="utf-8")
    assert scan_file(doc, rules) == []


def test_bare_type_is_a_hit(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text("The type is unclear.\n", encoding="utf-8")
    hits = scan_file(doc, rules)
    assert [hit.rule.phrase for hit in hits] == ["type"]


def test_bare_hit_message_asks_for_qualification(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text("The type is unclear.\n", encoding="utf-8")
    hit = scan_file(doc, rules)[0]
    assert 'don\'t say bare "type"' in format_hit(hit)
    assert "qualify it" in format_hit(hit)


def test_name_hit_message_names_the_declaration(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    code = tmp_path / "mod.py"
    text = "class Row:\n    kind: str\n"
    code.write_text(text, encoding="utf-8")
    hits = scan_names(code, text, rules, python_declarations(code, text))
    assert len(hits) == 1
    assert 'in field "kind"' in format_hit(hits[0])


def test_allow_marker_exempts_line(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text("the source <!-- dont-say: allow -->\n", encoding="utf-8")
    assert scan_file(doc, rules) == []


def test_allow_marker_does_not_exempt_other_lines(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text(
        "the source <!-- dont-say: allow -->\nthe source\n", encoding="utf-8"
    )
    hits = scan_file(doc, rules)
    assert [hit.line for hit in hits] == [2]


def test_allow_file_marker_exempts_whole_file(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text(
        "<!-- dont-say: allow-file: verbatim transcript -->\nthe source\n",
        encoding="utf-8",
    )
    assert scan_file(doc, rules) == []


def test_allow_file_marker_must_be_a_comment_line(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text(
        "Document `dont-say: allow-file` in prose.\nthe source\n", encoding="utf-8"
    )
    hits = scan_file(doc, rules)
    assert [hit.line for hit in hits] == [2]


def test_allow_file_marker_is_ignored_below_the_header(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text(
        "\n" * 10 + "<!-- dont-say: allow-file -->\nthe source\n", encoding="utf-8"
    )
    hits = scan_file(doc, rules)
    assert [hit.line for hit in hits] == [12]


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
    doc.write_text(
        "See `source` and `dataset/source_ingestion.py`.\n", encoding="utf-8"
    )
    assert scan_file(doc, rules) == []


def test_fenced_block_is_skipped(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text("```\nthe source\n```\n", encoding="utf-8")
    assert scan_file(doc, rules) == []


def test_nested_fence_content_is_skipped(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text(
        "````text\n"
        "\n"
        "the prompt\n"
        "\n"
        "```python\n"
        'result = f("the source")\n'
        "```\n"
        "\n"
        "more prompt\n"
        "````\n"
        "\n"
        "the source\n",
        encoding="utf-8",
    )
    hits = scan_file(doc, rules)
    assert [hit.line for hit in hits] == [12]


def test_fence_closes_only_with_a_long_enough_delimiter(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text(
        "````text\nthe source\n```\nthe source\n````\nthe source\n", encoding="utf-8"
    )
    hits = scan_file(doc, rules)
    assert [hit.line for hit in hits] == [6]


def test_tilde_fence_ignores_backtick_delimiters(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text(
        "~~~text\nthe source\n```\nthe source\n~~~~~\nthe source\n", encoding="utf-8"
    )
    hits = scan_file(doc, rules)
    assert [hit.line for hit in hits] == [6]


def test_a_fence_line_carrying_a_backtick_is_prose(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    doc = tmp_path / "doc.md"
    doc.write_text(
        "```text``` renders a fenced block with the source.\nthe source\n",
        encoding="utf-8",
    )
    hits = scan_file(doc, rules)
    assert [hit.line for hit in hits] == [1, 2]


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


def test_home_annotation_exempts_tree(tmp_path: Path) -> None:
    glossary = GLOSSARY.replace(
        "| query program | Gold query program |",
        "| query program (dataset) | Gold query program |",
    )
    rules = parse_rules(glossary)
    home_code = tmp_path / "dataset" / "mod.py"
    home_code.parent.mkdir()
    home_text = "class QueryProgram: ...\n"
    home_code.write_text(home_text, encoding="utf-8")
    other_code = tmp_path / "other" / "mod.py"
    other_code.parent.mkdir()
    other_text = "class QueryProgram: ...\n"
    other_code.write_text(other_text, encoding="utf-8")
    assert (
        scan_names(
            home_code, home_text, rules, python_declarations(home_code, home_text)
        )
        == []
    )
    assert [
        hit.rule.phrase
        for hit in scan_names(
            other_code,
            other_text,
            rules,
            python_declarations(other_code, other_text),
        )
    ] == ["query program"]


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


def test_iter_files_ignores_skip_dir_names_above_the_root(tmp_path: Path) -> None:
    root = tmp_path / ".worktrees" / "wt" / "docs"
    root.mkdir(parents=True)
    (root / "doc.md").write_text("hi\n", encoding="utf-8")
    found = {path.name for path in iter_files([str(root)])}
    assert found == {"doc.md"}


# --- names ---------------------------------------------------------------


def test_name_segments_split_every_spelling() -> None:
    assert name_segments("query_program") == ["query", "program"]
    assert name_segments("QueryProgram") == ["query", "program"]
    assert name_segments("query-program") == ["query", "program"]
    assert name_segments("QUERY_PROGRAM") == ["query", "program"]


def test_python_declarations_cover_every_form() -> None:
    text = (
        "class Row:\n"
        "    kind: str\n"
        "    def label(self, prefix: str) -> str:\n"
        "        total = prefix\n"
        "        self.tag = total\n"
        "        return total\n"
        "\n"
        "def build(rows: list[Row]) -> None:\n"
        "    for item in rows:\n"
        "        print(item)\n"
    )
    declarations = python_declarations(Path("mod.py"), text)
    forms = {(declaration.form, declaration.value) for declaration in declarations}
    assert ("class", "Row") in forms
    assert ("field", "kind") in forms
    assert ("method", "label") in forms
    assert ("parameter", "self") in forms
    assert ("parameter", "prefix") in forms
    assert ("variable", "total") in forms
    assert ("field", "tag") in forms
    assert ("function", "build") in forms
    assert ("parameter", "rows") in forms
    assert ("variable", "item") in forms


def test_python_syntax_error_is_an_error() -> None:
    with pytest.raises(ValueError, match="does not parse"):
        python_declarations(Path("broken.py"), "def build(:\n")


def test_qualified_bare_name_is_allowed() -> None:
    rules = parse_rules(GLOSSARY)
    assert not name_match("clue_type", next(r for r in rules if r.phrase == "type"))


def test_leading_verb_does_not_qualify_a_bare_name() -> None:
    rules = parse_rules(GLOSSARY)
    assert name_match("get_type", next(r for r in rules if r.phrase == "type"))


def test_bare_name_alone_is_a_hit() -> None:
    rules = parse_rules(GLOSSARY)
    assert name_match("kind", next(r for r in rules if r.phrase == "kind"))


def test_json_names_skip_schema_vocabulary(tmp_path: Path) -> None:
    path = tmp_path / "schema.json"
    text = json.dumps(
        {
            "type": "object",
            "properties": {
                "node": {"type": "string"},
                "clue_type": {"type": "string"},
            },
            "$defs": {"Kind": {"type": "string"}},
        },
        indent=2,
    )
    declarations = json_declarations(path, text)
    values = {declaration.value for declaration in declarations}
    assert "node" in values
    assert "Kind" in values
    assert "clue_type" in values
    # ``"type": "object"`` is schema vocabulary, not a CAD-QA name.
    assert "type" not in values


def test_json_description_is_prose(tmp_path: Path) -> None:
    path = tmp_path / "schema.json"
    text = json.dumps({"description": "The source builder."}, indent=2)
    path.write_text(text, encoding="utf-8")
    fragments = json_prose(text)
    assert [fragment.text for fragment in fragments] == ["The source builder."]
    rules = parse_rules(GLOSSARY)
    hits = scan_file(path, rules)
    assert [hit.rule.phrase for hit in hits] == ["source"]
    assert hits[0].form == ""


def test_file_and_folder_names_are_names(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    folder = tmp_path / "source_ingestion"
    folder.mkdir()
    path = folder / "Kind.py"
    path.write_text("value = 1\n", encoding="utf-8")

    file_hit = scan_names(path, "", rules, [file_declaration(path)])
    assert [hit.rule.phrase for hit in file_hit] == ["kind"]

    hits = collect_hits([str(tmp_path)], rules)
    forms = {(hit.form, hit.name) for hit in hits}
    assert ("folder name", "source_ingestion") in forms
    assert ("file name", "Kind") in forms


@pytest.mark.skipif(shutil.which("go") is None, reason="needs the Go toolchain")
def test_go_names_and_comments_end_to_end(tmp_path: Path) -> None:
    path = tmp_path / "sample.go"
    path.write_text(
        "package sample\n"
        "\n"
        "// The source builder.\n"
        "type Kind struct {\n"
        "\tKind int\n"
        "}\n"
        "\n"
        "func build(kind string) string { return kind }\n",
        encoding="utf-8",
    )
    rules = parse_rules(GLOSSARY)
    hits = collect_hits([str(tmp_path)], rules)
    found = {(hit.form, hit.name, hit.rule.phrase) for hit in hits}
    assert ("type", "Kind", "kind") in found
    assert ("parameter", "kind", "kind") in found
    assert ("", "", "source") in found


@pytest.mark.skipif(shutil.which("go") is None, reason="needs the Go toolchain")
def test_collect_hits_reports_a_go_comment_as_prose(tmp_path: Path) -> None:
    path = tmp_path / "sample.go"
    path.write_text("package sample\n\n// the source builder\n", encoding="utf-8")
    hits = collect_hits([str(tmp_path)], parse_rules(GLOSSARY))
    assert [hit.rule.phrase for hit in hits] == ["source"]
    assert hits[0].line == 3
    assert hits[0].form == ""


def test_ratchets_count_prose_and_names_separately(tmp_path: Path) -> None:
    glossary = write_glossary(tmp_path)
    (tmp_path / "doc.md").write_text("the source\n", encoding="utf-8")
    (tmp_path / "mod.py").write_text("class Kind: ...\n", encoding="utf-8")
    prose = tmp_path / "prose.txt"
    names = tmp_path / "names.txt"

    args = [
        "--glossary",
        str(glossary),
        "--roots",
        str(tmp_path),
        "--ratchet",
        str(prose),
        "--names-ratchet",
        str(names),
        "--quiet",
    ]
    assert main(args) == 0
    assert prose.read_text().strip() == "1"
    assert names.read_text().strip() == "1"

    assert main(args) == 0
    (tmp_path / "mod.py").write_text(
        "class Kind: ...\nclass Kinds: ...\n", encoding="utf-8"
    )
    assert main(args) == 1
    assert main([*args, "--update-baseline"]) == 0
    assert names.read_text().strip() == "2"


def test_hit_model_carries_the_declaration_form(tmp_path: Path) -> None:
    rules = parse_rules(GLOSSARY)
    declaration = Declaration(
        path=tmp_path / "mod.py", line=1, form="class", value="Kind"
    )
    hits = scan_names(tmp_path / "mod.py", "", rules, [declaration])
    assert hits[0].form == "class"
    assert hits[0].name == "Kind"
