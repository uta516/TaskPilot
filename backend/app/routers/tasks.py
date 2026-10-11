from fastapi import APIRouter, HTTPException

from app import db
from app.schemas import TaskCreate, TaskOut

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
def get_tasks():
    return db.list_tasks()


@router.post("", response_model=TaskOut, status_code=201)
def post_task(task: TaskCreate):
    existing_ids = {t["id"] for t in db.list_tasks()}
    for dep_id in task.depends_on:
        if dep_id not in existing_ids:
            raise HTTPException(400, f"依存タスク ID {dep_id} が存在しません")
    task_id = db.create_task(
        task.name, task.deadline.isoformat(), task.estimated_hours, task.importance, task.depends_on
    )
    return next(t for t in db.list_tasks() if t["id"] == task_id)


@router.delete("/{task_id}", status_code=204)
def remove_task(task_id: int):
    db.delete_task(task_id)
