import type { Constraint, ScheduleResponse, Settings, Task } from "./types";

const BASE_URL = "http://127.0.0.1:8001";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json; charset=utf-8" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore JSON parse failure
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  listTasks: () => request<Task[]>("/api/tasks"),
  createTask: (task: {
    name: string;
    deadline: string;
    estimated_hours: number;
    importance: number;
    depends_on: number[];
  }) => request<Task>("/api/tasks", { method: "POST", body: JSON.stringify(task) }),
  deleteTask: (id: number) => request<void>(`/api/tasks/${id}`, { method: "DELETE" }),

  listConstraints: () => request<Constraint[]>("/api/constraints"),
  createConstraint: (text: string) =>
    request<Constraint[]>("/api/constraints", { method: "POST", body: JSON.stringify({ text }) }),
  deleteConstraint: (id: number) => request<void>(`/api/constraints/${id}`, { method: "DELETE" }),

  getSettings: () => request<Settings>("/api/settings"),
  updateSettings: (settings: Partial<Settings>) =>
    request<Settings>("/api/settings", { method: "PUT", body: JSON.stringify(settings) }),

  generateSchedule: () => request<ScheduleResponse>("/api/schedule/generate", { method: "POST" }),
  getLatestSchedule: () => request<ScheduleResponse>("/api/schedule/latest"),
};
