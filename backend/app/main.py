from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routers import constraints, schedule, settings, tasks

app = FastAPI(title="TaskPilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(tasks.router)
app.include_router(constraints.router)
app.include_router(settings.router)
app.include_router(schedule.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
