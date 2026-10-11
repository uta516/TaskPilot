import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import DB_PATH, DEFAULT_DAILY_HOURS, DEFAULT_HORIZON_DAYS

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    deadline TEXT NOT NULL,
    estimated_hours REAL NOT NULL,
    importance INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_dependencies (
    task_id INTEGER NOT NULL,
    depends_on_id INTEGER NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (depends_on_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS constraints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_text TEXT NOT NULL,
    constraint_type TEXT NOT NULL,
    weekday INTEGER,
    date TEXT,
    start_date TEXT,
    end_date TEXT,
    available_hours REAL,
    reason TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    feasible INTEGER NOT NULL,
    result_json TEXT NOT NULL,
    explanation TEXT
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        defaults = {
            "default_daily_hours": str(DEFAULT_DAILY_HOURS),
            "horizon_days": str(DEFAULT_HORIZON_DAYS),
        }
        for key, value in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )


# ---------- tasks ----------

def create_task(name, deadline, estimated_hours, importance, depends_on):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (name, deadline, estimated_hours, importance, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, deadline, estimated_hours, importance, now_iso()),
        )
        task_id = cur.lastrowid
        for dep_id in depends_on:
            conn.execute(
                "INSERT INTO task_dependencies (task_id, depends_on_id) VALUES (?, ?)",
                (task_id, dep_id),
            )
        return task_id


def list_tasks():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY deadline ASC").fetchall()
        tasks = []
        for row in rows:
            deps = conn.execute(
                "SELECT depends_on_id FROM task_dependencies WHERE task_id = ?",
                (row["id"],),
            ).fetchall()
            task = dict(row)
            task["depends_on"] = [d["depends_on_id"] for d in deps]
            tasks.append(task)
        return tasks


def delete_task(task_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM task_dependencies WHERE task_id = ? OR depends_on_id = ?", (task_id, task_id))
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


# ---------- constraints ----------

def create_constraint(raw_text, parsed):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO constraints "
            "(raw_text, constraint_type, weekday, date, start_date, end_date, available_hours, reason, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                raw_text,
                parsed["constraint_type"],
                parsed.get("weekday"),
                parsed.get("date"),
                parsed.get("start_date"),
                parsed.get("end_date"),
                parsed.get("available_hours"),
                parsed.get("reason"),
                now_iso(),
            ),
        )
        return cur.lastrowid


def list_constraints():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM constraints ORDER BY id ASC").fetchall()
        return [dict(row) for row in rows]


def delete_constraint(constraint_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM constraints WHERE id = ?", (constraint_id,))


# ---------- settings ----------

def get_settings():
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        raw = {row["key"]: row["value"] for row in rows}
        return {
            "default_daily_hours": float(raw.get("default_daily_hours", DEFAULT_DAILY_HOURS)),
            "horizon_days": int(raw.get("horizon_days", DEFAULT_HORIZON_DAYS)),
        }


def update_settings(default_daily_hours=None, horizon_days=None):
    with get_conn() as conn:
        if default_daily_hours is not None:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('default_daily_hours', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (str(default_daily_hours),),
            )
        if horizon_days is not None:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('horizon_days', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (str(horizon_days),),
            )
    return get_settings()


# ---------- schedules ----------

def save_schedule(feasible, result: dict, explanation: str | None):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO schedules (created_at, feasible, result_json, explanation) VALUES (?, ?, ?, ?)",
            (now_iso(), 1 if feasible else 0, json.dumps(result, ensure_ascii=False, default=str), explanation),
        )
        return cur.lastrowid


def get_latest_schedule():
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM schedules ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["result"] = json.loads(data.pop("result_json"))
        data["feasible"] = bool(data["feasible"])
        return data
