from datetime import date, datetime

from fastapi import APIRouter, HTTPException

from app import db, gemini, scheduler
from app.schemas import ScheduleResponse

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


@router.post("/generate", response_model=ScheduleResponse)
def generate():
    raw_tasks = db.list_tasks()
    constraints = db.list_constraints()
    settings = db.get_settings()

    tasks_for_solver = [
        {**t, "deadline": datetime.strptime(t["deadline"], "%Y-%m-%d").date()} for t in raw_tasks
    ]

    result = scheduler.generate_schedule(
        tasks_for_solver,
        constraints,
        settings["default_daily_hours"],
        settings["horizon_days"],
        date.today(),
    )

    explanation = None
    try:
        if result["feasible"]:
            explanation = gemini.explain_schedule(result, raw_tasks)
        else:
            explanation = gemini.explain_infeasibility(result["issues"], result["suggestions"], raw_tasks)
    except Exception:  # noqa: BLE001
        explanation = None

    schedule_id = db.save_schedule(result["feasible"], result, explanation)
    return {
        "id": schedule_id,
        "feasible": result["feasible"],
        "result": result,
        "explanation": explanation,
        "created_at": db.now_iso(),
    }


@router.get("/latest", response_model=ScheduleResponse)
def latest():
    data = db.get_latest_schedule()
    if not data:
        raise HTTPException(404, "まだスケジュールが生成されていません")
    return {
        "id": data["id"],
        "feasible": data["feasible"],
        "result": data["result"],
        "explanation": data["explanation"],
        "created_at": data["created_at"],
    }
