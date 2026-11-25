package shared

import (
	"fmt"
	"math"
	"os"
	"slices"
	"strconv"

	"gopkg.in/yaml.v3"
)

// CheckArithmetic is a release check's arithmetic.
type CheckArithmetic string

const (
	CheckArithmeticCoverage      CheckArithmetic = "coverage"
	CheckArithmeticCountFloor    CheckArithmetic = "count_floor"
	CheckArithmeticSetEqual      CheckArithmetic = "set_equal"
	CheckArithmeticShareRange    CheckArithmetic = "share_range"
	CheckArithmeticShareTarget   CheckArithmetic = "share_target"
	CheckArithmeticRelativeRange CheckArithmetic = "relative_range"
)

// CheckScope is the population a release check covers.
type CheckScope string

const (
	CheckScopeRelease CheckScope = "release"
	CheckScopePerStep CheckScope = "per_step"
)

// CheckDisposition is what a release check does with its outcome.
type CheckDisposition string

const (
	CheckDispositionEnforced CheckDisposition = "enforced"
	CheckDispositionDeferred CheckDisposition = "deferred"
	CheckDispositionReported CheckDisposition = "reported"
)

// CheckPolicy is the typed root checks.yaml document.
type CheckPolicy struct {
	Version int            `yaml:"version"`
	Checks  []ReleaseCheck `yaml:"checks"`
}

// ReleaseCheck is one row of the release check policy. A bound is a number or
// a dotted path into balance.yaml; Bound preserves the raw scalar so the
// evaluator can resolve it against the balance policy. Value and MinimumValue
// select the dimension value a share_range check measures; they are not balance
// paths.
type ReleaseCheck struct {
	ID           string           `yaml:"id"`
	Requirement  []string         `yaml:"requirement"`
	Arithmetic   CheckArithmetic  `yaml:"arithmetic"`
	Scope        CheckScope       `yaml:"scope"`
	Dimension    string           `yaml:"dimension"`
	Value        *Bound           `yaml:"value"`
	MinimumValue *Bound           `yaml:"minimum_value"`
	Minimum      *Bound           `yaml:"minimum"`
	Maximum      *Bound           `yaml:"maximum"`
	Target       *Bound           `yaml:"target"`
	Tolerance    *Bound           `yaml:"tolerance"`
	To           *string          `yaml:"to"`
	Values       []Bound          `yaml:"values"`
	Below        *Bound           `yaml:"below"`
	Above        *Bound           `yaml:"above"`
	Disposition  CheckDisposition `yaml:"disposition"`
}

// Bound is a numeric literal or a dotted path into balance.yaml.
type Bound struct {
	Raw string
}

// UnmarshalYAML accepts one scalar and preserves its text.
func (b *Bound) UnmarshalYAML(yamlNode *yaml.Node) error {
	if yamlNode.Kind != yaml.ScalarNode {
		return fmt.Errorf("bound must be a scalar, got %s", yamlNode.Tag)
	}
	b.Raw = yamlNode.Value
	return nil
}

// IsNumber reports whether the bound is a literal number.
func (b Bound) IsNumber() bool {
	_, err := strconv.ParseFloat(b.Raw, 64)
	return err == nil
}

// Number returns the literal value. It is an error for a path bound.
func (b Bound) Number() (float64, error) {
	value, err := strconv.ParseFloat(b.Raw, 64)
	if err != nil {
		return 0, fmt.Errorf("bound %q is not a number: %w", b.Raw, err)
	}
	return value, nil
}

// LoadCheckPolicy reads and validates one checks.yaml file. Unknown fields are
// a load error, not a silently ignored check setting.
func LoadCheckPolicy(path string) (CheckPolicy, error) {
	file, err := os.Open(path)
	if err != nil {
		return CheckPolicy{}, fmt.Errorf("open check policy %s: %w", path, err)
	}
	defer file.Close()

	decoder := yaml.NewDecoder(file)
	decoder.KnownFields(true)

	var policy CheckPolicy
	if err := decoder.Decode(&policy); err != nil {
		return CheckPolicy{}, fmt.Errorf("decode check policy %s: %w", path, err)
	}
	if err := policy.Validate(); err != nil {
		return CheckPolicy{}, fmt.Errorf("validate check policy %s: %w", path, err)
	}
	return policy, nil
}

