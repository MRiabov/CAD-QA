# Don't-say naming checks

**Status:** done, 2026-11-21. The checker reports declared names in Python, Go,
and JSON, plus file and folder names, alongside the prose it already checked.
`tools/ci_cd/check_dont_say.py` is the entry point; the rule and matching policy
is `tools/ci_cd/dont_say_rules.py`, file walking and scanning is
`tools/ci_cd/dont_say_scan.py`, and syntax extraction is
`tools/ci_cd/dont_say_names.py` (Python, JSON, paths) and `tools/dont-say-go/`
(Go).

Every name below must spell the glossary term:

| Named thing | Python | Go |
|---|---|---|
| class | `ast.ClassDef.name` | `ast.TypeSpec.name` |
| function or method | `ast.FunctionDef.name` | `ast.FuncDecl.name` |
| variable, field, parameter | `ast.Name`, `ast.arg`, assignment targets | `ast.Ident` in `ValueSpec`, `Field`, `FieldList` |
| file name | `Path.stem` | `Path.stem` |
| folder name | path parts | path parts |

## Rejected approach

A hand-written lexer over Go text (commit `6809792`, reverted in `806af15`)
guessed where comments and literals end. It cannot tell a struct name from a
local, cannot see a declaration, and silently misses or invents hits. Do not
replace it with a regex scanner either.

## What landed

- **Python**: the standard `ast` module walks the module once and records
  classes, functions and methods, parameters, assignment targets (including
  `self.field`), loop and comprehension targets, `with`/`except`/`match`
  captures, declared type aliases, and declared type parameters. Comments and docstrings are
  matched as prose, as before.
- **Go**: `tools/dont-say-go` is its own module and prints one JSON record per
  declared name and per comment line, using `go/parser` and `go/ast`. The
  checker runs it once per invocation over every `.go` file. A file the parser
  rejects exits non-zero, so a syntax error is never a silent skip.
- **JSON**: `properties`, `$defs`, `definitions`, `patternProperties`,
  `dependentSchemas`, `enum`, and `const` values are names; `description` and
  `title` are prose. Schema vocabulary (`type`, `items`, `required`, …) is not
  a CAD-QA name.
- **File and folder names** are checked without a parser: each path part is
  split into word segments through the same rule set.
- **Matching**: the rule's words must appear as consecutive name segments, so
  snake, kebab, Pascal, and camel spellings all match. A bare term is allowed
  when a preceding segment qualifies it (`clue_type`); a leading verb does not
  (`get_type` is a hit).
- **Ratchets**: `tools/ci_cd/dont_say_baseline.txt` counts prose hits and
  `tools/ci_cd/dont_say_names_baseline.txt` counts declared-name hits. Both are
  enforced by the `dont-say` pre-commit hook and by CI.

## Acceptance

- A Go class, function, variable, file name, or folder name that spells a
  banned term is reported with its file and line. `tests/test_check_dont_say.py`
  covers the Go path end to end.
- The same holds for the Python equivalents.
- Identifier hits keep their own baseline, so the naming sweep can land after
  the capability.
- Tests cover one hit and one clean case per named-thing row above, in both
  languages.

## Deferred

- The naming sweep itself: the capability is in place, and the name baseline is at
  zero. `development-plan.md` Phase 6 owns keeping it there.
