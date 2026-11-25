# 03 task generation — typed models

> Owning pipeline stages: `03a`, `03b`, `03c` (Go).
> Contracts: [`../../../03-task-generation.md`](../../03-task-generation.md),
> [`../../../03-task-generation/03a-allocate-task-quotas/README.md`](../../03-task-generation/03a-allocate-task-quotas/README.md),
> [`../../../03-task-generation/03b-construct-task-definitions/README.md`](../../03-task-generation/03b-construct-task-definitions/README.md),
> [`../../../03-task-generation/03c-resolve-deficits.md`](../../03-task-generation/03c-resolve-deficits.md).

## Shared enums

```go
type Split string

const (
	SplitTrain      Split = "train"
	SplitValidation Split = "validation"
	SplitTest       Split = "test"
)

type Subset string

const (
	SubsetWarmup Subset = "warmup"
	SubsetMain   Subset = "main"
)

type QuotaDimension string

const (
	DimensionTargetCategory  QuotaDimension = "target_category"
	DimensionClueType        QuotaDimension = "clue_type"
	DimensionClueReductionForm QuotaDimension = "clue_reduction_form"
	DimensionAnswerMeaning   QuotaDimension = "answer_meaning"
	DimensionAnswerFormat    QuotaDimension = "answer_format"
)

type QuotaPriority string

const (
	PriorityCoverage QuotaPriority = "coverage"
	PriorityBalance  QuotaPriority = "balance"
	PriorityVolume   QuotaPriority = "volume"
)

type ExpansionTier string

const (
	ExpansionTierC  ExpansionTier = "C"
	ExpansionTierCP ExpansionTier = "C+P"
)

type DeficitClass string

const (
	DeficitCapability   DeficitClass = "capability_deficit"
	DeficitProbe        DeficitClass = "probe_deficit"
	DeficitCapacity     DeficitClass = "capacity_deficit"
	DeficitConstruction DeficitClass = "construction_deficit"
	DeficitConstructor  DeficitClass = "constructor_deficit"
	DeficitPlanConflict DeficitClass = "plan_conflict"
	DeficitStructural   DeficitClass = "structural_deficit"
)

type AllocationDetail string

const (
	DetailCoverageInfeasible       AllocationDetail = "coverage_infeasible"
	DetailAnswerMeaningInfeasible  AllocationDetail = "answer_meaning_infeasible"
	DetailClueCoverageInfeasible   AllocationDetail = "clue_coverage_infeasible"
	DetailIdentityQuotaInfeasible  AllocationDetail = "identity_quota_infeasible"
	DetailCapConflict              AllocationDetail = "cap_conflict"
	DetailSplitCapacityShort       AllocationDetail = "split_capacity_short"
	DetailFamilyQuotaShort         AllocationDetail = "family_quota_short"
	DetailQuotaTargetUnassigned    AllocationDetail = "quota_target_family_unassigned"
	DetailFamilyTargetConflict     AllocationDetail = "family_quota_target_conflict"
	DetailProgramFloorShort        AllocationDetail = "program_floor_short"
	DetailConstructionBudget       AllocationDetail = "construction_budget"
)

type TargetCategory string

const (
	TargetCadQueryProgram        TargetCategory = "cadquery_program"
	TargetOperation              TargetCategory = "operation"
	TargetFeature                TargetCategory = "feature"
	TargetSolidState             TargetCategory = "solid_state"
	TargetFace                   TargetCategory = "face"
	TargetEdge                   TargetCategory = "edge"
	TargetVertex                 TargetCategory = "vertex"
	TargetEdgeEndpoint           TargetCategory = "edge_endpoint"
	TargetCadQueryProfile        TargetCategory = "cadquery_profile"
	TargetCadQueryWorkplane      TargetCategory = "cadquery_workplane"
	TargetPath                   TargetCategory = "path"
	TargetPathPoint              TargetCategory = "path_point"
	TargetPathSegment            TargetCategory = "path_segment"
	TargetRegion                 TargetCategory = "region"
	TargetCadQuerySelectorResult TargetCategory = "cadquery_selector_result"
	TargetScalarValue            TargetCategory = "scalar_value"
)

type ClueType string

const (
	ClueProperty   ClueType = "property"
	ClueRelation   ClueType = "relation"
	ClueComparison ClueType = "comparison"
	ClueAggregation ClueType = "aggregation"
	ClueProvenance ClueType = "provenance"
)

type ClueReductionForm string

const (
	ReductionFiltered              ClueReductionForm = "filtered"
	ReductionSelectedInEarlierClue ClueReductionForm = "selected_in_earlier_clue"
	ReductionAggregated            ClueReductionForm = "aggregated"
	ReductionCrossState            ClueReductionForm = "cross_state"
)

type AnswerMeaning string

const (
	AnswerIdentity       AnswerMeaning = "identity"
	AnswerVolume         AnswerMeaning = "volume"
	AnswerArea           AnswerMeaning = "area"
	AnswerLength         AnswerMeaning = "length"
	AnswerDistance       AnswerMeaning = "distance"
	AnswerAngle          AnswerMeaning = "angle"
	AnswerCount          AnswerMeaning = "count"
	AnswerRank           AnswerMeaning = "rank"
	AnswerMembership     AnswerMeaning = "membership"
	AnswerValidity       AnswerMeaning = "validity"
	AnswerPosition       AnswerMeaning = "position"
	AnswerExtent         AnswerMeaning = "extent"
	AnswerWorkplaneState AnswerMeaning = "cadquery_workplane_state"
	AnswerMaterialChange AnswerMeaning = "material_change"
	AnswerTopologyChange AnswerMeaning = "topology_change"
)

type AnswerFormat string

const (
	FormatMultipleChoice AnswerFormat = "multiple_choice"
	FormatNumber         AnswerFormat = "number"
	FormatInteger        AnswerFormat = "integer"
	FormatBoolean        AnswerFormat = "boolean"
	FormatCoordinate     AnswerFormat = "coordinate"
	FormatBoundingBox    AnswerFormat = "bounding_box"
	FormatStructured     AnswerFormat = "structured"
)

type ScoringRule string

const (
	ScoringExact           ScoringRule = "exact"
	ScoringNumericTolerance ScoringRule = "numeric_tolerance"
	ScoringStructuredExact ScoringRule = "structured_exact"
)

type StateScope string

const (
	StateScopeFinal StateScope = "final"
)

type ProgramRequestMode string

const (
	RequestExtend ProgramRequestMode = "extend"
	RequestTarget ProgramRequestMode = "target"
)
```

