import type { ScenePayload, TaskDetail as TaskDetailType } from "./types";

interface TaskDetailProps {
  detail: TaskDetailType | null;
  scene: ScenePayload | null;
  sceneError: string | null;
}

export function TaskDetail({ detail, scene, sceneError }: TaskDetailProps) {
  if (detail === null) {
    return (
      <aside className="detail-pane">
        <p className="empty">Select a task.</p>
      </aside>
    );
  }

  const counts =
    scene === null
      ? (sceneError ?? "loading scene…")
      : `${scene.triangle_count} triangles · ${scene.segment_count} line segments`;

  return (
    <aside className="detail-pane">
      <section className="answer-block">
        <h2>Answer</h2>
        <p className="answer">{detail.answer}</p>
      </section>

      <details className="panel">
        <summary>Prompt</summary>
        <pre>{detail.prompt}</pre>
      </details>

      {detail.choices.length > 0 ? (
        <details className="panel">
          <summary>Choices</summary>
          <ul className="choices">
            {detail.choices.map((choice) => (
              <li key={choice.label}>
                <strong>{choice.label}</strong> {choice.candidate}
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      <details className="panel">
        <summary>Diagnostics</summary>
        <dl>
          {detail.diagnostics.map((entry) => (
            <div key={entry.label}>
              <dt>{entry.label}</dt>
              <dd>{entry.value}</dd>
            </div>
          ))}
        </dl>
        <p className="meta">{counts}</p>
      </details>

      <details className="panel">
        <summary>Usage</summary>
        <p>Left-drag orbits. Right-drag or Shift-drag pans. The wheel zooms.</p>
        <p className="axes">Axes: X (red), Y (green), Z (blue)</p>
      </details>

      <details className="panel">
        <summary>Program</summary>
        <pre>{detail.program}</pre>
      </details>
    </aside>
  );
}
