import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR.parent / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else None)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
DB_PATH = BASE_DIR / "data.db"

DEFAULT_DAILY_HOURS = 4.0
DEFAULT_HORIZON_DAYS = 30
