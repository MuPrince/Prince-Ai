from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from agents.memory.profile import trigger_after_summary
from app.core.database import SessionLocal, get_db
from app.models.entities import Task as TaskModel
from app.models.entities import TaskStatus
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate
from app.services.completion_service import run_summary_generation
from app.services.record_service import create_auto_record
from app.services.task_service import (
    create_task,
    list_tasks,
    set_status,
    update_task,
)

router = APIRouter(prefix="/api", tags=["tasks"])


def _get_task_or_404(session: Session, task_id: int) -> TaskModel:
    task = session.scalar(select(TaskModel).where(TaskModel.id == task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


def task_to_out(task: TaskModel) -> TaskOut:
    return TaskOut(
        id=task.id,
        language=task.language.name,
        title=task.title,
        description=task.description,
        status=task.status,
        summary_status=task.summary_status,
        summary_error=task.summary_error,
        completed_at=task.completed_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get("/tasks", response_model=list[TaskOut])
def api_list_tasks(
    language: str | None = None,
    status: TaskStatus | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
):
    return [task_to_out(t) for t in list_tasks(db, language, status, keyword)]


@router.post("/tasks", response_model=TaskOut, status_code=201)
def api_create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    try:
        task = create_task(db, payload.language, payload.title, payload.description)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return task_to_out(task)


@router.get("/tasks/{task_id}", response_model=TaskOut)
def api_get_task(task_id: int, db: Session = Depends(get_db)):
    return task_to_out(_get_task_or_404(db, task_id))


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def api_update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    try:
        task = update_task(
            db,
            task_id,
            language_name=payload.language,
            title=payload.title,
            description=payload.description,
            status=payload.status,
        )
    except (ValueError, LookupError) as exc:
        raise HTTPException(
            status_code=400 if isinstance(exc, ValueError) else 404, detail=str(exc)
        )
    return task_to_out(task)


@router.post("/tasks/{task_id}/start", response_model=TaskOut)
def api_start_task(task_id: int, db: Session = Depends(get_db)):
    task = _get_task_or_404(db, task_id)
    if task.status == TaskStatus.completed:
        task.completed_at = None
        db.commit()
    task = set_status(db, task_id, TaskStatus.in_progress)
    create_auto_record(db, task_id)
    return task_to_out(task)


@router.post("/tasks/{task_id}/complete", response_model=TaskOut)
def api_complete_task(
    task_id: int,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    task = _get_task_or_404(db, task_id)
    if task.status != TaskStatus.completed:
        task = set_status(db, task_id, TaskStatus.completed)
        background.add_task(
            run_summary_generation,
            SessionLocal,
            task_id,
            after_success=trigger_after_summary,
        )
    return task_to_out(task)
