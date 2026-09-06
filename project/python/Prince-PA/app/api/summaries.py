from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from agents.memory.profile import trigger_after_summary
from app.core.database import SessionLocal, get_db
from app.models.entities import SummaryStatus, Task
from app.schemas.note import SummaryOut
from app.services.completion_service import run_summary_generation
from app.services.note_service import read_summary_content

router = APIRouter(prefix="/api/tasks/{task_id}/summary", tags=["summaries"])


@router.get("", response_model=SummaryOut)
def api_get_summary(task_id: int, db: Session = Depends(get_db)):
    task = db.scalar(select(Task).where(Task.id == task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return SummaryOut(
        status=task.summary_status.value,
        content=read_summary_content(db, task_id),
        error=task.summary_error,
    )


@router.post("/regenerate", response_model=SummaryOut)
def api_regenerate_summary(
    task_id: int,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    task = db.scalar(select(Task).where(Task.id == task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.summary_status = SummaryStatus.pending
    task.summary_error = None
    db.commit()
    background.add_task(
        run_summary_generation,
        SessionLocal,
        task_id,
        after_success=trigger_after_summary,
    )
    return SummaryOut(status="pending")
