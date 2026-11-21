package shared

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"gopkg.in/yaml.v3"
)

// The root policy files are committed data the Go stages load. These tests read
// the real files, the same way TestLoadCheckPolicy and TestLoadBalancePolicy do.

// allowedBounds names the bound fields each arithmetic may set.
var allowedBounds = map[CheckArithmetic]map[string]bool{
	CheckArithmeticCoverage:      {},
	CheckArithmeticCountFloor:    {"minimum": true},
	CheckArithmeticShareRange:    {"minimum": true, "maximum": true},
	CheckArithmeticRelativeRange: {"below": true, "above": true},
	CheckArithmeticShareTarget:   {"target": true, "tolerance": true},
	CheckArithmeticSetEqual:      {"values": true, "to": true},
}

// requiredBounds names the bound fields each arithmetic must set.
var requiredBounds = map[CheckArithmetic][]string{
	CheckArithmeticCountFloor:    {"minimum"},
	CheckArithmeticRelativeRange: {"below", "above"},
	CheckArithmeticShareTarget:   {"target", "tolerance"},
}

var checkDimensions = map[string]bool{
	"answer_format":             true,
	"answer_meaning":            true,
	"clue_operand_form":         true,
	"clue_type":                 true,
	"correct_answer":            true,
	"geometry_required":         true,
	"program_id":                true,
	"split":                     true,
	"target_category":           true,
	"task_count":                true,
	"task_reasoning_step_count": true,
	"warmup":                    true,
}

var checkRequirements = map[string]bool{
	"DS-37":              true,
	"PRD-8":              true,
	"R-4":                true,
	"R-7":                true,
	"R-8":                true,
	"R-9":                true,
	"R-10":               true,
	"R-11":               true,
	"R-12":               true,
	"R-15":               true,
	"release-contract-3": true,
}

var derivedSets = map[string]bool{"one_step_tasks": true}

// presentBounds names the bound fields a check sets, including values and to.
func presentBounds(check ReleaseCheck) map[string]bool {
	present := make(map[string]bool, 8)
	for name, bound := range namedBounds(check) {
		if bound != nil {
			present[name] = true
		}
	}
	if len(check.Values) > 0 {
		present["values"] = true
	}
	if check.To != nil {
		present["to"] = true
	}
	return present
}

// namedBounds returns the single-scalar bounds a check sets.
func namedBounds(check ReleaseCheck) map[string]*Bound {
	return map[string]*Bound{
		"minimum":   check.Minimum,
		"maximum":   check.Maximum,
		"target":    check.Target,
		"tolerance": check.Tolerance,
		"below":     check.Below,
		"above":     check.Above,
	}
}

func loadRootCheckPolicy(t *testing.T) CheckPolicy {
	t.Helper()

	policy, err := LoadCheckPolicy(filepath.Join(repositoryRoot(t), "checks.yaml"))
	if err != nil {
		t.Fatalf("load check policy: %v", err)
	}
	return policy
}

func TestCheckPolicyBoundVocabulary(t *testing.T) {
	policy := loadRootCheckPolicy(t)

	for _, check := range policy.Checks {
		present := presentBounds(check)

		for name := range present {
			if !allowedBounds[check.Arithmetic][name] {
				t.Errorf("check %q: %s is not a %s bound", check.ID, name, check.Arithmetic)
			}
		}
		for _, name := range requiredBounds[check.Arithmetic] {
			if !present[name] {
				t.Errorf("check %q: %s arithmetic needs %s", check.ID, check.Arithmetic, name)
			}
		}

		switch check.Arithmetic {
		case CheckArithmeticShareRange:
			if len(present) == 0 {
				t.Errorf("check %q: a share range needs a bound", check.ID)
			}
		case CheckArithmeticSetEqual:
			hasValues := present["values"]
			hasTo := present["to"]
			if hasValues == hasTo {
				t.Errorf("check %q: set_equal needs exactly one of values or to", check.ID)
			}
			if hasTo && !derivedSets[*check.To] {
				t.Errorf("check %q: to %q is not a derived set", check.ID, *check.To)
			}
			if hasValues && len(check.Values) == 0 {
				t.Errorf("check %q: values is empty", check.ID)
			}
		}
	}
}

func TestCheckPolicyCitations(t *testing.T) {
	policy := loadRootCheckPolicy(t)

	cited := make(map[string]bool, len(checkRequirements))
	for _, check := range policy.Checks {
		if !checkDimensions[check.Dimension] {
			t.Errorf("check %q: unknown dimension %q", check.ID, check.Dimension)
		}
		if len(check.Requirement) == 0 {
			t.Errorf("check %q: requirement is empty", check.ID)
		}
		for _, requirement := range check.Requirement {
			if !checkRequirements[requirement] {
				t.Errorf("check %q: unknown requirement %q", check.ID, requirement)
			}
			cited[requirement] = true
		}
	}

	for requirement := range checkRequirements {
		if !cited[requirement] {
			t.Errorf("requirement %q is never cited by a check", requirement)
		}
	}
}

// TestCheckBoundsResolveAgainstBalance holds the cross-file contract: a bound
// that is not a number is a dotted path into balance.yaml. The loader checks one
// file at a time, so only this test can see both.
func TestCheckBoundsResolveAgainstBalance(t *testing.T) {
	root := repositoryRoot(t)
	policy := loadRootCheckPolicy(t)
	balance := readYAMLMapping(t, filepath.Join(root, "balance.yaml"))

	resolved := 0
	for _, check := range policy.Checks {
		for name, bound := range namedBounds(check) {
			if bound == nil || bound.IsNumber() {
				continue
			}
			resolved++
			if _, ok := resolveYAMLPath(balance, bound.Raw); !ok {
				t.Errorf("check %q: %s %q does not resolve in balance.yaml", check.ID, name, bound.Raw)
			}
		}
	}
	if resolved == 0 {
		t.Fatal("no path bounds to resolve; the check is vacuous")
	}
}

// readYAMLMapping decodes one YAML document into nested maps.
func readYAMLMapping(t *testing.T, path string) map[string]any {
	t.Helper()

	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read %s: %v", path, err)
	}
	var mapping map[string]any
	if err := yaml.Unmarshal(data, &mapping); err != nil {
		t.Fatalf("decode %s: %v", path, err)
	}
	return mapping
}

// resolveYAMLPath walks a dotted path through nested mappings.
func resolveYAMLPath(node any, path string) (any, bool) {
	for part := range strings.SplitSeq(path, ".") {
		mapping, ok := node.(map[string]any)
		if !ok {
			return nil, false
		}
		node, ok = mapping[part]
		if !ok {
			return nil, false
		}
	}
	return node, true
}
