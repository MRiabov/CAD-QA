# 02c build CAD graph — typed models

> Owning pipeline stage: `02c` (Go).
> Contract: [`../../02c-build-cad-graph.md`](../../02c-build-cad-graph.md).
> Schemas: [`../../extraction/graph-persistence.md`](../../extraction/graph-persistence.md),
> [`../../extraction/graph-construction.md`](../../extraction/graph-construction.md).

The Go geometry types below mirror the Python `Point3D`, `Vector3D`,
`BoundingBox`, and `BoundingBoxChange` shapes in
[`02-execute-cadquery-and-build-graph.md`](02-execute-cadquery-and-build-graph.md).
The Go `Tolerance` is the measurement tolerance; the answer-scoring
`AnswerTolerance` is declared in [`03-task-generation.md`](03-task-generation.md).

## 02c — CadGraph (Go, Parquet)

```go
type GraphNodeType string

const (
	NodeCadQueryProgram       GraphNodeType = "cadquery_program"
	NodeOperation             GraphNodeType = "operation"
	NodeFeature               GraphNodeType = "feature"
	NodeSolidState            GraphNodeType = "solid_state"
	NodePointProbe            GraphNodeType = "point_probe"
	NodeFace                  GraphNodeType = "face"
	NodeEdge                  GraphNodeType = "edge"
	NodeVertex                GraphNodeType = "vertex"
	NodeEdgeEndpoint          GraphNodeType = "edge_endpoint"
	NodeCadQueryProfile       GraphNodeType = "cadquery_profile"
	NodeCadQueryWorkplane     GraphNodeType = "cadquery_workplane"
	NodeCadQueryPath          GraphNodeType = "cadquery_path"
	NodeCadQueryPathPoint     GraphNodeType = "cadquery_path_point"
	NodeCadQueryPathSegment   GraphNodeType = "cadquery_path_segment"
	NodeRegion                GraphNodeType = "region"
	NodeCadQuerySelectorResult GraphNodeType = "cadquery_selector_result"
)

type RelationType string

const (
	RelBefore            RelationType = "before"
	RelAfter             RelationType = "after"
	RelCreates           RelationType = "creates"
	RelUses              RelationType = "uses"
	RelDerivedFrom       RelationType = "derived_from"
	RelHasFace           RelationType = "has_face"
	RelHasEdge           RelationType = "has_edge"
	RelHasVertex         RelationType = "has_vertex"
	RelAdjacentTo        RelationType = "adjacent_to"
	RelHasPointProbe     RelationType = "has_point_probe"
	RelEndpointOf        RelationType = "endpoint_of"
	RelSameAs            RelationType = "same_as" // P2
	RelSelectedFrom      RelationType = "selected_from"
	RelSelectedBy        RelationType = "selected_by"
	RelAddsMaterial      RelationType = "adds_material"
	RelRemovesMaterial   RelationType = "removes_material"
	RelPartOf            RelationType = "part_of"
	RelParallelTo        RelationType = "parallel_to"
	RelPerpendicularTo   RelationType = "perpendicular_to"
	RelCoplanarWith      RelationType = "coplanar_with"
	RelCoaxialWith       RelationType = "coaxial_with"
)

type MeasurementType string

const (
	MeasureVolume           MeasurementType = "volume"
	MeasureArea             MeasurementType = "area"
	MeasureLength           MeasurementType = "length"
	MeasureDistance         MeasurementType = "distance"
	MeasureAngle            MeasurementType = "angle"
	MeasureBoundingBox      MeasurementType = "bounding_box"
	MeasureCentroid         MeasurementType = "centroid"
	MeasureProbePoint       MeasurementType = "probe_point"
	MeasureDistanceToSurface MeasurementType = "distance_to_surface"
	MeasureFaceCount        MeasurementType = "face_count"
	MeasureEdgeCount        MeasurementType = "edge_count"
	MeasureVertexCount      MeasurementType = "vertex_count"
	MeasureSelectedCount    MeasurementType = "selected_count"
	MeasureValidity         MeasurementType = "validity"
	MeasureVolumeChange     MeasurementType = "volume_change"
	MeasureBoundingBoxChange MeasurementType = "bounding_box_change"
	MeasureTopologyChange   MeasurementType = "topology_change"
	MeasureWorkplaneFrame   MeasurementType = "workplane_frame"
)

type MeasurementUnit string

const (
	UnitMillimetre       MeasurementUnit = "millimetre"
	UnitSquareMillimetre MeasurementUnit = "square_millimetre"
	UnitCubicMillimetre  MeasurementUnit = "cubic_millimetre"
	UnitDegree           MeasurementUnit = "degree"
	UnitRadian           MeasurementUnit = "radian"
	UnitUnitless         MeasurementUnit = "unitless"
)

type EvidenceKind string

const (
	EvidenceDerived  EvidenceKind = "derived"
	EvidenceMeasured EvidenceKind = "measured"
)

type ToleranceKind string

const (
	ToleranceExact    ToleranceKind = "exact"
	ToleranceAbsolute ToleranceKind = "absolute"
	ToleranceRelative ToleranceKind = "relative"
)

type ProbeClassifier string

const (
	ProbeClassifierIsInside ProbeClassifier = "is_inside"
)

type MeasurementValueKind string

const (
	MeasurementValueScalar            MeasurementValueKind = "scalar"
	MeasurementValueInteger           MeasurementValueKind = "integer"
	MeasurementValueBoolean           MeasurementValueKind = "boolean"
	MeasurementValuePoint             MeasurementValueKind = "point"
	MeasurementValueBoundingBox       MeasurementValueKind = "bounding_box"
	MeasurementValueBoundingBoxChange MeasurementValueKind = "bounding_box_change"
	MeasurementValueTopologyDelta     MeasurementValueKind = "topology_delta"
	MeasurementValueWorkplaneFrame    MeasurementValueKind = "workplane_frame"
)

type EvidenceRefKind string

const (
	EvidenceRefNode            EvidenceRefKind = "node"
	EvidenceRefMeasurement     EvidenceRefKind = "measurement"
	EvidenceRefOperation       EvidenceRefKind = "operation"
	EvidenceRefSourceLine      EvidenceRefKind = "source_line"
	EvidenceRefRuntimeArtifact EvidenceRefKind = "runtime_artifact"
)

type FaceSurfaceKind string

const (
	SurfacePlane    FaceSurfaceKind = "plane"
	SurfaceCylinder FaceSurfaceKind = "cylinder"
	SurfaceCone     FaceSurfaceKind = "cone"
	SurfaceSphere   FaceSurfaceKind = "sphere"
	SurfaceTorus    FaceSurfaceKind = "torus"
	SurfaceBSpline  FaceSurfaceKind = "bspline"
	SurfaceOther    FaceSurfaceKind = "other"
)

type EdgeCurveKind string

const (
	CurveLine      EdgeCurveKind = "line"
	CurveCircle    EdgeCurveKind = "circle"
	CurveEllipse   EdgeCurveKind = "ellipse"
	CurveHyperbola EdgeCurveKind = "hyperbola"
	CurveParabola  EdgeCurveKind = "parabola"
	CurveBSpline   EdgeCurveKind = "bspline"
	CurveOther     EdgeCurveKind = "other"
)

type EdgeEnd string

const (
	EdgeEndStart EdgeEnd = "start"
	EdgeEndEnd   EdgeEnd = "end"
)

type ProfileKind string

const (
	ProfileRectangle ProfileKind = "rectangle"
	ProfileCircle    ProfileKind = "circle"
	ProfileEllipse   ProfileKind = "ellipse"
	ProfilePolygon   ProfileKind = "polygon"
	ProfileSlot      ProfileKind = "slot"
	ProfileOther     ProfileKind = "other"
)

type WorkplaneKind string

const (
	WorkplaneNamed  WorkplaneKind = "named"
	WorkplaneCustom WorkplaneKind = "custom"
	WorkplaneFace   WorkplaneKind = "face"
)

type NamedPlane string

const (
	NamedPlaneXY NamedPlane = "xy"
	NamedPlaneYZ NamedPlane = "yz"
	NamedPlaneXZ NamedPlane = "xz"
)

type PathKind string

const (
	PathLine     PathKind = "line"
	PathPolyline PathKind = "polyline"
	PathSpline   PathKind = "spline"
	PathArc      PathKind = "arc"
	PathHelix    PathKind = "helix"
	PathOther    PathKind = "other"
)

type PathSegmentKind string

const (
	SegmentLine   PathSegmentKind = "line"
	SegmentArc    PathSegmentKind = "arc"
	SegmentSpline PathSegmentKind = "spline"
	SegmentOther  PathSegmentKind = "other"
)

type RegionSign string

const (
	RegionAdded   RegionSign = "added"
	RegionRemoved RegionSign = "removed"
)

type SelectorKind string

const (
	SelectorString   SelectorKind = "string"
	SelectorCall     SelectorKind = "call"
	SelectorFilter   SelectorKind = "filter"
	SelectorImplicit SelectorKind = "implicit"
)
```

