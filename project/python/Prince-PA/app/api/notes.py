from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import NoteFile, NoteKind
from app.schemas.note import NoteContent, NoteOut
from app.services.note_service import read_note_content, write_note
from app.services.task_service import _get_task

router = APIRouter(prefix="/api/tasks/{task_id}", tags=["notes"])


@router.get("/note", response_model=NoteOut)
def api_get_note(task_id: int, db: Session = Depends(get_db)):
    try:
        _get_task(db, task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    row = db.scalar(
        select(NoteFile).where(
            NoteFile.task_id == task_id, NoteFile.kind == NoteKind.note
        )
    )
    return NoteOut(
        content=read_note_content(db, task_id),
        rel_path=row.rel_path if row else None,
    )


@router.put("/note", response_model=NoteOut)
def api_save_note(task_id: int, payload: NoteContent, db: Session = Depends(get_db)):
    try:
        row = write_note(db, task_id, payload.content)
    except (LookupError, ValueError) as exc:
        status = 404 if isinstance(exc, LookupError) else 400
        raise HTTPException(status_code=status, detail=str(exc))
    return NoteOut(content=payload.content, rel_path=row.rel_path)
