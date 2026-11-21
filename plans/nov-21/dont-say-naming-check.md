# Don't-say naming checks — TODO

**Status:** TODO, 2026-11-21. Deferred until the Go module exists
([`file-trees.md`](../../docs/dataset/implementation/file-trees.md) puts it at
`generator/`). The Python half can land earlier.

`tools/check_dont_say.py` checks prose: Markdown, LaTeX, Python comments and
docstrings. It does not check the names a reader navigates by, which is the gap
this note tracks. Every name below must spell the glossary term:

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

## Correct approach

- **Python**: the standard `ast` and `tokenize` modules, already used for
  comments and docstrings. Extend the walk to record each declaration with its
  declaration form, and reuse `identifier_variants` for the snake, kebab, Pascal, and camel
  forms.
- **Go**: the toolchain's own parser, `go/parser` plus `go/ast`. A small helper
  under `tools/` (its own module) reads the `.go` files and prints JSON: one
  record per comment, and one per identifier with its declaration form and line. The
  checker runs that helper once per invocation, the way it reads Markdown.
  `go/parser` is the authority on Go syntax; the checker never guesses.
- **File and folder names** need no parser: split the path and match each part
  through the same rule set, so a file or folder named for a banned term is
  checked like prose.

## Acceptance

- A Go class, function, variable, file name, or folder name that spells a
  banned term is reported with its file and line.
- The same holds for the Python equivalents.
- Identifier hits keep their own baseline
  (`tools/dont_say_identifiers_baseline.txt`), so the naming sweep can land
  after the capability.
- Tests cover one hit and one clean case per named-thing row above, in both
  languages.

## Deferred

- Go: until `generator/` exists. Scanning `.go` before then would check nothing
  and would risk a wrong result.
- The naming sweep itself: the capability first, then lower the identifier
  baseline.
