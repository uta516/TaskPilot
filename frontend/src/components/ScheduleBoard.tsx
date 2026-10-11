import type { DayLoad, ScheduledItem } from "../types";

interface Props {
  items: ScheduledItem[];
  dayLoads: DayLoad[];
}

export default function ScheduleBoard({ items, dayLoads }: Props) {
  const itemsByDay = new Map<string, ScheduledItem[]>();
  for (const item of items) {
    const list = itemsByDay.get(item.day) ?? [];
    list.push(item);
    itemsByDay.set(item.day, list);
  }

  return (
    <div className="card">
      <h2>生成されたスケジュール</h2>
      <div className="day-board">
        {dayLoads.map((dl) => (
          <div key={dl.day} className="day-column">
            <div className="day-header">
              <span>{dl.day}</span>
              {dl.is_override && <span className="badge warn">{dl.note ?? "制約あり"}</span>}
            </div>
            <div className="day-capacity-bar">
              <div
                className="day-capacity-fill"
                style={{ width: `${Math.min(100, (dl.used_hours / dl.capacity_hours) * 100)}%` }}
              />
            </div>
            <div className="muted small">
              {dl.used_hours}h / {dl.capacity_hours}h
            </div>
            <ul className="day-tasks">
              {(itemsByDay.get(dl.day) ?? []).map((item) => (
                <li key={item.task_id} className="day-task">
                  <span>{item.task_name}</span>
                  <span className="muted small">
                    {item.estimated_hours}h ・ 重要度{item.importance}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
