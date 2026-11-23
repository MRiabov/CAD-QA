export type Color = [number, number, number];
export type Point3 = [number, number, number];

export interface Facets {
  task_count: number;
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
  prompt_preview: string;
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

export interface TaskDetail {
  task_id: string;
  split: string;
  subset: string;
  target_category: string;
  answer_format: string;
  answer_meaning: string;
  answer: string;
  prompt: string;
  program: string;
  choices: Choice[];
  diagnostics: Diagnostic[];
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
