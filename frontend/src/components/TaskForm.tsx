import { useState } from "react";
import type { Task } from "../types";

interface Props {
  tasks: Task[];
  onSubmit: (task: {
    name: string;
    deadline: string;
    estimated_hours: number;
    importance: number;
    depends_on: number[];
  }) => Promise<void>;
}

export default function TaskForm({ tasks, onSubmit }: Props) {
  const [name, setName] = useState("");
  const [deadline, setDeadline] = useState("");
  const [hours, setHours] = useState("1");
  const [importance, setImportance] = useState("3");
  const [dependsOn, setDependsOn] = useState<number[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleDep = (id: number) => {
    setDependsOn((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !deadline) {
      setError("タスク名と締切は必須です");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        name: name.trim(),
        deadline,
        estimated_hours: Number(hours),
        importance: Number(importance),
        depends_on: dependsOn,
      });
      setName("");
      setDeadline("");
      setHours("1");
      setImportance("3");
      setDependsOn([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2>タスクを登録</h2>
      <label>
        タスク名
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="例: レポート執筆" />
      </label>
      <div className="row">
        <label>
          締切
          <input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
        </label>
        <label>
          推定所要時間 (h)
          <input type="number" min="0.5" step="0.5" value={hours} onChange={(e) => setHours(e.target.value)} />
        </label>
        <label>
          重要度 (5が最重要)
          <select value={importance} onChange={(e) => setImportance(e.target.value)}>
            {[1, 2, 3, 4, 5].map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </label>
      </div>
      {tasks.length > 0 && (
        <fieldset>
          <legend>依存タスク（このタスクより先に完了させる必要があるもの）</legend>
          <div className="dep-list">
            {tasks.map((t) => (
              <label key={t.id} className="dep-item">
                <input
                  type="checkbox"
                  checked={dependsOn.includes(t.id)}
                  onChange={() => toggleDep(t.id)}
                />
                {t.name}
              </label>
            ))}
          </div>
        </fieldset>
      )}
      {error && <p className="error">{error}</p>}
      <button type="submit" disabled={submitting}>
        {submitting ? "登録中..." : "タスクを追加"}
      </button>
    </form>
  );
}
