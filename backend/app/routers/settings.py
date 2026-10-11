from fastapi import APIRouter

from app import db
from app.schemas import SettingsOut, SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_settings():
    return db.get_settings()


@router.put("", response_model=SettingsOut)
def put_settings(payload: SettingsUpdate):
    return db.update_settings(payload.default_daily_hours, payload.horizon_days)
