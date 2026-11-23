import type { Facets, ScenePayload, TaskDetail, TaskPage } from "./types";

export interface TaskQuery {
  offset: number;
  limit: number;
  search: string;
  split: string;
  subset: string;
  targetCategory: string;
  answerMeaning: string;
  order: "file" | "random";
  seed: string;
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export function fetchFacets(): Promise<Facets> {
  return getJson<Facets>("/api/facets");
}

export function fetchTasks(query: TaskQuery): Promise<TaskPage> {
  const params = new URLSearchParams();
  params.set("offset", String(query.offset));
  params.set("limit", String(query.limit));
  if (query.search) params.set("search", query.search);
  if (query.split) params.set("split", query.split);
  if (query.subset) params.set("subset", query.subset);
  if (query.targetCategory) params.set("target_category", query.targetCategory);
  if (query.answerMeaning) params.set("answer_meaning", query.answerMeaning);
  params.set("order", query.order);
  if (query.order === "random") params.set("seed", query.seed);
  return getJson<TaskPage>(`/api/tasks?${params.toString()}`);
}

export function fetchTask(taskId: string): Promise<TaskDetail> {
  return getJson<TaskDetail>(`/api/tasks/${encodeURIComponent(taskId)}`);
}

export function fetchScene(taskId: string): Promise<ScenePayload> {
  return getJson<ScenePayload>(`/api/tasks/${encodeURIComponent(taskId)}/scene`);
}
