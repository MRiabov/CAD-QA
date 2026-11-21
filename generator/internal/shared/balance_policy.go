package shared

import (
	"errors"
	"fmt"
	"math"
	"os"

	"gopkg.in/yaml.v3"
)

// Split is a release split name.
type Split string

const (
	SplitTrain      Split = "train"
	SplitValidation Split = "validation"
	SplitTest       Split = "test"
)

// BalancePolicy is the typed root balance.yaml document. It carries every
// tunable quota and balance number; coverage and scope come from the task
// reasoning step support tables, not from this file.
type BalancePolicy struct {
	Version                int                  `yaml:"version"`
	Release                ReleaseBalancePolicy `yaml:"release"`
	TaskReasoningStepShare map[int]float64      `yaml:"task_reasoning_step_share"`
	// TODO(bootstrap): the 6-10 gate selects this fallback mix. 03a must
	// choose between the two maps from the gate result, not read only one.
	TaskReasoningStepShareP0Fallback map[int]float64                   `yaml:"task_reasoning_step_share_p0_fallback"`
	Expansion                        ExpansionBalancePolicy            `yaml:"expansion"`
	Construction                     ConstructionBalancePolicy         `yaml:"construction"`
	Dimensions                       map[string]DimensionBalancePolicy `yaml:"dimensions"`
}

// ReleaseBalancePolicy holds release-level floors, caps, and split shares.
type ReleaseBalancePolicy struct {
	TasksMin                int               `yaml:"tasks_min"`
	ProgramsMin             int               `yaml:"programs_min"`
	BuiltShapeMinShare      float64           `yaml:"built_shape_min_share"`
	ThreeOrMoreStepMinShare float64           `yaml:"three_or_more_step_min_share"`
	CadModelMaxShare        float64           `yaml:"cad_model_max_share"`
	ShareTolerance          float64           `yaml:"share_tolerance"`
	Splits                  map[Split]float64 `yaml:"splits"`
	DistinctAnswerMin       int               `yaml:"distinct_answer_min"`
	CorrectAnswerMaxShare   float64           `yaml:"correct_answer_max_share"`
}

// ExpansionBalancePolicy holds the slow-loop expansion rounds.
type ExpansionBalancePolicy struct {
	Rounds              int     `yaml:"rounds"`
	GrowthSharePerRound float64 `yaml:"growth_share_per_round"`
}

// ConstructionBalancePolicy holds the construction attempt multipliers.
type ConstructionBalancePolicy struct {
	AttemptMultiplier              float64 `yaml:"attempt_multiplier"`
	HighRejectionAttemptMultiplier float64 `yaml:"high_rejection_attempt_multiplier"`
}

// DimensionBalancePolicy holds the default and per-value bounds for one
// coverage dimension. A nil bound is absent and takes the dimension meaning.
type DimensionBalancePolicy struct {
	Min    *float64                      `yaml:"min"`
	Max    *float64                      `yaml:"max"`
	Target *DimensionTarget              `yaml:"target"`
	Severe *SevereBalancePolicy          `yaml:"severe"`
	Values map[string]ValueBalancePolicy `yaml:"values"`
}

// ValueBalancePolicy overrides one dimension value.
type ValueBalancePolicy struct {
	Min    *float64         `yaml:"min"`
	Max    *float64         `yaml:"max"`
	Target *DimensionTarget `yaml:"target"`
}

// SevereBalancePolicy holds the multiples that make an imbalance severe.
type SevereBalancePolicy struct {
	Below float64 `yaml:"below"`
	Above float64 `yaml:"above"`
}

// DimensionTarget is either the literal `equal` or a numeric share.
type DimensionTarget struct {
	Equal bool
	Share float64
}

// UnmarshalYAML accepts `equal` or a number.
func (t *DimensionTarget) UnmarshalYAML(node *yaml.Node) error {
	if node.Kind != yaml.ScalarNode {
		return fmt.Errorf("target must be a scalar, got %s", node.Tag)
	}
	if node.Value == "equal" {
		t.Equal = true
		t.Share = 0
		return nil
	}
	var share float64
	if err := node.Decode(&share); err != nil {
		return fmt.Errorf("target must be `equal` or a number: %w", err)
	}
	t.Equal = false
	t.Share = share
	return nil
}

// LoadBalancePolicy reads and validates one balance.yaml file. Unknown fields
// are a load error, not a silently ignored setting.
func LoadBalancePolicy(path string) (BalancePolicy, error) {
	file, err := os.Open(path)
	if err != nil {
		return BalancePolicy{}, fmt.Errorf("open balance policy %s: %w", path, err)
	}
	defer file.Close()

	decoder := yaml.NewDecoder(file)
	decoder.KnownFields(true)

	var policy BalancePolicy
	if err := decoder.Decode(&policy); err != nil {
		return BalancePolicy{}, fmt.Errorf("decode balance policy %s: %w", path, err)
	}
	if err := policy.Validate(); err != nil {
		return BalancePolicy{}, fmt.Errorf("validate balance policy %s: %w", path, err)
	}
	return policy, nil
}

