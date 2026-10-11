import { useEffect, useState } from "react";
import "./App.css";
import { api } from "./api";
import type { Constraint, ScheduleResponse, Settings, Task } from "./types";
import TaskForm from "./components/TaskForm";
import TaskList from "./components/TaskList";
import ConstraintPanel from "./components/ConstraintPanel";
import SettingsPanel from "./components/SettingsPanel";
import ScheduleBoard from "./components/ScheduleBoard";
import ExplanationCard from "./components/ExplanationCard";
import RelaxSuggestions from "./components/RelaxSuggestions";

export default function App() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [constraints, setConstraints] = useState<Constraint[]>([]);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [schedule, setSchedule] = useState<ScheduleResponse | null>(null);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    (async () => {
      const [t, c, s] = await Promise.all([api.listTasks(), api.listConstraints(), api.getSettings()]);
      setTasks(t);
      setConstraints(c);
      setSettings(s);
      try {
        setSchedule(await api.getLatestSchedule());
      } catch {
        // まだスケジュール未生成
      }
      setLoaded(true);
    })();
  }, []);

  const handleAddTask = async (task: {
    name: string;
    deadline: string;
    estimated_hours: number;
    importance: number;
    depends_on: number[];
  }) => {
    const created = await api.createTask(task);
    setTasks((prev) => [...prev, created]);
  };

  const handleDeleteTask = async (id: number) => {
    await api.deleteTask(id);
    setTasks((prev) => prev.filter((t) => t.id !== id));
  };

  const handleAddConstraint = async (text: string) => {
    const created = await api.createConstraint(text);
    setConstraints((prev) => [...prev, ...created]);
  };

  const handleDeleteConstraint = async (id: number) => {
    await api.deleteConstraint(id);
    setConstraints((prev) => prev.filter((c) => c.id !== id));
  };

  const handleUpdateSettings = async (patch: Partial<Settings>) => {
    const updated = await api.updateSettings(patch);
    setSettings(updated);
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setGenError(null);
    try {
      const result = await api.generateSchedule();
      setSchedule(result);
    } catch (err) {
      setGenError(err instanceof Error ? err.message : String(err));
    } finally {
      setGenerating(false);
    }
  };

  if (!loaded) {
    return <div className="app-loading">読み込み中...</div>;
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>TaskPilot</h1>
        <p className="muted">AIとSATソルバーで作るタスクスケジュール</p>
      </header>

      <main className="app-grid">
        <section className="app-col">
          <SettingsPanel settings={settings} onUpdate={handleUpdateSettings} />
          <TaskForm tasks={tasks} onSubmit={handleAddTask} />
          <TaskList tasks={tasks} onDelete={handleDeleteTask} />
          <ConstraintPanel constraints={constraints} onAdd={handleAddConstraint} onDelete={handleDeleteConstraint} />
        </section>

        <section className="app-col">
          <div className="card">
            <button className="primary-btn" onClick={handleGenerate} disabled={generating || tasks.length === 0}>
              {generating ? "生成中..." : "スケジュールを生成"}
            </button>
            {tasks.length === 0 && <p className="muted small">タスクを登録すると生成できます。</p>}
            {genError && <p className="error">{genError}</p>}
          </div>

          {schedule && schedule.result.feasible && (
            <>
              <ScheduleBoard items={schedule.result.items} dayLoads={schedule.result.day_loads} />
              <ExplanationCard title="なぜこの配置になったか" explanation={schedule.explanation} />
            </>
          )}

          {schedule && !schedule.result.feasible && (
            <>
              <RelaxSuggestions issues={schedule.result.issues} suggestions={schedule.result.suggestions} />
              <ExplanationCard title="詳しい説明" explanation={schedule.explanation} />
            </>
          )}
        </section>
      </main>
    </div>
  );
}
