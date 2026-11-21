package shared

// The worker contract structs are generated from the checked-in JSON Schema.
// Run `go generate ./internal/shared` from the generator module after changing
// the schema, and commit the result.
//
//go:generate go run github.com/atombender/go-jsonschema@v0.24.1 --package shared --struct-name-from-title --only-models --tags json --capitalization d -o s01d_normalize_programs_contract.go ../../../contracts/worker/v1/s01d_normalize_programs.schema.json
