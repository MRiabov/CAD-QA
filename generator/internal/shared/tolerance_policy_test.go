package shared

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"

	"gopkg.in/yaml.v3"
)

// The root measurement tolerance policy is committed data. `02c` build CAD graph
// reads it through the run manifest, so its schema is checked here rather than in
// the Python suite. The shape is the TolerancePolicy model in
// docs/dataset/implementation/pipeline/extraction/graph-persistence.md.

var toleranceUnits = map[string]bool{
	"millimetre":        true,
	"square_millimetre": true,
	"cubic_millimetre":  true,
	"degree":            true,
	"radian":            true,
	"unitless":          true,
}

var toleranceKinds = map[string]bool{
	"exact":    true,
	"absolute": true,
	"relative": true,
}

type toleranceEntry struct {
	ToleranceKind string   `yaml:"kind"`
	Value         *float64 `yaml:"value"`
}

type tolerancePolicy struct {
	Version int                       `yaml:"version"`
	Policy  map[string]toleranceEntry `yaml:"policy"`
}

func TestTolerancePolicy(t *testing.T) {
	path := filepath.Join(repositoryRoot(t), "tolerance.yaml")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read %s: %v", path, err)
	}

	decoder := yaml.NewDecoder(bytes.NewReader(data))
	decoder.KnownFields(true)

	var policy tolerancePolicy
	if err := decoder.Decode(&policy); err != nil {
		t.Fatalf("decode %s: %v", path, err)
	}

	if policy.Version < 1 {
		t.Errorf("version = %d, minimum is 1", policy.Version)
	}
	if len(policy.Policy) != len(toleranceUnits) {
		t.Errorf("policy has %d entries, want %d", len(policy.Policy), len(toleranceUnits))
	}

	for unit, entry := range policy.Policy {
		if !toleranceUnits[unit] {
			t.Errorf("unknown unit %q", unit)
		}
		if !toleranceKinds[entry.ToleranceKind] {
			t.Errorf("%s: unknown kind %q", unit, entry.ToleranceKind)
		}
		if entry.ToleranceKind == "exact" {
			if entry.Value != nil {
				t.Errorf("%s: exact must not carry a value", unit)
			}
			continue
		}
		if entry.Value == nil {
			t.Errorf("%s: %s needs a value", unit, entry.ToleranceKind)
			continue
		}
		if *entry.Value < 0 {
			t.Errorf("%s: value = %v, must not be negative", unit, *entry.Value)
		}
	}

	for unit := range toleranceUnits {
		if _, ok := policy.Policy[unit]; !ok {
			t.Errorf("policy is missing unit %q", unit)
		}
	}
	if policy.Policy["unitless"].ToleranceKind != "exact" {
		t.Errorf("unitless kind = %q, want exact", policy.Policy["unitless"].ToleranceKind)
	}
}