## 03a — census and plan

```go
type ProgramCapabilityCensus struct {
	TargetCategories           []TargetCategory                  `parquet:"target_categories"`
	ClueConstructors           []ClueConstructor                 `parquet:"clue_constructors"`
	ClueReductionForms           map[ClueType][]ClueReductionForm    `parquet:"clue_reduction_forms"`
	Measurements               map[string][]string               `parquet:"measurements"`
	AnswerMeanings             []AnswerMeaning                   `parquet:"answer_meanings"`
	MaxTaskReasoningStepCount  []TaskStepBound                   `parquet:"max_task_reasoning_step_count"`
	EntityCounts               map[TargetCategory]int            `parquet:"entity_counts"`
	StatesWithPointProbe       int                               `parquet:"states_with_point_probe"`
}

type TaskStepBound struct {
	TargetCategory TargetCategory `parquet:"target_category"`
	AnswerMeaning  AnswerMeaning  `parquet:"answer_meaning"`
	MaxSteps       int            `parquet:"max_steps"`
}

type ClueConstructor struct {
	ClueType      ClueType    `parquet:"clue_type"`
	RelationType  *string     `parquet:"relation_type"` // null for an angle relation
	Measurement   *string     `parquet:"measurement"`
}

type FamilyProfile struct {
	CadevolveProgramFamilyID   string                          `parquet:"cadevolve_program_family_id"`
	ProgramCount               int                             `parquet:"program_count"`
	Split                      *Split                          `parquet:"split"`
	TargetCategories           []TargetCategory                `parquet:"target_categories"`
	ClueConstructors           []ClueConstructor               `parquet:"clue_constructors"`
	ClueReductionForms           map[ClueType][]ClueReductionForm  `parquet:"clue_reduction_forms"`
	Measurements               map[string][]string             `parquet:"measurements"`
	AnswerMeanings             []AnswerMeaning                 `parquet:"answer_meanings"`
	AnswerFormats              []AnswerFormat                  `parquet:"answer_formats"`
	MaxTaskReasoningStepCount  []TaskStepBound                 `parquet:"max_task_reasoning_step_count"`
	StatesWithPointProbe       int                             `parquet:"states_with_point_probe"`
	EntityCounts               map[TargetCategory]int          `parquet:"entity_counts"`
	TaskQuotaPerProgram        int                             `parquet:"task_quota_per_program"`
	FamilyTaskCapacity         int                             `parquet:"family_task_capacity"`
	ProbeSuccessRate           float64                         `parquet:"probe_success_rate"`
	QuotaTargetProbeSuccessRates map[string]float64            `parquet:"quota_target_probe_success_rates"`
}

type QuotaTarget struct {
	TaskReasoningStepCount int            `parquet:"task_reasoning_step_count"`
	QuotaDimension         QuotaDimension `parquet:"quota_dimension"`
	DimensionValue         string         `parquet:"dimension_value"`
	Minimum                int            `parquet:"minimum"`
	QuotaTargetCount       int            `parquet:"quota_target_count"`
	Maximum                int            `parquet:"maximum"`
	Priority               QuotaPriority  `parquet:"priority"`
}

type ClueQuota struct {
	TaskReasoningStepCount int       `parquet:"task_reasoning_step_count"`
	ClueType               ClueType  `parquet:"clue_type"`
	Minimum                int       `parquet:"minimum"`
	TargetCount            int       `parquet:"target_count"`
	Maximum                int       `parquet:"maximum"`
}

type FamilyAssignment struct {
	CadevolveProgramFamilyID    string         `parquet:"cadevolve_program_family_id"`
	Split                       Split          `parquet:"split"`
	TaskQuota                   int            `parquet:"task_quota"`
	TaskReasoningStepQuotas     map[int]int    `parquet:"task_reasoning_step_quotas"`
	QuotaTargets                []QuotaTarget  `parquet:"quota_targets"`
}

type ConstructionAttemptBudget struct {
	CadevolveProgramFamilyID    string `parquet:"cadevolve_program_family_id"`
	TaskReasoningStepCount      int    `parquet:"task_reasoning_step_count"`
	AttemptBudget               int    `parquet:"attempt_budget"`
}

type ProgramCensusEntry struct {
	ProgramSHA256 string                   `parquet:"program_sha256"`
	GraphIdentitySHA256 string             `parquet:"graph_identity_sha256"`
	Census        ProgramCapabilityCensus  `parquet:"census"`
}

type TaskQuotaPlan struct { // Parquet
	PlanVersion                    int                              `parquet:"plan_version"`
	ParentPlanVersion              *int                             `parquet:"parent_plan_version"`
	Seed                           int64                            `parquet:"seed"`
	BalancePolicyVersion           int                              `parquet:"balance_policy_version"`
	BalancePolicySHA256            string                           `parquet:"balance_policy_sha256"`
	TaskReasoningStepQuotas        map[int]int                      `parquet:"task_reasoning_step_quotas"`
	QuotaTargets                   []QuotaTarget                    `parquet:"quota_targets"`
	ClueQuotas                     []ClueQuota                      `parquet:"clue_quotas"`
	ClueOccurrences                map[int]int                      `parquet:"clue_occurrences"`
	ProgramCensus                  []ProgramCensusEntry             `parquet:"program_census"`
	FamilyProfiles                 map[string]FamilyProfile         `parquet:"family_profiles"`
	FamilyAssignment               map[string]FamilyAssignment      `parquet:"family_assignment"`
	ConstructionAttemptBudgets     []ConstructionAttemptBudget      `parquet:"construction_attempt_budgets"`
	ConstructionAttemptMultiplier  float64                          `parquet:"construction_attempt_multiplier"`
	ExpansionTier                  ExpansionTier                    `parquet:"expansion_tier"`
	ExpansionRounds                int                              `parquet:"expansion_rounds"`
	ExpansionGrowthSharePerRound   float64                          `parquet:"expansion_growth_share_per_round"`
	Subset                         map[int]Subset                   `parquet:"subset"`
}
```

