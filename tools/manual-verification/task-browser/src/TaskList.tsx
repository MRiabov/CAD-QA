import type { TaskQuery } from "./api";
import type { Facets, TaskPage } from "./types";

interface TaskListProps {
  facets: Facets | null;
  page: TaskPage | null;
  query: TaskQuery;
  activeId: string | null;
  onQueryChange: (query: TaskQuery) => void;
  onSelect: (taskId: string) => void;
}

function Select({
  label,
  value,
  values,
  onChange,
}: {
  label: string;
  value: string;
  values: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="filter">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">All</option>
        {values.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </select>
    </label>
  );
}

export function TaskList({
  facets,
  page,
  query,
  activeId,
  onQueryChange,
  onSelect,
}: TaskListProps) {
  const update = (patch: Partial<TaskQuery>) => onQueryChange({ ...query, ...patch });

  const first = page === null ? 0 : page.offset + 1;
  const last = page === null ? 0 : page.offset + page.tasks.length;

  return (
    <section className="task-list">
      <div className="filters">
        <input
          className="search"
          type="search"
          placeholder="Search prompts, answers, IDs"
          value={query.search}
          onChange={(event) => update({ search: event.target.value, offset: 0 })}
        />
        <Select
          label="Split"
          value={query.split}
          values={facets?.splits ?? []}
          onChange={(split) => update({ split, offset: 0 })}
        />
        <Select
          label="Subset"
          value={query.subset}
          values={facets?.subsets ?? []}
          onChange={(subset) => update({ subset, offset: 0 })}
        />
        <Select
          label="Target"
          value={query.targetCategory}
          values={facets?.target_categories ?? []}
          onChange={(targetCategory) => update({ targetCategory, offset: 0 })}
        />
        <Select
          label="Answer"
          value={query.answerMeaning}
          values={facets?.answer_meanings ?? []}
          onChange={(answerMeaning) => update({ answerMeaning, offset: 0 })}
        />
        <div className="filter-actions">
          <select
            value={query.order}
            onChange={(event) =>
              update({
                order: event.target.value === "random" ? "random" : "file",
                offset: 0,
              })
            }
          >
            <option value="file">File order</option>
            <option value="random">Random</option>
          </select>
          <button
            type="button"
            onClick={() =>
              update({
                order: "random",
                offset: 0,
                seed: `${Date.now()}`,
              })
            }
          >
            Shuffle
          </button>
        </div>
      </div>

      <div className="task-cards">
        {page?.tasks.map((task) => (
          <button
            key={task.task_id}
            type="button"
            className={`task-card${task.task_id === activeId ? " active" : ""}`}
            onClick={() => onSelect(task.task_id)}
          >
            <span className="task-card-meta">
              {task.split} · {task.subset} · {task.target_category} ·{" "}
              {task.task_reasoning_step_count} steps
            </span>
            <span className="task-card-prompt">{task.prompt_preview}</span>
            <span className="task-card-answer">{task.answer}</span>
          </button>
        ))}
        {page !== null && page.tasks.length === 0 ? (
          <p className="empty">No tasks match these filters.</p>
        ) : null}
      </div>

      <div className="pager">
        <button
          type="button"
          disabled={query.offset <= 0}
          onClick={() => update({ offset: Math.max(0, query.offset - query.limit) })}
        >
          Prev
        </button>
        <span>
          {first}–{last} of {page?.total ?? 0}
        </span>
        <button
          type="button"
          disabled={page === null || query.offset + query.limit >= page.total}
          onClick={() => update({ offset: query.offset + query.limit })}
        >
          Next
        </button>
      </div>
    </section>
  );
}
