import json
from datetime import date
from typing import Optional

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import GEMINI_API_KEY, GEMINI_MODEL

_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY が設定されていません (.env を確認してください)")
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


class _GeminiConstraint(BaseModel):
    constraint_type: str
    weekday: Optional[int] = None
    date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    available_hours: Optional[float] = None
    reason: Optional[str] = None


class _GeminiConstraintList(BaseModel):
    constraints: list[_GeminiConstraint]


CONSTRAINT_SYSTEM_PROMPT = """あなたはタスク管理アプリ TaskPilot の自然言語制約パーサーです。
ユーザーが日本語で入力した「作業できる時間の制約」を、構造化データに変換してください。

各制約は次の4種類のいずれかに分類します:
- recurring_weekday_limit: 毎週特定の曜日に使える時間が限られる（weekday, available_hours を指定。weekday は 0=月曜〜6=日曜）
- specific_date_limit: 特定の1日だけ使える時間が限られる（date, available_hours を指定）
- specific_date_unavailable: 特定の1日がまったく作業できない（date を指定、available_hours は 0）
- date_range_unavailable: 連続する期間がまったく作業できない（start_date, end_date を指定）

日付は今日の日付を基準に解釈し、YYYY-MM-DD 形式の文字列で出力してください。
1つの入力文に複数の制約が含まれる場合は複数要素を返してください。
reason には制約の理由（バイト、旅行など）を短く日本語で入れてください。
時間が明示されていない「まったく使えない」場合は available_hours を 0 にしてください。
"""


def parse_constraint_text(text: str, today: date) -> list[dict]:
    client = get_client()
    prompt = (
        f"{CONSTRAINT_SYSTEM_PROMPT}\n\n"
        f"今日の日付: {today.isoformat()}\n"
        f"ユーザー入力: {text}"
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_GeminiConstraintList,
            temperature=0.0,
        ),
    )
    parsed: _GeminiConstraintList = response.parsed
    if parsed is None:
        data = json.loads(response.text)
        parsed = _GeminiConstraintList.model_validate(data)
    return [c.model_dump() for c in parsed.constraints]


EXPLANATION_SYSTEM_PROMPT = """あなたはタスク管理アプリ TaskPilot のスケジュール説明アシスタントです。
PySAT（SATソルバー）が生成したスケジュールの結果(JSON)を受け取り、
ユーザー向けに日本語で分かりやすく、根拠を示しながら説明してください。

説明には次を含めてください:
重要度は1〜5の整数で、5に近いほど重要度が高い（優先すべき）ことを意味します。1が最も重要度が低いタスクです。
この向きを取り違えないよう、説明の中では必ず「重要度5(最重要)」のように数値と高低を明示してください。

- 各タスクがなぜその日に配置されたか（締切、依存関係、重要度、他の日の混雑状況などを根拠に）
- 重要度が高いタスクがどのように優先されたか
- 日ごとの作業時間の使用状況の概観

丁寧だが簡潔な日本語で、箇条書きを活用してください。専門用語（SAT、CNFなど）は使わないでください。
"""


def explain_schedule(schedule_result: dict, tasks: list[dict]) -> str:
    client = get_client()
    prompt = (
        f"{EXPLANATION_SYSTEM_PROMPT}\n\n"
        f"タスク一覧: {json.dumps(tasks, ensure_ascii=False, default=str)}\n\n"
        f"スケジュール結果: {json.dumps(schedule_result, ensure_ascii=False, default=str)}"
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3),
    )
    return response.text


RELAX_SYSTEM_PROMPT = """あなたはタスク管理アプリ TaskPilot のアシスタントです。
全タスクを制約内に収めるスケジュールが作成できませんでした（実行不可能）。
どの制約を、どのように緩めれば解決できそうかの候補(JSON)が渡されるので、
ユーザーが状況を理解し納得して選択できるように、日本語で分かりやすく説明してください。
なぜ収まらないのか（重要度の低いタスクの締切や、忙しい日の時間制約が原因であることなど）にも触れてください。
重要度は1〜5の整数で、5に近いほど重要度が高く、1が最も重要度が低いタスクです。この向きを取り違えないでください。
丁寧だが簡潔な日本語で、箇条書きを活用してください。専門用語（SAT、UNSATなど）は使わないでください。
"""


def explain_infeasibility(issues: list[str], suggestions: list[dict], tasks: list[dict]) -> str:
    client = get_client()
    prompt = (
        f"{RELAX_SYSTEM_PROMPT}\n\n"
        f"タスク一覧: {json.dumps(tasks, ensure_ascii=False, default=str)}\n\n"
        f"検出された問題点: {json.dumps(issues, ensure_ascii=False)}\n\n"
        f"緩和候補: {json.dumps(suggestions, ensure_ascii=False, default=str)}"
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3),
    )
    return response.text