## 03a/03b — DeficitLedger

```go
type DeficitLedger struct { // JSON
	PlanVersion    int             `json:"plan_version"`
	UpdateSequence int64           `json:"update_sequence"`
	Entries        []DeficitEntry  `json:"entries"`
}

type DeficitEntry struct {
	QuotaTarget        QuotaTargetRef     `json:"quota_target"`
	CadevolveProgramFamilyID *string       `json:"cadevolve_program_family_id"`
	AcceptedCount      int                 `json:"accepted_count"`
	RejectedCount      int                 `json:"rejected_count"`
	RemainingCount     int                 `json:"remaining_count"`
	DeficitClass       *DeficitClass       `json:"deficit_class"`
	AllocationDetail   *AllocationDetail   `json:"allocation_detail"`
	RejectionCounts    map[string]int      `json:"rejection_counts"`
	AttemptCount       int                 `json:"attempt_count"`
}

type QuotaTargetRef struct {
	TaskReasoningStepCount int            `json:"task_reasoning_step_count"`
	QuotaDimension         QuotaDimension `json:"quota_dimension"`
	DimensionValue         string         `json:"dimension_value"`
}
```

`DeficitClass` is owned by `03c`; `03b` records it directly when it knows it.
`AllocationDetail` is owned by `03a`. A task contributes to several quota
targets, so accepted counts are independent and are never summed across
dimensions.

