import { useEffect, useState } from "react";
import { fetchFacets, fetchScene, fetchTask, fetchTasks } from "./api";
import type { TaskQuery } from "./api";
import { SceneView } from "./SceneView";
import { TaskDetail } from "./TaskDetail";
import { TaskList } from "./TaskList";
import type { Facets, ScenePayload, TaskDetail as TaskDetailType, TaskPage } from "./types";

const INITIAL_QUERY: TaskQuery = {
  offset: 0,
  limit: 50,
  search: "",
  split: "",
  subset: "",
  targetCategory: "",
  answerMeaning: "",
  order: "file",
  seed: "0",
};

interface LoadedDetail {
  taskId: string;
  value: TaskDetailType;
}

interface LoadedScene {
  taskId: string;
  value: ScenePayload | null;
  error: string | null;
}

export default function App() {
  const [facets, setFacets] = useState<Facets | null>(null);
  const [query, setQuery] = useState<TaskQuery>(INITIAL_QUERY);
  const [page, setPage] = useState<TaskPage | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loadedDetail, setLoadedDetail] = useState<LoadedDetail | null>(null);
  const [loadedScene, setLoadedScene] = useState<LoadedScene | null>(null);
  const [error, setError] = useState<string | null>(null);

  const detail =
    loadedDetail !== null && loadedDetail.taskId === activeId ? loadedDetail.value : null;
  const scene = loadedScene !== null && loadedScene.taskId === activeId ? loadedScene.value : null;
  const sceneError =
    loadedScene !== null && loadedScene.taskId === activeId ? loadedScene.error : null;

  useEffect(() => {
    fetchFacets()
      .then(setFacets)
      .catch((reason: unknown) => setError(String(reason)));
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchTasks(query)
      .then((next) => {
        if (cancelled) return;
        setPage(next);
        setError(null);
        setActiveId((current) => {
          if (current !== null && next.tasks.some((task) => task.task_id === current)) {
            return current;
          }
          return next.tasks[0]?.task_id ?? null;
        });
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(String(reason));
      });
    return () => {
      cancelled = true;
    };
  }, [query]);

  useEffect(() => {
    if (activeId === null) return;
    let cancelled = false;
    fetchTask(activeId)
      .then((value) => {
        if (!cancelled) setLoadedDetail({ taskId: activeId, value });
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(String(reason));
      });
    fetchScene(activeId)
      .then((value) => {
        if (!cancelled) {
          setLoadedScene({ taskId: activeId, value, error: null });
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setLoadedScene({
            taskId: activeId,
            value: null,
            error: String(reason),
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activeId]);

  return (
    <div className="app">
      <header className="topbar">
        <h1>CAD-QA task browser</h1>
        <span className="topbar-meta">
          {facets === null
            ? "loading…"
            : `${facets.task_count} ${facets.task_count === 1 ? "task" : "tasks"}`}
        </span>
      </header>
      {error === null ? null : <div className="error-banner">{error}</div>}
      <main className="layout">
        <TaskList
          facets={facets}
          page={page}
          query={query}
          activeId={activeId}
          onQueryChange={setQuery}
          onSelect={setActiveId}
        />
        <section className="stage">
          <SceneView scene={scene} />
          {sceneError === null ? null : <p className="scene-error">{sceneError}</p>}
        </section>
        <TaskDetail detail={detail} scene={scene} sceneError={sceneError} />
      </main>
    </div>
  );
}
