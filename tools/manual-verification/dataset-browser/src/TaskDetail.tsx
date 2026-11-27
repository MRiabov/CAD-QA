import { useState } from "react";
import type { ReactNode } from "react";
import { Code } from "./Code";
import type { OracleRecord, ScenePayload, TaskDetail as TaskDetailType } from "./types";

interface TaskDetailProps {
  detail: TaskDetailType | null;
  scene: ScenePayload | null;
  sceneError: string | null;
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="group">
      <h2 className="group-title">{title}</h2>
      {children}
    </section>
  );
}

function Panel({
  id,
  title,
  open,
  onToggle,
  children,
}: {
  id: string;
  title: string;
  open: boolean;
  onToggle: (id: string, open: boolean) => void;
  children: ReactNode;
}) {
  return (
    <details
      className="panel"
      open={open}
      onToggle={(event) => onToggle(id, event.currentTarget.open)}
    >
      <summary>{title}</summary>
      {children}
    </details>
  );
}

function OracleStatus({ oracle }: { oracle: OracleRecord }) {
  const check = oracle.verification.gold_query;
  const stdout = check.stdout === null ? "" : ` (${check.stdout})`;
  const checked = check.checked_at === null ? "" : ` · ${check.checked_at}`;
  return (
    <p className={`oracle-status ${oracle.verification.status}`}>
      {oracle.verification.status} · gold query {check.status}
      {stdout}
      {checked}
    </p>
  );
}

function VerificationContent({ oracle }: { oracle: OracleRecord }) {
  return (
    <>
      <dl>
        <div>
          <dt>status</dt>
          <dd>{oracle.verification.status}</dd>
        </div>
        <div>
          <dt>verified by</dt>
          <dd>{oracle.verification.verified_by ?? "—"}</dd>
        </div>
        <div>
          <dt>verified at</dt>
          <dd>{oracle.verification.verified_at ?? "—"}</dd>
        </div>
        <div>
          <dt>gold query</dt>
          <dd>
            {oracle.verification.gold_query.status} ·{" "}
            {oracle.verification.gold_query.checked_at ?? "not recorded"}
          </dd>
        </div>
      </dl>
      <p>{oracle.verification.rationale}</p>
    </>
  );
}

function TaskDescriptionContent({ oracle }: { oracle: OracleRecord }) {
  const task = oracle.task;
  const answer = oracle.answer;
  const tolerance =
    answer.tolerance === null
      ? "exact"
      : `${answer.tolerance.tolerance_kind} ${answer.tolerance.value_text}`;

  return (
    <>
      <dl>
        <div>
          <dt>target category</dt>
          <dd>{task.target_category}</dd>
        </div>
        <div>
          <dt>possible answers</dt>
          <dd>{task.possible_answer_count}</dd>
        </div>
        <div>
          <dt>reasoning steps</dt>
          <dd>{task.task_reasoning_step_count}</dd>
        </div>
        <div>
          <dt>answer</dt>
          <dd>
            {task.answer_format} ({task.answer_meaning}), native {task.native_answer_format}
          </dd>
        </div>
        <div>
          <dt>geometry required</dt>
          <dd>{task.geometry_required ? "yes" : "no"}</dd>
        </div>
        <div>
          <dt>uniqueness</dt>
          <dd>{task.uniqueness}</dd>
        </div>
      </dl>
      <p className="meta">
        {answer.evidence_kind} · {answer.evidence_rule} · scoring {answer.scoring_rule} · tolerance{" "}
        {tolerance} · {answer.answer_equivalent_set.length} answer-equivalent entries
      </p>
    </>
  );
}

function ClueChainContent({ oracle }: { oracle: OracleRecord }) {
  if (oracle.clues.length === 0) {
    return <p>The question names the target directly; there is no clue.</p>;
  }
  return (
    <ol className="clues">
      {oracle.clues.map((clue) => (
        <li key={clue.order}>
          <span className="clue-statement">{clue.statement}</span>
          <span className="clue-meta">
            {clue.clue_type}
            {clue.clue_reduction_form === null ? "" : ` · ${clue.clue_reduction_form}`}
            {` · narrows ${clue.narrows.before} → ${clue.narrows.after}`}
          </span>
        </li>
      ))}
    </ol>
  );
}

function GoldQueryContent({ oracle }: { oracle: OracleRecord }) {
  return (
    <>
      <Code code={oracle.gold_query.code} language="python" />
      <dl>
        <div>
          <dt>expected stdout</dt>
          <dd>{oracle.gold_query.expected_stdout}</dd>
        </div>
        <div>
          <dt>sha256</dt>
          <dd>{oracle.gold_query.sha256}</dd>
        </div>
      </dl>
    </>
  );
}

function CoverageContent({ oracle }: { oracle: OracleRecord }) {
  return (
    <dl>
      <div>
        <dt>target category</dt>
        <dd>{oracle.covers.target_category}</dd>
      </div>
      <div>
        <dt>clue types</dt>
        <dd>{oracle.covers.clue_types.join(", ") || "none"}</dd>
      </div>
      <div>
        <dt>reduction forms</dt>
        <dd>{oracle.covers.clue_reduction_forms.join(", ") || "none"}</dd>
      </div>
      <div>
        <dt>answer</dt>
        <dd>
          {oracle.covers.answer_format} ({oracle.covers.answer_meaning})
        </dd>
      </div>
      <div>
        <dt>reasoning steps</dt>
        <dd>{oracle.covers.task_reasoning_step_count}</dd>
      </div>
    </dl>
  );
}