## 03b — TaskDefinition

```go
type TaskDefinition struct { // Parquet
	TaskID                     string                    `parquet:"task_id"`
	DefinitionSHA256           string                    `parquet:"definition_sha256"`
	AnswerSHA256               string                    `parquet:"answer_sha256"`
	ProgramID                  string                    `parquet:"program_id"`
	ProgramSHA256              string                    `parquet:"program_sha256"`
	CadevolveProgramFamilyID   string                    `parquet:"cadevolve_program_family_id"`
	Split                      Split                     `parquet:"split"`
	Subset                     Subset                    `parquet:"subset"`
	GraphSchemaVersion         string                    `parquet:"graph_schema_version"`
	DefinitionSchemaVersion    string                    `parquet:"definition_schema_version"`
	StateScope                 StateScope                `parquet:"state_scope"`
	PossibleAnswerCount        int                       `parquet:"possible_answer_count"`
	TargetCategory             TargetCategory            `parquet:"target_category"`
	TargetBinding              TargetBinding             `parquet:"target_binding"`
	TaskClues                  []TaskClue                `parquet:"task_clues"`
	ClueReductionFormProfile     []ClueReductionFormEntry    `parquet:"clue_reduction_form_profile"`
	AnswerMeaning              AnswerMeaning             `parquet:"answer_meaning"`
	TaskAnswerStep             int                       `parquet:"task_answer_step"`
	AnswerParameter            *AnswerParameter          `parquet:"answer_parameter"`
	NativeAnswerFormat         AnswerFormat              `parquet:"native_answer_format"`
	AnswerFormat               AnswerFormat              `parquet:"answer_format"`
	GoldAnswer                 AnswerValue               `parquet:"gold_answer"`
	AnswerUnit                 *string                   `parquet:"answer_unit"`
	Tolerance                  *AnswerTolerance          `parquet:"tolerance"`
	ScoringRule                ScoringRule               `parquet:"scoring_rule"`
	AnswerSchemaVersion        string                    `parquet:"answer_schema_version"`
	AnswerEvidence             AnswerEvidence            `parquet:"answer_evidence"`
	ChoicePool                 []ChoicePoolEntry         `parquet:"choice_pool"`
	TaskClueStepCount          int                       `parquet:"task_clue_step_count"`
	TaskReasoningStepCount     int                       `parquet:"task_reasoning_step_count"`
	GeometryRequired           bool                      `parquet:"geometry_required"`
	ValidityRecord             ValidityRecord            `parquet:"validity_record"`
	Provenance                 Provenance                `parquet:"provenance"`
}

type TargetBinding struct { // exactly one group is non-null, matching Kind
	Kind            string     `parquet:"kind"` // "entity" | "measurement"
	NodeID          *uuid.UUID `parquet:"node_id"`
	MeasurementName *string    `parquet:"measurement_name"`
}

type TaskClue struct {
	ClueID  string       `parquet:"clue_id"`
	Order   int          `parquet:"order"`
	ClueType ClueType    `parquet:"clue_type"`
	Subject BindingRef   `parquet:"subject"`
	Check   ClueCheck    `parquet:"check"`
	Result  ClueResult   `parquet:"result"`
}

type BindingRef struct { // exactly one group is non-null, matching Kind
	Kind              string          `parquet:"kind"` // "target" | "earlier_clue" | "filtered" | "literal"
	ClueReductionForm *string         `parquet:"clue_reduction_form"` // filtered | selected_in_earlier_clue | aggregated | cross_state
	ClueID            *string         `parquet:"clue_id"`             // earlier_clue: the clue whose set this reads
	Category          *string         `parquet:"category"`            // filtered: the graph entity category the class is drawn from
	FaceSurfaceKind   *string         `parquet:"face_surface_kind"`   // filtered: a FaceSurfaceKind value
	Position          *string         `parquet:"position"`            // filtered: a frame extreme, min_x … max_z
	Provenance        *string         `parquet:"provenance_operation_id"` // filtered: the operation that created the entity
	Axis              *string         `parquet:"axis"`                // filtered: the program axis a direction condition names
	Predicate         *PropertyCheck  `parquet:"predicate"`           // filtered: the measured-value condition, when the phrase states one
	Aggregation       *AggregationCheck `parquet:"aggregation"`       // aggregated: the extreme or rank that reduces the set
	StateScope        *string         `parquet:"state_scope"`         // cross_state: the state pair the set is read in
	MeasurementName   *string         `parquet:"measurement_name"`    // target: the measured property the answer reads
	Literal           *string         `parquet:"literal"`             // literal: a value, not an entity set
}

type ClueCheck struct { // exactly one group is non-null; Property/Categorical and Relation/AngleRelation are the two shapes of their clue type
	Property      *PropertyCheck      `parquet:"property"`
	Categorical   *CategoricalCheck   `parquet:"categorical"`
	Relation      *RelationCheck      `parquet:"relation"`
	AngleRelation *AngleRelationCheck `parquet:"angle_relation"`
	Comparison    *ComparisonCheck    `parquet:"comparison"`
	Aggregation   *AggregationCheck   `parquet:"aggregation"`
	Provenance    *ProvenanceCheck    `parquet:"provenance"`
}

type PropertyCheck struct {
	Measurement string     `parquet:"measurement"`
	Comparator  string     `parquet:"comparator"`
	Threshold   *string    `parquet:"threshold"`
	Range       *ValueRange `parquet:"range"`
}

type CategoricalCheck struct {
	Feature string `parquet:"feature"` // "face_surface_kind" | "position"
	Value   string `parquet:"value"`
}

type ValueRange struct {
	Minimum string `parquet:"minimum"`
	Maximum string `parquet:"maximum"`
}

type RelationCheck struct {
	RelationType string      `parquet:"relation_type"`
	Direction    string      `parquet:"direction"` // "object_to_subject" | "subject_to_object"
	Object       BindingRef  `parquet:"object"`
}

type AngleRelationCheck struct {
	Measurement string     `parquet:"measurement"` // "angle"
	Comparator  string     `parquet:"comparator"`
	Threshold   string     `parquet:"threshold"`
	Object      BindingRef `parquet:"object"`
}

type ComparisonCheck struct {
	Measurement string     `parquet:"measurement"`
	Comparator  string     `parquet:"comparator"`
	Reference   BindingRef `parquet:"reference"`
}

type AggregationCheck struct {
	Scope           string     `parquet:"scope"`
	AggregationKind string     `parquet:"aggregation_kind"`
	Measurement     string     `parquet:"measurement"`
	Rank            *int       `parquet:"rank"`
	Extreme         *string    `parquet:"extreme"`
}

type ProvenanceCheck struct { // exactly one group is non-null
	OperationID *string `parquet:"operation_id"`
	ProfileID   *string `parquet:"profile_id"`
}

type ClueResult struct {
	BeforeCount     int                `parquet:"before_count"`
	AfterCount      int                `parquet:"after_count"`
	BoundEntities   []uuid.UUID        `parquet:"bound_entities"`
	ClueReductionForm *ClueReductionForm   `parquet:"clue_reduction_form"`
	EvidenceRefs    []EvidenceRef      `parquet:"evidence_refs"`
}

type ClueReductionFormEntry struct {
	ClueType        ClueType         `parquet:"clue_type"`
	ClueReductionForm *ClueReductionForm `parquet:"clue_reduction_form"`
}
```

