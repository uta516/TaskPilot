import { useMemo, useState } from "react";
import type { Task } from "../types";

interface Props {
  tasks: Task[];
  onDelete: (id: number) => void;
}

type SortKey = "deadline" | "importance" | "estimated_hours";

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "deadline", label: "締切が近い順" },
  { value: "importance", label: "重要度が高い順" },
  { value: "estimated_hours", label: "所要時間が長い順" },
];

function sortTasks(tasks: Task[], key: SortKey): Task[] {
  const copy = [...tasks];
  copy.sort((a, b) => {
    switch (key) {
      case "deadline":
        return a.deadline.localeCompare(b.deadline);
      case "importance":
        return b.importance - a.importance;
      case "estimated_hours":
        return b.estimated_hours - a.estimated_hours;
    }
  });
  return copy;
}

export default function TaskList({ tasks, onDelete }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("deadline");
  const sortedTasks = useMemo(() => sortTasks(tasks, sortKey), [tasks, sortKey]);

  if (tasks.length === 0) {
    return (
      <div className="card">
        <h2>登録済みタスク</h2>
        <p className="muted">まだタスクがありません。</p>
      </div>
    );
  }

  const nameById = new Map(tasks.map((t) => [t.id, t.name]));

  return (
    <div className="card">
      <div className="task-list-header">
        <h2>登録済みタスク ({tasks.length})</h2>
        <div className="sort-control">
          <span>並び替え</span>
          <select value={sortKey} onChange={(e) => setSortKey(e.target.value as SortKey)}>
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      <ul className="task-list">
        {sortedTasks.map((t) => (
          <li key={t.id} className="task-item">
            <div className="task-item-main">
              <span className="task-name">{t.name}</span>
              <span className="badge">重要度 {t.importance}</span>
            </div>
            <div className="task-item-meta">
              締切: {t.deadline} ・ 所要: {t.estimated_hours}h
              {t.depends_on.length > 0 && (
                <> ・ 依存: {t.depends_on.map((id) => nameById.get(id) ?? `#${id}`).join(", ")}</>
              )}
            </div>
            <button className="link-btn" onClick={() => onDelete(t.id)}>
              削除
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