```go
type GraphNode struct { // Parquet: nodes.parquet
	ProgramID          string         `parquet:"program_id"`
	GraphSchemaVersion string         `parquet:"graph_schema_version"`
	NodeID             uuid.UUID      `parquet:"node_id"`
	NodeType           GraphNodeType  `parquet:"node_type"`
	LocalID            string         `parquet:"local_id"`
	StateID            *string        `parquet:"state_id"`
	OperationID        *string        `parquet:"operation_id"`
	Label              string         `parquet:"label"`
	Attributes         NodeAttributes `parquet:"attributes"`
}

type NodeAttributes struct { // exactly one group is non-null, matching NodeType
	CadQueryProgram        *CadQueryProgramAttributes        `parquet:"cadquery_program"`
	Operation              *OperationAttributes              `parquet:"operation"`
	Feature                *FeatureAttributes                `parquet:"feature"`
	SolidState             *SolidStateAttributes             `parquet:"solid_state"`
	PointProbe             *PointProbeAttributes             `parquet:"point_probe"`
	Face                   *FaceAttributes                   `parquet:"face"`
	Edge                   *EdgeAttributes                   `parquet:"edge"`
	Vertex                 *VertexAttributes                 `parquet:"vertex"`
	EdgeEndpoint           *EdgeEndpointAttributes           `parquet:"edge_endpoint"`
	CadQueryProfile        *CadQueryProfileAttributes        `parquet:"cadquery_profile"`
	CadQueryWorkplane      *CadQueryWorkplaneAttributes      `parquet:"cadquery_workplane"`
	CadQueryPath           *CadQueryPathAttributes           `parquet:"cadquery_path"`
	CadQueryPathPoint      *CadQueryPathPointAttributes      `parquet:"cadquery_path_point"`
	CadQueryPathSegment    *CadQueryPathSegmentAttributes    `parquet:"cadquery_path_segment"`
	Region                 *RegionAttributes                 `parquet:"region"`
	CadQuerySelectorResult *CadQuerySelectorResultAttributes `parquet:"cadquery_selector_result"`
}

type CadQueryProgramAttributes struct {
	ProgramSHA256               string `parquet:"program_sha256"`
	NormalizationVersion        string `parquet:"normalization_version"`
	ExtractorVersion            string `parquet:"extractor_version"`
	RuntimeExtractionResultSHA256 string `parquet:"runtime_extraction_result_sha256"`
	GraphIdentitySHA256         string `parquet:"graph_identity_sha256"`
}

type OperationAttributes struct {
	OperationKind string  `parquet:"operation_kind"`
	Method        string  `parquet:"method"`
	Order         int     `parquet:"order"`
	SourceLine    int     `parquet:"source_line"`
	ResultVar     *string `parquet:"result_var"`
}

type FeatureAttributes struct {
	FeatureKind string `parquet:"feature_kind"`
}

type SolidStateAttributes struct {
	SequenceIndex int     `parquet:"sequence_index"`
	IsFinal       bool    `parquet:"is_final"`
	IsSolid       bool    `parquet:"is_solid"`
	ShapeHash     *string `parquet:"shape_hash"`
}

type PointProbeAttributes struct {
	ProbeIndex  int             `parquet:"probe_index"`
	IsInside    bool            `parquet:"is_inside"`
	Classifier  ProbeClassifier `parquet:"classifier"`
}

type FaceAttributes struct {
	FingerprintSHA256 string `parquet:"fingerprint_sha256"`
	FaceSurfaceKind   FaceSurfaceKind `parquet:"face_surface_kind"`
}

type EdgeAttributes struct {
	FingerprintSHA256 string `parquet:"fingerprint_sha256"`
	EdgeCurveKind     EdgeCurveKind `parquet:"edge_curve_kind"`
	IsClosed          bool   `parquet:"is_closed"`
}

type VertexAttributes struct {
	FingerprintSHA256 string `parquet:"fingerprint_sha256"`
}

type EdgeEndpointAttributes struct {
	End EdgeEnd `parquet:"end"`
}

type CadQueryProfileAttributes struct {
	ProfileKind ProfileKind `parquet:"profile_kind"`
	IsClosed    bool   `parquet:"is_closed"`
}

type CadQueryWorkplaneAttributes struct {
	WorkplaneKind WorkplaneKind `parquet:"workplane_kind"`
	NamedPlane    *NamedPlane   `parquet:"named_plane"`
}

type CadQueryPathAttributes struct {
	PathKind PathKind `parquet:"path_kind"`
	IsClosed bool   `parquet:"is_closed"`
}

type CadQueryPathPointAttributes struct {
	Index int `parquet:"index"`
}

type CadQueryPathSegmentAttributes struct {
	Index       int    `parquet:"index"`
	SegmentKind PathSegmentKind `parquet:"segment_kind"`
}

type RegionAttributes struct {
	RegionSign RegionSign `parquet:"region_sign"`
}

type CadQuerySelectorResultAttributes struct {
	SelectorID         string `parquet:"selector_id"`
	SelectorExpression string `parquet:"selector_expression"`
	SelectorKind       SelectorKind `parquet:"selector_kind"`
	SourceLine         int    `parquet:"source_line"`
}
```