```go
type AnswerValue struct { // exactly one group is non-null, matching Kind
	Kind         string      `parquet:"kind"` // label | number | integer | boolean | point | bounding_box | structured
	Label        *string     `parquet:"label"`
	NumberText   *string     `parquet:"number_text"`
	Integer      *int64      `parquet:"integer"`
	Boolean      *bool       `parquet:"boolean"`
	Point        *Point3D    `parquet:"point"`
	BoundingBox  *BoundingBox `parquet:"bounding_box"`
	Structured   *string     `parquet:"structured"`
}

type AnswerTolerance struct { // answer scoring, not a measurement tolerance
	Kind      ToleranceKind `parquet:"kind"`
	ValueText *string       `parquet:"value_text"`
	Unit      *string       `parquet:"unit"`
}

type AnswerParameter struct { // exactly one group is non-null, matching Kind
	Kind     string     `parquet:"kind"` // "point" | "category"
	Point    *Point3D   `parquet:"point"`
	Category *string    `parquet:"category"`
}

type AnswerEvidence struct {
	EvidenceKind           EvidenceKind            `parquet:"evidence_kind"`
	EvidenceRule           string                  `parquet:"evidence_rule"`
	EvidenceRefs           []EvidenceRef           `parquet:"evidence_refs"`
	AnswerEquivalentSet    []AnswerEquivalentEntry `parquet:"answer_equivalent_set"`
	PointProbe             *AnswerPointProbe       `parquet:"point_probe"`
}

type AnswerEquivalentEntry struct {
	Subject string      `parquet:"subject"`
	Answer  AnswerValue `parquet:"answer"`
}

type AnswerPointProbe struct {
	Point            Point3D `parquet:"point"`
	Location         string  `parquet:"location"` // "inside" | "outside"
	DistanceToFaceSurface string `parquet:"distance_to_face_surface"`
	Classifier       string  `parquet:"classifier"`
	Margin           string  `parquet:"margin"`
}

type ChoicePoolEntry struct {
	Label               string      `parquet:"label"` // A..G
	Candidate           AnswerValue `parquet:"candidate"`
	DistinguishingFacts []string    `parquet:"distinguishing_facts"`
	ErrorMode           *string     `parquet:"error_mode"`
}

type ValidityRecord struct {
	Checks                 []ValidityCheck `parquet:"checks"`
	AnswerEquivalentSize   int             `parquet:"answer_equivalent_size"`
	SameAnswerHolds        bool            `parquet:"same_answer_holds"`
}

type ValidityCheck struct {
	Name    string `parquet:"name"`
	Outcome string `parquet:"outcome"` // "pass" | "fail"
	Detail  string `parquet:"detail"`
}

type Provenance struct {
	RuntimeExtractionSHA256 string `parquet:"runtime_extraction_sha256"`
	GraphIdentitySHA256     string `parquet:"graph_identity_sha256"`
	ConstructorVersion      string `parquet:"constructor_version"`
	ConstructionSeed        int64  `parquet:"construction_seed"`
	PlanVersion             int    `parquet:"plan_version"`
	BalancePolicyVersion    int    `parquet:"balance_policy_version"`
}
```

