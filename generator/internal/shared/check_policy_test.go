package shared

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadCheckPolicy(t *testing.T) {
	root := moduleRoot(t)
	policy, err := LoadCheckPolicy(filepath.Join(root, "config", "release-checks.yaml"))
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
	path := filepath.Join(t.TempDir(), "release-checks.yaml")
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

func TestLoadCheckPolicySelectors(t *testing.T) {
	policy := loadRootCheckPolicy(t)
	byID := make(map[string]ReleaseCheck, len(policy.Checks))
	for _, check := range policy.Checks {
		byID[check.ID] = check
	}

	builtShape, ok := byID["built_shape_share_floor"]
	if !ok {
		t.Fatal("built_shape_share_floor check is missing")
	}
	if builtShape.Value == nil || builtShape.Value.Raw != "true" {
		t.Fatalf("built_shape_share_floor value = %+v, want true", builtShape.Value)
	}

	stepThree, ok := byID["steps_three_or_more_share"]
	if !ok {
		t.Fatal("steps_three_or_more_share check is missing")
	}
	if stepThree.MinimumValue == nil || stepThree.MinimumValue.Raw != "3" {
		t.Fatalf("steps_three_or_more_share minimum_value = %+v, want 3", stepThree.MinimumValue)
	}
}

// TestLoadCheckPolicyExtractionCapabilityCoverage pins the check that makes a
// declared extraction capability with no accepted graph a blocking miss.
func TestLoadCheckPolicyExtractionCapabilityCoverage(t *testing.T) {
	policy := loadRootCheckPolicy(t)

	var coverage *ReleaseCheck
	for index := range policy.Checks {
		if policy.Checks[index].ID == "extraction_capability_coverage" {
			coverage = &policy.Checks[index]
			break
		}
	}
	if coverage == nil {
		t.Fatal("extraction_capability_coverage check is missing")
	}
	if coverage.Arithmetic != CheckArithmeticSetEqual {
		t.Fatalf("arithmetic = %q, want set_equal", coverage.Arithmetic)
	}
	if coverage.Scope != CheckScopeRelease {
		t.Fatalf("scope = %q, want release", coverage.Scope)
	}
	if coverage.Dimension != "extraction_capability" {
		t.Fatalf("dimension = %q, want extraction_capability", coverage.Dimension)
	}
	if coverage.To == nil || *coverage.To != "must_extract_capabilities" {
		t.Fatalf("to = %v, want must_extract_capabilities", coverage.To)
	}
	if coverage.Disposition != CheckDispositionEnforced {
		t.Fatalf("disposition = %q, want enforced", coverage.Disposition)
	}
	if len(coverage.Requirement) != 1 || coverage.Requirement[0] != "R-19" {
		t.Fatalf("requirement = %v, want [R-19]", coverage.Requirement)
	}
}

func TestCheckPolicyRejectsTwoSelectors(t *testing.T) {
	check := ReleaseCheck{
		Arithmetic:   CheckArithmeticShareRange,
		Value:        &Bound{Raw: "true"},
		MinimumValue: &Bound{Raw: "3"},
	}
	if err := check.validateMeasuredValue(); err == nil {
		t.Fatal("value and minimum_value were accepted together")
	}
}

func TestCheckPolicyRejectsNonIntegerMinimumValue(t *testing.T) {
	check := ReleaseCheck{
		Arithmetic:   CheckArithmeticShareRange,
		MinimumValue: &Bound{Raw: "3.5"},
	}
	if err := check.validateMeasuredValue(); err == nil {
		t.Fatal("non-integer minimum_value was accepted")
	}
}

func TestCheckPolicyRejectsSelectorOnOtherArithmetic(t *testing.T) {
	check := ReleaseCheck{
		Arithmetic: CheckArithmeticCoverage,
		Value:      &Bound{Raw: "true"},
	}
	if err := check.validateMeasuredValue(); err == nil {
		t.Fatal("value was accepted on a coverage check")
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