```go
type GraphRelation struct { // Parquet: relations.parquet
	ProgramID          string       `parquet:"program_id"`
	GraphSchemaVersion string       `parquet:"graph_schema_version"`
	RelationID         uuid.UUID    `parquet:"relation_id"`
	RelationType       RelationType `parquet:"relation_type"`
	FromNodeID         uuid.UUID    `parquet:"from_node_id"`
	ToNodeID           uuid.UUID    `parquet:"to_node_id"`
	Tolerance          *Tolerance   `parquet:"tolerance"`
	EvidenceKind       EvidenceKind `parquet:"evidence_kind"`
	EvidenceRule       string       `parquet:"evidence_rule"`
	EvidenceRefs       []EvidenceRef `parquet:"evidence_refs"`
}

type GraphMeasurement struct { // Parquet: measurements.parquet
	ProgramID          string          `parquet:"program_id"`
	GraphSchemaVersion string          `parquet:"graph_schema_version"`
	MeasurementID      uuid.UUID       `parquet:"measurement_id"`
	SubjectNodeID      uuid.UUID       `parquet:"subject_node_id"`
	ObjectNodeID       *uuid.UUID      `parquet:"object_node_id"`
	MeasurementType    MeasurementType `parquet:"measurement_type"`
	Value              MeasurementValue `parquet:"value"`
	Unit               MeasurementUnit `parquet:"unit"`
	EvidenceKind       EvidenceKind    `parquet:"evidence_kind"`
	EvidenceRule       string          `parquet:"evidence_rule"`
	EvidenceRefs       []EvidenceRef   `parquet:"evidence_refs"`
	Tolerance          *Tolerance      `parquet:"tolerance"`
}

type MeasurementValue struct { // exactly one group is non-null, matching Kind
	Kind             MeasurementValueKind `parquet:"kind"`
	Scalar           *float64         `parquet:"scalar"`
	Integer          *int64           `parquet:"integer"`
	Boolean          *bool            `parquet:"boolean"`
	Point            *Point3D         `parquet:"point"`
	BoundingBox      *BoundingBox     `parquet:"bounding_box"`
	BoundingBoxChange *BoundingBoxChange `parquet:"bounding_box_change"`
	TopologyDelta    *TopologyDelta   `parquet:"topology_delta"`
	WorkplaneFrame   *WorkplaneFrame  `parquet:"workplane_frame"`
}

type Point3D struct {
	X float64 `parquet:"x"`
	Y float64 `parquet:"y"`
	Z float64 `parquet:"z"`
}

type Vector3D struct {
	X float64 `parquet:"x"`
	Y float64 `parquet:"y"`
	Z float64 `parquet:"z"`
}

type BoundingBox struct {
	Min Point3D `parquet:"min"`
	Max Point3D `parquet:"max"`
}

type BoundingBoxChange struct {
	Before BoundingBox `parquet:"before"`
	After  BoundingBox `parquet:"after"`
}

type TopologyDelta struct {
	FaceDelta   int64 `parquet:"face_delta"`
	EdgeDelta   int64 `parquet:"edge_delta"`
	VertexDelta int64 `parquet:"vertex_delta"`
}

type WorkplaneFrame struct {
	Origin     Point3D  `parquet:"origin"`
	XDirection Vector3D `parquet:"x_direction"`
	Normal     Vector3D `parquet:"normal"`
}

type Tolerance struct {
	Kind  ToleranceKind   `parquet:"kind"`
	Value *float64        `parquet:"value"`
	Unit  *MeasurementUnit `parquet:"unit"`
}

type EvidenceRef struct { // exactly one group is non-null, matching Kind
	Kind           EvidenceRefKind           `parquet:"kind"`
	Node           *NodeEvidenceRef          `parquet:"node"`
	Measurement    *MeasurementEvidenceRef   `parquet:"measurement"`
	Operation      *OperationEvidenceRef     `parquet:"operation"`
	SourceLine     *SourceLineEvidenceRef    `parquet:"source_line"`
	RuntimeArtifact *RuntimeArtifactEvidenceRef `parquet:"runtime_artifact"`
}

type NodeEvidenceRef struct {
	NodeID uuid.UUID `parquet:"node_id"`
}

type MeasurementEvidenceRef struct {
	MeasurementID uuid.UUID `parquet:"measurement_id"`
}

type OperationEvidenceRef struct {
	OperationID string `parquet:"operation_id"`
}

type SourceLineEvidenceRef struct {
	SourceLine int64 `parquet:"source_line"`
}

type RuntimeArtifactEvidenceRef struct {
	ArtifactURI   string  `parquet:"artifact_uri"`
	ArtifactField *string `parquet:"artifact_field"`
}

type CadGraph struct { // logical aggregate of the three Parquet tables
	ProgramID          string             `parquet:"program_id"`
	GraphSchemaVersion string             `parquet:"graph_schema_version"`
	Nodes              []GraphNode        `parquet:"nodes"`
	Relations          []GraphRelation    `parquet:"relations"`
	Measurements       []GraphMeasurement `parquet:"measurements"`
}

type CompletenessDisposition string

const (
	CompletenessComplete      CompletenessDisposition = "complete"
	CompletenessExtractorGap  CompletenessDisposition = "extractor_gap"
	CompletenessCorpusDefect  CompletenessDisposition = "corpus_defect"
	CompletenessContractGap   CompletenessDisposition = "contract_gap"
	CompletenessUnclassified  CompletenessDisposition = "unclassified"
)

type ExpectedSource string

const (
	ExpectedContractRule  ExpectedSource = "contract_rule"
	ExpectedUpstreamRecord ExpectedSource = "upstream_record"
	ExpectedEmissionRule  ExpectedSource = "emission_rule"
	ExpectedKernelOracle  ExpectedSource = "kernel_oracle"
	ExpectedGraphArtifact ExpectedSource = "graph_artifact"
)

type EndpointPairEvidence struct {
	SubjectNodeID uuid.UUID     `parquet:"subject_node_id"`
	ObjectNodeID  *uuid.UUID    `parquet:"object_node_id"`
	EvidenceRefs  []EvidenceRef `parquet:"evidence_refs"`
}

type RelationCompleteness struct {
	RelationKind        RelationType          `parquet:"relation_kind"`
	SubjectKind         GraphNodeType         `parquet:"subject_kind"`
	ObjectKind          GraphNodeType         `parquet:"object_kind"`
	ExpectedCount       int                   `parquet:"expected_count"`
	ActualCount         int                   `parquet:"actual_count"`
	MissingCount        int                   `parquet:"missing_count"`
	OrphanCount         int                   `parquet:"orphan_count"`
	UnclassifiedCount   int                   `parquet:"unclassified_count"`
	ExpectedSource      ExpectedSource        `parquet:"expected_source"`
	ActualSource        ExpectedSource        `parquet:"actual_source"`
	MissingPairs        []EndpointPairEvidence `parquet:"missing_pairs"`
	OrphanPairs         []EndpointPairEvidence `parquet:"orphan_pairs"`
}

type NodeCompleteness struct {
	NodeKind            GraphNodeType  `parquet:"node_kind"`
	ExpectedCount       int            `parquet:"expected_count"`
	ActualCount         int            `parquet:"actual_count"`
	MissingCount        int            `parquet:"missing_count"`
	OrphanCount         int            `parquet:"orphan_count"`
	UnclassifiedCount   int            `parquet:"unclassified_count"`
	ExpectedSource      ExpectedSource `parquet:"expected_source"`
	ActualSource        ExpectedSource `parquet:"actual_source"`
}

type MeasurementCompleteness struct {
	SubjectKind         GraphNodeType     `parquet:"subject_kind"`
	MeasurementKind     MeasurementType   `parquet:"measurement_kind"`
	ExpectedCount       int               `parquet:"expected_count"`
	ActualCount         int               `parquet:"actual_count"`
	MissingCount        int               `parquet:"missing_count"`
	OrphanCount         int               `parquet:"orphan_count"`
	UnclassifiedCount   int               `parquet:"unclassified_count"`
	ExpectedSource      ExpectedSource    `parquet:"expected_source"`
	ActualSource        ExpectedSource    `parquet:"actual_source"`
}

type GraphCompletenessReport struct { // written by 02c next to the graph
	ProgramID                string                  `parquet:"program_id"`
	GraphArtifactSHA256      string                  `parquet:"graph_artifact_sha256"`
	ExtractorVersion         string                  `parquet:"extractor_version"`
	CanonicalizationVersion  string                  `parquet:"canonicalization_version"`
	TolerancePolicyVersion   int                     `parquet:"tolerance_policy_version"`
	TolerancePolicySHA256    string                  `parquet:"tolerance_policy_sha256"`
	Rows                     []RelationCompleteness  `parquet:"rows"`
	NodeRows                 []NodeCompleteness      `parquet:"node_rows"`
	MeasurementRows          []MeasurementCompleteness `parquet:"measurement_rows"`
	Disposition              CompletenessDisposition `parquet:"disposition"`
}
```

Graph-local IDs are deterministic UUIDv5 values. `Tolerance` on a relation is
null unless the relation is one of `parallel_to`, `perpendicular_to`,
`coplanar_with`, or `coaxial_with`.