function fullPrompt(detail: TaskDetailType): string {
  if (detail.prompt !== null) return detail.prompt;
  const oracle = detail.oracle;
  if (oracle === null) return detail.program;
  const lines = ["```python", detail.program.trimEnd(), "```", "", oracle.task.question];
  if (oracle.clues.length > 0) {
    lines.push("", ...oracle.clues.map((clue) => `${clue.order}. ${clue.statement}`));
  }
  return lines.join("\n");
}

export function TaskDetail({ detail, scene, sceneError }: TaskDetailProps) {
  const [openPanels, setOpenPanels] = useState<Record<string, boolean>>({
    verification: true,
  });
  const togglePanel = (id: string, open: boolean) =>
    setOpenPanels((current) => ({ ...current, [id]: open }));
  const panel = (id: string, title: string, children: ReactNode) => (
    <Panel id={id} title={title} open={openPanels[id] ?? false} onToggle={togglePanel}>
      {children}
    </Panel>
  );

  if (detail === null) {
    return (
      <aside className="detail-pane">
        <p className="empty">Select a task.</p>
      </aside>
    );
  }

  const oracle = detail.oracle;
  const counts =
    scene === null
      ? (sceneError ?? "loading scene…")
      : `${scene.triangle_count} triangles · ${scene.segment_count} line segments`;

  return (
    <aside className="detail-pane">
      <Group title="Task">
        {panel("full-prompt", "Full prompt", <pre>{fullPrompt(detail)}</pre>)}
        {oracle === null
          ? null
          : panel("question", "Question", <p className="question">{oracle.task.question}</p>)}
        {panel("program", "Program", <Code code={detail.program} language="python" />)}
        {oracle === null
          ? null
          : panel("clues", "Clue chain", <ClueChainContent oracle={oracle} />)}
      </Group>

      <Group title="Solution">
        <section className="answer-block">
          <h2>Answer</h2>
          <p className="answer">{detail.answer}</p>
          {oracle === null ? null : <OracleStatus oracle={oracle} />}
        </section>
        {oracle === null
          ? null
          : panel("verification", "Verification", <VerificationContent oracle={oracle} />)}
        {oracle === null
          ? null
          : panel("gold-query", "Gold query", <GoldQueryContent oracle={oracle} />)}
      </Group>

      <Group title="Other">
        {oracle === null
          ? null
          : panel(
              "task-description",
              "Task description",
              <TaskDescriptionContent oracle={oracle} />,
            )}
        {oracle === null
          ? null
          : panel("coverage", "Coverage", <CoverageContent oracle={oracle} />)}
        {oracle === null ? null : (
          <Panel
            id="excluded"
            title="Excluded"
            open={openPanels.excluded ?? false}
            onToggle={togglePanel}
          >
            <ul className="choices">
              {oracle.excluded.map((entry) => (
                <li key={`${entry.exclusion_kind}:${entry.reason}`}>
                  <strong>{entry.exclusion_kind}</strong> {entry.reason}
                </li>
              ))}
            </ul>
          </Panel>
        )}
        {oracle === null || oracle.notes.length === 0 ? null : (
          <Panel id="notes" title="Notes" open={openPanels.notes ?? false} onToggle={togglePanel}>
            <ul className="choices">
              {oracle.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </Panel>
        )}
        {oracle === null ? null : (
          <Panel
            id="environment"
            title="Environment"
            open={openPanels.environment ?? false}
            onToggle={togglePanel}
          >
            <p className="meta">
              CadQuery {oracle.environment.cadquery_version} · OCP {oracle.environment.ocp_version}{" "}
              · Python {oracle.environment.python_version} · oracle tool{" "}
              {oracle.environment.oracle_tool_version}
            </p>
          </Panel>
        )}
        {detail.choices.length === 0 ? null : (
          <Panel
            id="choices"
            title="Choices"
            open={openPanels.choices ?? false}
            onToggle={togglePanel}
          >
            <ul className="choices">
              {detail.choices.map((choice) => (
                <li key={choice.label}>
                  <strong>{choice.label}</strong> {choice.candidate}
                </li>
              ))}
            </ul>
          </Panel>
        )}
        <Panel
          id="diagnostics"
          title="Diagnostics"
          open={openPanels.diagnostics ?? false}
          onToggle={togglePanel}
        >
          <dl>
            {detail.diagnostics.map((entry) => (
              <div key={entry.label}>
                <dt>{entry.label}</dt>
                <dd>{entry.value}</dd>
              </div>
            ))}
          </dl>
          <p className="meta">{counts}</p>
        </Panel>
        <Panel id="usage" title="Usage" open={openPanels.usage ?? false} onToggle={togglePanel}>
          <p>Left-drag orbits. Right-drag or Shift-drag pans. The wheel zooms.</p>
          <p className="axes">Axes: X (red), Y (green), Z (blue)</p>
        </Panel>
      </Group>
    </aside>
  );
}