The validity check names are the closed set in
[`../../../03-task-generation/03b-construct-task-definitions/a-construction.md`](../../03-task-generation/03b-construct-task-definitions/a-construction.md#validity):
`clue_satisfied`, `clue_narrows`, `clue_necessary`, `predicate_margin`,
`answer_equivalence`, `scalar_target_agrees`, `single_gold_answer`,
`target_binding_unambiguous`, `family_and_split_present`, `split_matches_assignment`,
`subset_matches_step_count`, `answer_evidence_present`, `choice_pool_valid`,
`geometry_required_recorded`, `definition_unique`, and the P2 `near_miss_valid`.

## 03c — control records

```go
type ProgramReassignmentRequest struct { // JSON control record
	QuotaTarget             QuotaTargetRef `json:"quota_target"`
	CurrentFamilyAssignment FamilyAssignment `json:"current_family_assignment"`
	CurrentFamilyQuota      int            `json:"current_family_quota"`
	AcceptedCounts          map[string]int `json:"accepted_counts"`
	RemainingCounts         map[string]int `json:"remaining_counts"`
	UnassignedFamilies      []string       `json:"unassigned_families"`
	UnusedCapacity          map[string]int `json:"unused_capacity"`
	RequestedChange         string         `json:"requested_change"`
	RetryBudget             int            `json:"retry_budget"`
	PlanVersion             int            `json:"plan_version"`
}

type ProgramRequest struct { // JSON control record
	QuotaTarget            QuotaTargetRef   `json:"quota_target"`
	MissingCapability      ClueConstructor  `json:"missing_capability"`
	AcceptedCounts         map[string]int   `json:"accepted_counts"`
	RemainingCounts        map[string]int   `json:"remaining_counts"`
	FeatureTags            []FeatureTag     `json:"feature_tags"`
	Collections            []string         `json:"collections"`
	FamilyConstraints      []string         `json:"family_constraints"`
	Mode                   ProgramRequestMode `json:"mode"`
	RequestedProgramCount  int              `json:"requested_program_count"`
	MaxGraphBuildBudget    int              `json:"max_graph_build_budget"`
	Reason                 string           `json:"reason"`
	PlanVersion            int              `json:"plan_version"`
}

type AcceptedMiss struct { // JSON control record
	QuotaTarget    QuotaTargetRef `json:"quota_target"`
	RemainingCount int            `json:"remaining_count"`
	Reason         string         `json:"reason"`
	Owner          string         `json:"owner"`
	PlanVersion    int            `json:"plan_version"`
}
```

`ProgramRequest` is answered by `01b` with a `ProgramSelectionDelta`; the
request itself is not a selection artifact.
