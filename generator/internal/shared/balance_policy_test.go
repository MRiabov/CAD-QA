package shared

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadBalancePolicy(t *testing.T) {
	root := moduleRoot(t)
	policy, err := LoadBalancePolicy(filepath.Join(root, "config", "balance.yaml"))
	if err != nil {
		t.Fatalf("load balance policy: %v", err)
	}

	if policy.Version != 1 {
		t.Fatalf("version = %d, want 1", policy.Version)
	}
	if policy.Release.TasksMin != 10000 {
		t.Fatalf("release.tasks_min = %d, want 10000", policy.Release.TasksMin)
	}
	if policy.Release.ProgramsMin != 1000 {
		t.Fatalf("release.programs_min = %d, want 1000", policy.Release.ProgramsMin)
	}
	if len(policy.TaskReasoningStepShare) != 10 {
		t.Fatalf("task_reasoning_step_share has %d entries, want 10", len(policy.TaskReasoningStepShare))
	}
	if policy.TaskReasoningStepShare[3] != 0.30 {
		t.Fatalf("step 3 share = %g, want 0.30", policy.TaskReasoningStepShare[3])
	}
	if len(policy.TaskReasoningStepShareP0Fallback) != 5 {
		t.Fatalf(
			"task_reasoning_step_share_p0_fallback has %d entries, want 5",
			len(policy.TaskReasoningStepShareP0Fallback),
		)
	}
	if policy.TaskReasoningStepShareP0Fallback[3] != 0.40 {
		t.Fatalf(
			"fallback step 3 share = %g, want 0.40",
			policy.TaskReasoningStepShareP0Fallback[3],
		)
	}
	if policy.Release.Splits[SplitTrain] != 0.70 {
		t.Fatalf("train split = %g, want 0.70", policy.Release.Splits[SplitTrain])
	}
	if policy.Expansion.Rounds != 3 {
		t.Fatalf("expansion.rounds = %d, want 3", policy.Expansion.Rounds)
	}

	operandForm, ok := policy.Dimensions["clue_operand_form"]
	if !ok {
		t.Fatal("clue_operand_form dimension is missing")
	}
	if operandForm.Target == nil || !operandForm.Target.Equal {
		t.Fatalf("clue_operand_form target = %+v, want equal", operandForm.Target)
	}
	if operandForm.Severe == nil || operandForm.Severe.Above != 4.0 {
		t.Fatalf("clue_operand_form severe = %+v, want above 4.0", operandForm.Severe)
	}
}

func TestLoadBalancePolicyRejectsUnknownField(t *testing.T) {
	path := filepath.Join(t.TempDir(), "balance.yaml")
	document := "version: 1\nunknown_field: true\n"
	if err := os.WriteFile(path, []byte(document), 0o644); err != nil {
		t.Fatalf("write policy: %v", err)
	}

	if _, err := LoadBalancePolicy(path); err == nil {
		t.Fatal("unknown field was accepted")
	}
}

func TestBalancePolicyRejectsBadShares(t *testing.T) {
	policy := BalancePolicy{
		Version: 1,
		Release: ReleaseBalancePolicy{
			TasksMin:          1,
			ProgramsMin:       1,
			DistinctAnswerMin: 1,
			Splits: map[Split]float64{
				SplitTrain:      0.5,
				SplitValidation: 0.5,
				SplitTest:       0.5,
			},
		},
		TaskReasoningStepShare:           map[int]float64{1: 1},
		TaskReasoningStepShareP0Fallback: map[int]float64{1: 1},
		Expansion:                        ExpansionBalancePolicy{Rounds: 1},
		Construction: ConstructionBalancePolicy{
			AttemptMultiplier:              1,
			HighRejectionAttemptMultiplier: 1,
		},
	}
	if err := policy.Validate(); err == nil {
		t.Fatal("split shares summing above 1 were accepted")
	}
}
