import { useState } from "react";
import type { Constraint } from "../types";
import { WEEKDAY_LABELS } from "../types";

interface Props {
  constraints: Constraint[];
  onAdd: (text: string) => Promise<void>;
  onDelete: (id: number) => void;
}

function describe(c: Constraint): string {
  switch (c.constraint_type) {
    case "recurring_weekday_limit":
      return `毎週${WEEKDAY_LABELS[c.weekday ?? 0]}曜日: ${c.available_hours}時間まで${c.reason ? `（${c.reason}）` : ""}`;
    case "specific_date_limit":
      return `${c.date}: ${c.available_hours}時間まで${c.reason ? `（${c.reason}）` : ""}`;
    case "specific_date_unavailable":
      return `${c.date}: 終日作業不可${c.reason ? `（${c.reason}）` : ""}`;
    case "date_range_unavailable":
      return `${c.start_date} 〜 ${c.end_date}: 終日作業不可${c.reason ? `（${c.reason}）` : ""}`;
    default:
      return c.raw_text;
  }
}

export default function ConstraintPanel({ constraints, onAdd, onDelete }: Props) {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await onAdd(text.trim());
      setText("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card">
      <h2>自然言語で制約を入力</h2>
      <form onSubmit={handleSubmit} className="row">
        <input
          className="grow"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="例: 火曜はバイトで2時間しか使えない"
        />
        <button type="submit" disabled={submitting}>
          {submitting ? "解析中..." : "追加"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      {constraints.length > 0 && (
        <ul className="constraint-list">
          {constraints.map((c) => (
            <li key={c.id} className="constraint-item">
              <div>
                <div className="constraint-desc">{describe(c)}</div>
                <div className="muted small">「{c.raw_text}」</div>
              </div>
              <button className="link-btn" onClick={() => onDelete(c.id)}>
                削除
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
