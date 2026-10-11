export interface Task {
  id: number;
  name: string;
  deadline: string; // YYYY-MM-DD
  estimated_hours: number;
  importance: number;
  depends_on: number[];
  created_at: string;
}

export type ConstraintType =
  | "recurring_weekday_limit"
  | "specific_date_limit"
  | "specific_date_unavailable"
  | "date_range_unavailable";

export interface Constraint {
  id: number;
  raw_text: string;
  constraint_type: ConstraintType;
  weekday: number | null;
  date: string | null;
  start_date: string | null;
  end_date: string | null;
  available_hours: number | null;
  reason: string | null;
  created_at: string;
}

export interface Settings {
  default_daily_hours: number;
  horizon_days: number;
}

export interface ScheduledItem {
  task_id: number;
  task_name: string;
  day: string;
  estimated_hours: number;
  importance: number;
}

export interface DayLoad {
  day: string;
  capacity_hours: number;
  used_hours: number;
  is_override: boolean;
  note: string | null;
}

export interface RelaxSuggestion {
  kind: "extend_deadline" | "restore_capacity" | "reduce_hours";
  description: string;
  task_id: number | null;
  constraint_id: number | null;
}

export interface ScheduleResult {
  feasible: boolean;
  items: ScheduledItem[];
  day_loads: DayLoad[];
  suggestions: RelaxSuggestion[];
  issues: string[];
}

export interface ScheduleResponse {
  id: number;
  feasible: boolean;
  result: ScheduleResult;
  explanation: string | null;
  created_at: string;
}

export const WEEKDAY_LABELS = ["月", "火", "水", "木", "金", "土", "日"];
