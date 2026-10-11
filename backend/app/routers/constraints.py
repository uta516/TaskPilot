from datetime import date

from fastapi import APIRouter, HTTPException

from app import db, gemini
from app.schemas import ConstraintCreate, ConstraintOut, ParsedConstraint

router = APIRouter(prefix="/api/constraints", tags=["constraints"])


@router.get("", response_model=list[ConstraintOut])
def get_constraints():
    return db.list_constraints()


@router.post("", response_model=list[ConstraintOut], status_code=201)
def post_constraint(payload: ConstraintCreate):
    try:
        parsed_list = gemini.parse_constraint_text(payload.text, date.today())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"制約の解析に失敗しました: {exc}") from exc

    if not parsed_list:
        raise HTTPException(422, "制約を解析できませんでした。表現を変えて再入力してください。")

    created_ids = []
    for raw in parsed_list:
        try:
            validated = ParsedConstraint.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(422, f"Geminiの応答が不正な形式です: {exc}") from exc
        data = validated.model_dump()
        for key in ("date", "start_date", "end_date"):
            if data.get(key) is not None:
                data[key] = data[key].isoformat()
        created_id = db.create_constraint(payload.text, data)
        created_ids.append(created_id)

    all_constraints = {c["id"]: c for c in db.list_constraints()}
    return [all_constraints[cid] for cid in created_ids]


@router.delete("/{constraint_id}", status_code=204)
def remove_constraint(constraint_id: int):
    db.delete_constraint(constraint_id)
