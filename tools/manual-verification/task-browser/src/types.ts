export type Color = [number, number, number];
export type Point3 = [number, number, number];

export interface Facets {
  task_count: number;
  input_kind: "release" | "gold";
  splits: string[];
  subsets: string[];
  target_categories: string[];
  answer_meanings: string[];
}

export interface TaskSummary {
  task_id: string;
  split: string;
  subset: string;
  target_category: string;
  answer_meaning: string;
  answer: string;
  task_reasoning_step_count: number;
  program_id: string;
  preview: string;
}

export interface TaskPage {
  total: number;
  offset: number;
  limit: number;
  tasks: TaskSummary[];
}

export interface Diagnostic {
  label: string;
  value: string;
}

export interface Choice {
  label: string;
  candidate: string;
}

export type VerificationStatus = "proposed" | "verified" | "stale";

export interface OracleClue {
  order: number;
  clue_type: string;
  clue_reduction_form: string | null;
  statement: string;
  narrows: { before: number; after: number };
}

export interface OracleRecord {
  slug: string;
  verification: {
    status: VerificationStatus;
    verified_by: string | null;
    verified_at: string | null;
    rationale: string;
    gold_query: {
      status: string;
      stdout: string | null;
      checked_at: string | null;
    };
  };
  environment: {
    cadquery_version: string;
    ocp_version: string;
    python_version: string;
    oracle_tool_version: string;
  };
  program: { program_id: string; program_sha256: string; text: string };
  task: {
    target_category: string;
    question: string;
    state_scope: string;
    possible_answer_count: number;
    task_reasoning_step_count: number;
    answer_meaning: string;
    answer_format: string;
    native_answer_format: string;
    geometry_required: boolean;
    uniqueness: string;
  };
  clues: OracleClue[];
  answer: {
    value_kind: string;
    value: unknown;
    unit: string;
    tolerance: { tolerance_kind: string; value_text: string } | null;
    scoring_rule: string;
    evidence_kind: string;
    evidence_rule: string;
    answer_equivalent_set: { subject: unknown; value: unknown }[];
  };
  gold_query: {
    language: string;
    code: string;
    expected_stdout: string;
    sha256: string;
  };
  covers: {
    target_category: string;
    clue_types: string[];
    clue_reduction_forms: string[];
    answer_meaning: string;
    answer_format: string;
    task_reasoning_step_count: number;
  };
  excluded: { exclusion_kind: string; reason: string }[];
  notes: string[];
}

export interface TaskDetail {
  task_id: string;
  split: string;
  subset: string;
  target_category: string;
  answer_format: string;
  answer_meaning: string;
  answer: string;
  prompt: string | null;
  program: string;
  choices: Choice[];
  diagnostics: Diagnostic[];
  oracle: OracleRecord | null;
}

export type PrimitiveKind = "triangles" | "lines";

export interface MeshPart {
  primitive_kind: PrimitiveKind;
  color: Color;
  positions: number[];
}

export interface LegendEntry {
  key: string;
  label: string;
  detail: string;
  color: Color;
}

export interface ScenePayload {
  scene_version: number;
  parts: MeshPart[];
  legend: LegendEntry[];
  bounds_min: Point3;
  bounds_max: Point3;
  triangle_count: number;
  segment_count: number;
}
