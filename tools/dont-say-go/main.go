// Command dont-say-go prints every name and comment a Go file declares.
//
// The don't-say checker (tools/ci_cd/check_dont_say.py) owns the banned-term
// policy. This helper owns Go syntax: it prints one JSON object per declared
// name and one per comment line, so the checker never has to guess where a
// comment, a literal, or an identifier ends. A file the parser rejects is an
// error, never a silent skip.
package main

import (
	"encoding/json"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"sort"
	"strings"
)

// record is one declared name or one comment line.
//
// Form "comment" marks prose: Value is the comment text with its markers.
// Every other form marks a declared name: Value is the identifier.
type record struct {
	Path  string `json:"path"`
	Line  int    `json:"line"`
	Form  string `json:"form"`
	Value string `json:"value"`
}

// collector turns one parsed file into records.
type collector struct {
	fset    *token.FileSet
	path    string
	records []record
}

func (c *collector) add(name *ast.Ident, form string) {
	if name == nil || name.Name == "" || name.Name == "_" {
		return
	}
	c.records = append(c.records, record{
		Path:  c.path,
		Line:  c.fset.Position(name.Pos()).Line,
		Form:  form,
		Value: name.Name,
	})
}

// addNames records the names of a field list, such as parameters or results.
func (c *collector) addNames(fields *ast.FieldList, form string) {
	if fields == nil {
		return
	}
	for _, field := range fields.List {
		for _, name := range field.Names {
			c.add(name, form)
		}
	}
}

// addComments records one record per comment line, so a block comment reports
// the line each of its sentences is on.
func (c *collector) addComments(groups []*ast.CommentGroup) {
	for _, group := range groups {
		for _, comment := range group.List {
			line := c.fset.Position(comment.Pos()).Line
			for offset, part := range strings.Split(comment.Text, "\n") {
				c.records = append(c.records, record{
					Path:  c.path,
					Line:  line + offset,
					Form:  "comment",
					Value: part,
				})
			}
		}
	}
}

// visitType records the names declared inside a declared type expression.
func (c *collector) visitType(expr ast.Expr) {
	switch t := expr.(type) {
	case *ast.StructType:
		if t.Fields == nil {
			return
		}
		for _, field := range t.Fields.List {
			for _, name := range field.Names {
				c.add(name, "field")
			}
			c.visitType(field.Type)
		}
	case *ast.InterfaceType:
		if t.Methods == nil {
			return
		}
		for _, method := range t.Methods.List {
			for _, name := range method.Names {
				c.add(name, "interface method")
			}
			if fn, ok := method.Type.(*ast.FuncType); ok {
				c.addNames(fn.Params, "parameter")
				c.addNames(fn.Results, "result")
			}
		}
	}
}

// visitBody records the names a function body declares.
func (c *collector) visitBody(body *ast.BlockStmt) {
	ast.Inspect(body, func(current ast.Node) bool {
		switch n := current.(type) {
		case *ast.DeclStmt:
			decl, ok := n.Decl.(*ast.GenDecl)
			if !ok {
				return true
			}
			form := "variable"
			if decl.Tok == token.CONST {
				form = "constant"
			}
			for _, spec := range decl.Specs {
				if value, ok := spec.(*ast.ValueSpec); ok {
					for _, name := range value.Names {
						c.add(name, form)
					}
				}
			}
		case *ast.AssignStmt:
			if n.Tok != token.DEFINE {
				return true
			}
			for _, expr := range n.Lhs {
				if name, ok := expr.(*ast.Ident); ok {
					c.add(name, "variable")
				}
			}
		case *ast.RangeStmt:
			if n.Tok != token.DEFINE {
				return true
			}
			for _, expr := range []ast.Expr{n.Key, n.Value} {
				if name, ok := expr.(*ast.Ident); ok {
					c.add(name, "variable")
				}
			}
		case *ast.FuncLit:
			if n.Type != nil {
				c.addNames(n.Type.Params, "parameter")
				c.addNames(n.Type.Results, "result")
			}
		}
		return true
	})
}

// visitFile records every name and comment the file declares.
func (c *collector) visitFile(file *ast.File) {
	c.addComments(file.Comments)
	for _, decl := range file.Decls {
		switch d := decl.(type) {
		case *ast.GenDecl:
			for _, spec := range d.Specs {
				switch s := spec.(type) {
				case *ast.TypeSpec:
					c.add(s.Name, "type")
					c.addNames(s.TypeParams, "type parameter")
					c.visitType(s.Type)
				case *ast.ValueSpec:
					form := "variable"
					if d.Tok == token.CONST {
						form = "constant"
					}
					for _, name := range s.Names {
						c.add(name, form)
					}
				}
			}
		case *ast.FuncDecl:
			form := "function"
			if d.Recv != nil {
				form = "method"
			}
			c.add(d.Name, form)
			c.addNames(d.Recv, "parameter")
			if d.Type != nil {
				c.addNames(d.Type.TypeParams, "type parameter")
				c.addNames(d.Type.Params, "parameter")
				c.addNames(d.Type.Results, "result")
			}
			if d.Body != nil {
				c.visitBody(d.Body)
			}
		}
	}
}

func collect(path string, file *ast.File, fset *token.FileSet) []record {
	c := &collector{fset: fset, path: path}
	c.visitFile(file)
	sortRecords(c.records)
	return c.records
}

// sortRecords puts records in a stable order: path, line, form, value.
func sortRecords(records []record) {
	sort.Slice(records, func(i, j int) bool {
		a, b := records[i], records[j]
		if a.Path != b.Path {
			return a.Path < b.Path
		}
		if a.Line != b.Line {
			return a.Line < b.Line
		}
		if a.Form != b.Form {
			return a.Form < b.Form
		}
		return a.Value < b.Value
	})
}

func main() {
	paths := os.Args[1:]
	if len(paths) == 0 {
		fmt.Fprintln(os.Stderr, "usage: dont-say-go FILE.go...")
		os.Exit(2)
	}

	fset := token.NewFileSet()
	records := make([]record, 0, len(paths))
	for _, path := range paths {
		file, err := parser.ParseFile(fset, path, nil, parser.SkipObjectResolution|parser.ParseComments)
		if err != nil {
			fmt.Fprintf(os.Stderr, "dont-say-go: %v\n", err)
			os.Exit(1)
		}
		records = append(records, collect(path, file, fset)...)
	}

	sortRecords(records)

	encoder := json.NewEncoder(os.Stdout)
	for _, rec := range records {
		if err := encoder.Encode(rec); err != nil {
			fmt.Fprintf(os.Stderr, "dont-say-go: %v\n", err)
			os.Exit(1)
		}
	}
}
