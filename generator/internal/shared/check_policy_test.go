package shared

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadCheckPolicy(t *testing.T) {
	root := moduleRoot(t)
	policy, err := LoadCheckPolicy(filepath.Join(root, "config", "checks.yaml"))
	if err != nil {
		t.Fatalf("load check policy: %v", err)
	}

	if policy.Version != 1 {
		t.Fatalf("version = %d, want 1", policy.Version)
	}
	if len(policy.Checks) == 0 {
		t.Fatal("checks is empty")
	}

	first := policy.Checks[0]
	if first.ID != "target_category_coverage" {
		t.Fatalf("first check id = %q, want target_category_coverage", first.ID)
	}
	if first.Arithmetic != CheckArithmeticCoverage {
		t.Fatalf("first arithmetic = %q, want coverage", first.Arithmetic)
	}
	if first.Scope != CheckScopePerStep {
		t.Fatalf("first scope = %q, want per_step", first.Scope)
	}
	if first.Disposition != CheckDispositionEnforced {
		t.Fatalf("first disposition = %q, want enforced", first.Disposition)
	}

	var taskCount *ReleaseCheck
	for index := range policy.Checks {
		if policy.Checks[index].ID == "release_task_count" {
			taskCount = &policy.Checks[index]
			break
		}
	}
	if taskCount == nil {
		t.Fatal("release_task_count check is missing")
	}
	if taskCount.Minimum == nil || taskCount.Minimum.Raw != "release.tasks_min" {
		t.Fatalf("release_task_count minimum = %+v, want release.tasks_min", taskCount.Minimum)
	}
	if taskCount.Minimum.IsNumber() {
		t.Fatal("release.tasks_min path was read as a number")
	}
}

func TestLoadCheckPolicyRejectsUnknownField(t *testing.T) {
	path := filepath.Join(t.TempDir(), "checks.yaml")
	document := "version: 1\nunknown_field: true\n"
	if err := os.WriteFile(path, []byte(document), 0o644); err != nil {
		t.Fatalf("write policy: %v", err)
	}

	if _, err := LoadCheckPolicy(path); err == nil {
		t.Fatal("unknown field was accepted")
	}
}

func TestCheckPolicyRejectsDuplicateIDs(t *testing.T) {
	check := ReleaseCheck{
		ID:          "duplicate",
		Requirement: []string{"R-8"},
		Arithmetic:  CheckArithmeticCoverage,
		Scope:       CheckScopePerStep,
		Dimension:   "target_category",
		Disposition: CheckDispositionEnforced,
	}
	policy := CheckPolicy{Version: 1, Checks: []ReleaseCheck{check, check}}

	if err := policy.Validate(); err == nil {
		t.Fatal("duplicate check id was accepted")
	}
}

func TestBoundNumber(t *testing.T) {
	bound := Bound{Raw: "0.25"}
	value, err := bound.Number()
	if err != nil {
		t.Fatalf("bound number: %v", err)
	}
	if value != 0.25 {
		t.Fatalf("bound number = %g, want 0.25", value)
	}

	path := Bound{Raw: "release.tasks_min"}
	if path.IsNumber() {
		t.Fatal("dotted path was read as a number")
	}
	if _, err := path.Number(); err == nil {
		t.Fatal("dotted path returned a number")
	}
}