// Validate reports whether the policy is internally consistent.
func (p BalancePolicy) Validate() error {
	if p.Version < 1 {
		return fmt.Errorf("version is %d, minimum is 1", p.Version)
	}
	if err := p.Release.validate(); err != nil {
		return err
	}
	if err := validateStepShare("task_reasoning_step_share", p.TaskReasoningStepShare, 10); err != nil {
		return err
	}
	if err := validateStepShare(
		"task_reasoning_step_share_p0_fallback",
		p.TaskReasoningStepShareP0Fallback,
		5,
	); err != nil {
		return err
	}
	if p.Expansion.Rounds < 1 {
		return fmt.Errorf("expansion.rounds is %d, minimum is 1", p.Expansion.Rounds)
	}
	if err := share("expansion.growth_share_per_round", p.Expansion.GrowthSharePerRound); err != nil {
		return err
	}
	if p.Construction.AttemptMultiplier < 1 {
		return fmt.Errorf("construction.attempt_multiplier is %g, minimum is 1", p.Construction.AttemptMultiplier)
	}
	if p.Construction.HighRejectionAttemptMultiplier < p.Construction.AttemptMultiplier {
		return fmt.Errorf(
			"construction.high_rejection_attempt_multiplier %g is below attempt_multiplier %g",
			p.Construction.HighRejectionAttemptMultiplier,
			p.Construction.AttemptMultiplier,
		)
	}
	for name, dimension := range p.Dimensions {
		if err := dimension.validate(name); err != nil {
			return err
		}
	}
	return nil
}

func (p ReleaseBalancePolicy) validate() error {
	if p.TasksMin < 1 {
		return fmt.Errorf("release.tasks_min is %d, minimum is 1", p.TasksMin)
	}
	if p.ProgramsMin < 1 {
		return fmt.Errorf("release.programs_min is %d, minimum is 1", p.ProgramsMin)
	}
	if p.DistinctAnswerMin < 1 {
		return fmt.Errorf("release.distinct_answer_min is %d, minimum is 1", p.DistinctAnswerMin)
	}
	shares := map[string]float64{
		"release.built_shape_min_share":        p.BuiltShapeMinShare,
		"release.three_or_more_step_min_share": p.ThreeOrMoreStepMinShare,
		"release.cad_model_max_share":          p.CadModelMaxShare,
		"release.share_tolerance":              p.ShareTolerance,
		"release.correct_answer_max_share":     p.CorrectAnswerMaxShare,
	}
	for name, value := range shares {
		if err := share(name, value); err != nil {
			return err
		}
	}
	return validateSplits(p.Splits)
}

func validateSplits(splits map[Split]float64) error {
	if len(splits) == 0 {
		return errors.New("release.splits is empty")
	}
	total := 0.0
	for split, value := range splits {
		switch split {
		case SplitTrain, SplitValidation, SplitTest:
		default:
			return fmt.Errorf("release.splits has unknown split %q", split)
		}
		if err := share("release.splits."+string(split), value); err != nil {
			return err
		}
		total += value
	}
	if math.Abs(total-1) > 1e-9 {
		return fmt.Errorf("release.splits sums to %g, expected 1", total)
	}
	return nil
}

func validateStepShare(name string, stepShare map[int]float64, maximumStep int) error {
	if len(stepShare) == 0 {
		return fmt.Errorf("%s is empty", name)
	}
	total := 0.0
	for step, value := range stepShare {
		if step < 1 || step > maximumStep {
			return fmt.Errorf("%s has step %d, expected 1..%d", name, step, maximumStep)
		}
		if err := share(fmt.Sprintf("%s.%d", name, step), value); err != nil {
			return err
		}
		total += value
	}
	if math.Abs(total-1) > 1e-9 {
		return fmt.Errorf("%s sums to %g, expected 1", name, total)
	}
	return nil
}

func (d DimensionBalancePolicy) validate(name string) error {
	if d.Min != nil {
		if err := share("dimensions."+name+".min", *d.Min); err != nil {
			return err
		}
	}
	if d.Max != nil {
		if err := share("dimensions."+name+".max", *d.Max); err != nil {
			return err
		}
	}
	if d.Min != nil && d.Max != nil && *d.Min > *d.Max {
		return fmt.Errorf("dimensions.%s.min %g is above max %g", name, *d.Min, *d.Max)
	}
	if d.Target != nil {
		if err := d.Target.validate("dimensions." + name + ".target"); err != nil {
			return err
		}
	}
	if d.Severe != nil {
		if d.Severe.Below <= 0 {
			return fmt.Errorf("dimensions.%s.severe.below is %g, must be positive", name, d.Severe.Below)
		}
		if d.Severe.Above <= 0 {
			return fmt.Errorf("dimensions.%s.severe.above is %g, must be positive", name, d.Severe.Above)
		}
	}
	for value, override := range d.Values {
		if override.Min != nil {
			if err := share("dimensions."+name+".values."+value+".min", *override.Min); err != nil {
				return err
			}
		}
		if override.Max != nil {
			if err := share("dimensions."+name+".values."+value+".max", *override.Max); err != nil {
				return err
			}
		}
		if override.Min != nil && override.Max != nil && *override.Min > *override.Max {
			return fmt.Errorf(
				"dimensions.%s.values.%s.min %g is above max %g",
				name, value, *override.Min, *override.Max,
			)
		}
		if override.Target != nil {
			if err := override.Target.validate("dimensions." + name + ".values." + value + ".target"); err != nil {
				return err
			}
		}
	}
	return nil
}

func (t DimensionTarget) validate(name string) error {
	if t.Equal {
		return nil
	}
	return share(name, t.Share)
}

func share(name string, value float64) error {
	if math.IsNaN(value) || value < 0 || value > 1 {
		return fmt.Errorf("%s is %g, expected a share in [0, 1]", name, value)
	}
	return nil
}
