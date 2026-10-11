from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    name: str
    deadline: date
    estimated_hours: float = Field(gt=0, le=200)
    importance: int = Field(ge=1, le=5)
    depends_on: list[int] = Field(default_factory=list)


class TaskOut(BaseModel):
    id: int
    name: str
    deadline: date
    estimated_hours: float
    importance: int
    depends_on: list[int]
    created_at: str


class ConstraintCreate(BaseModel):
    text: str


ConstraintType = Literal[
    "recurring_weekday_limit",
    "specific_date_limit",
    "specific_date_unavailable",
    "date_range_unavailable",
]


class ParsedConstraint(BaseModel):
    constraint_type: ConstraintType
    weekday: Optional[int] = None  # 0=Mon .. 6=Sun
    date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    available_hours: Optional[float] = None
    reason: Optional[str] = None


class ConstraintOut(BaseModel):
    id: int
    raw_text: str
    constraint_type: str
    weekday: Optional[int] = None
    date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    available_hours: Optional[float] = None
    reason: Optional[str] = None
    created_at: str


class SettingsUpdate(BaseModel):
    default_daily_hours: Optional[float] = Field(default=None, gt=0, le=24)
    horizon_days: Optional[int] = Field(default=None, ge=1, le=180)


class SettingsOut(BaseModel):
    default_daily_hours: float
    horizon_days: int


class ScheduledItem(BaseModel):
    task_id: int
    task_name: str
    day: date
    estimated_hours: float
    importance: int


class DayLoad(BaseModel):
    day: date
    capacity_hours: float
    used_hours: float
    is_override: bool
    note: Optional[str] = None


class RelaxSuggestion(BaseModel):
    kind: Literal["extend_deadline", "restore_capacity", "reduce_hours"]
    description: str
    task_id: Optional[int] = None
    constraint_id: Optional[int] = None


class ScheduleResult(BaseModel):
    feasible: bool
    items: list[ScheduledItem] = Field(default_factory=list)
    day_loads: list[DayLoad] = Field(default_factory=list)
    suggestions: list[RelaxSuggestion] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class ScheduleResponse(BaseModel):
    id: int
    feasible: bool
    result: ScheduleResult
    explanation: Optional[str] = None
    created_at: str
