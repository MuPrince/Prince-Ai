from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.record import RecordCreate, RecordOut
from app.services.record_service import (
    create_manual_record,
    list_records_by_task,
)
from app.services.task_service import _get_task

router = APIRouter(prefix="/api/tasks/{task_id}/records", tags=["records"])


@router.get("", response_model=list[RecordOut])
def api_list_records(task_id: int, db: Session = Depends(get_db)):
    try:
        _get_task(db, task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return list_records_by_task(db, task_id)


@router.post("", response_model=RecordOut, status_code=201)
def api_create_record(
    task_id: int, payload: RecordCreate, db: Session = Depends(get_db)
):
    try:
        _get_task(db, task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return create_manual_record(db, task_id, payload.started_at, payload.content)
