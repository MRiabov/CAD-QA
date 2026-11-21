package main

import (
	"go/parser"
	"go/token"
	"reflect"
	"testing"
)

func parseSample(t *testing.T, text string) []record {
	t.Helper()
	fset := token.NewFileSet()
	file, err := parser.ParseFile(fset, "sample.go", text, parser.SkipObjectResolution|parser.ParseComments)
	if err != nil {
		t.Fatalf("parse: %v", err)
	}
	return collect("sample.go", file, fset)
}

func TestCollectDeclarations(t *testing.T) {
	text := `package sample

const maxCount = 3

var global int

type Row struct {
	Kind   string
	Nested struct {
		Inner int
	}
}

type Reader interface {
	Read(p []byte) (n int, err error)
}

func build(node string, count int) (total int) {
	local := 1
	var declared int
	for index, value := range []int{1} {
		_, _ = index, value
	}
	fn := func(inner int) int { return inner }
	return local + declared + fn(count)
}

func (r Row) Label(prefix string) string { return prefix }
`
	got := parseSample(t, text)
	want := []record{
		{Path: "sample.go", Line: 3, Form: "constant", Value: "maxCount"},
		{Path: "sample.go", Line: 5, Form: "variable", Value: "global"},
		{Path: "sample.go", Line: 7, Form: "type", Value: "Row"},
		{Path: "sample.go", Line: 8, Form: "field", Value: "Kind"},
		{Path: "sample.go", Line: 9, Form: "field", Value: "Nested"},
		{Path: "sample.go", Line: 10, Form: "field", Value: "Inner"},
		{Path: "sample.go", Line: 14, Form: "type", Value: "Reader"},
		{Path: "sample.go", Line: 15, Form: "interface method", Value: "Read"},
		{Path: "sample.go", Line: 15, Form: "parameter", Value: "p"},
		{Path: "sample.go", Line: 15, Form: "result", Value: "err"},
		{Path: "sample.go", Line: 15, Form: "result", Value: "n"},
		{Path: "sample.go", Line: 18, Form: "function", Value: "build"},
		{Path: "sample.go", Line: 18, Form: "parameter", Value: "count"},
		{Path: "sample.go", Line: 18, Form: "parameter", Value: "node"},
		{Path: "sample.go", Line: 18, Form: "result", Value: "total"},
		{Path: "sample.go", Line: 19, Form: "variable", Value: "local"},
		{Path: "sample.go", Line: 20, Form: "variable", Value: "declared"},
		{Path: "sample.go", Line: 21, Form: "variable", Value: "index"},
		{Path: "sample.go", Line: 21, Form: "variable", Value: "value"},
		{Path: "sample.go", Line: 24, Form: "parameter", Value: "inner"},
		{Path: "sample.go", Line: 24, Form: "variable", Value: "fn"},
		{Path: "sample.go", Line: 28, Form: "method", Value: "Label"},
		{Path: "sample.go", Line: 28, Form: "parameter", Value: "prefix"},
		{Path: "sample.go", Line: 28, Form: "parameter", Value: "r"},
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("records mismatch:\ngot  %#v\nwant %#v", got, want)
	}
}

func TestCollectIgnoresBlankAndUnnamed(t *testing.T) {
	text := `package sample

func build(_ string, _ int) {}

type Empty struct {
	Embedded
}
`
	got := parseSample(t, text)
	want := []record{
		{Path: "sample.go", Line: 3, Form: "function", Value: "build"},
		{Path: "sample.go", Line: 5, Form: "type", Value: "Empty"},
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("records mismatch:\ngot  %#v\nwant %#v", got, want)
	}
}

func TestCollectGenericTypeParameters(t *testing.T) {
	text := `package sample

type Cache[Key comparable, Value any] struct {
	items map[Key]Value
}

func Map[Item any](input []Item) []Item { return input }
`
	got := parseSample(t, text)
	want := []record{
		{Path: "sample.go", Line: 3, Form: "type", Value: "Cache"},
		{Path: "sample.go", Line: 3, Form: "type parameter", Value: "Key"},
		{Path: "sample.go", Line: 3, Form: "type parameter", Value: "Value"},
		{Path: "sample.go", Line: 4, Form: "field", Value: "items"},
		{Path: "sample.go", Line: 7, Form: "function", Value: "Map"},
		{Path: "sample.go", Line: 7, Form: "parameter", Value: "input"},
		{Path: "sample.go", Line: 7, Form: "type parameter", Value: "Item"},
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("records mismatch:\ngot  %#v\nwant %#v", got, want)
	}
}

func TestCollectCommentsByLine(t *testing.T) {
	text := `package sample

// The text builder.
func build() {}

/* First line.
Second line.
*/
var global int
`
	got := parseSample(t, text)
	want := []record{
		{Path: "sample.go", Line: 3, Form: "comment", Value: "// The text builder."},
		{Path: "sample.go", Line: 4, Form: "function", Value: "build"},
		{Path: "sample.go", Line: 6, Form: "comment", Value: "/* First line."},
		{Path: "sample.go", Line: 7, Form: "comment", Value: "Second line."},
		{Path: "sample.go", Line: 8, Form: "comment", Value: "*/"},
		{Path: "sample.go", Line: 9, Form: "variable", Value: "global"},
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("records mismatch:\ngot  %#v\nwant %#v", got, want)
	}
}