// Validate reports whether the policy is internally consistent.
func (p CheckPolicy) Validate() error {
	if p.Version < 1 {
		return fmt.Errorf("version is %d, minimum is 1", p.Version)
	}
	if len(p.Checks) == 0 {
		return fmt.Errorf("checks is empty")
	}
	seen := make(map[string]struct{}, len(p.Checks))
	for index, check := range p.Checks {
		if err := check.validate(); err != nil {
			return fmt.Errorf("checks[%d]: %w", index, err)
		}
		if _, duplicate := seen[check.ID]; duplicate {
			return fmt.Errorf("checks[%d]: duplicate id %q", index, check.ID)
		}
		seen[check.ID] = struct{}{}
	}
	return nil
}

func (c ReleaseCheck) validate() error {
	if c.ID == "" {
		return fmt.Errorf("id is empty")
	}
	if len(c.Requirement) == 0 {
		return fmt.Errorf("check %q: requirement is empty", c.ID)
	}
	if slices.Contains(c.Requirement, "") {
		return fmt.Errorf("check %q: requirement entry is empty", c.ID)
	}
	switch c.Arithmetic {
	case CheckArithmeticCoverage,
		CheckArithmeticCountFloor,
		CheckArithmeticSetEqual,
		CheckArithmeticShareRange,
		CheckArithmeticShareTarget,
		CheckArithmeticRelativeRange:
	default:
		return fmt.Errorf("check %q: unknown arithmetic %q", c.ID, c.Arithmetic)
	}
	switch c.Scope {
	case CheckScopeRelease, CheckScopePerStep:
	default:
		return fmt.Errorf("check %q: unknown scope %q", c.ID, c.Scope)
	}
	if c.Dimension == "" {
		return fmt.Errorf("check %q: dimension is empty", c.ID)
	}
	switch c.Disposition {
	case CheckDispositionEnforced, CheckDispositionDeferred, CheckDispositionReported:
	default:
		return fmt.Errorf("check %q: unknown disposition %q", c.ID, c.Disposition)
	}
	if err := c.validateMeasuredValue(); err != nil {
		return err
	}
	return c.validateBounds()
}

// validateMeasuredValue checks the two fields that narrow a share_range check
// to one dimension value or a cumulative tail of them.
func (c ReleaseCheck) validateMeasuredValue() error {
	if c.Value == nil && c.MinimumValue == nil {
		return nil
	}
	if c.Arithmetic != CheckArithmeticShareRange {
		return fmt.Errorf("check %q: value and minimum_value select a share_range value", c.ID)
	}
	if c.Value != nil && c.MinimumValue != nil {
		return fmt.Errorf("check %q: set at most one of value and minimum_value", c.ID)
	}
	if c.MinimumValue == nil {
		return nil
	}
	number, err := c.MinimumValue.Number()
	if err != nil {
		return fmt.Errorf("check %q: minimum_value: %w", c.ID, err)
	}
	if math.Trunc(number) != number {
		return fmt.Errorf("check %q: minimum_value %q is not an integer", c.ID, c.MinimumValue.Raw)
	}
	return nil
}

func (c ReleaseCheck) validateBounds() error {
	for name, bound := range map[string]*Bound{
		"value":         c.Value,
		"minimum_value": c.MinimumValue,
		"minimum":       c.Minimum,
		"maximum":       c.Maximum,
		"target":        c.Target,
		"tolerance":     c.Tolerance,
		"below":         c.Below,
		"above":         c.Above,
	} {
		if bound != nil && bound.Raw == "" {
			return fmt.Errorf("check %q: %s is empty", c.ID, name)
		}
	}
	for index, value := range c.Values {
		if value.Raw == "" {
			return fmt.Errorf("check %q: values[%d] is empty", c.ID, index)
		}
	}
	if c.To != nil && *c.To == "" {
		return fmt.Errorf("check %q: to is set but empty", c.ID)
	}
	return nil
}
