from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.entities import Language, SummaryStatus, Task, TaskStatus
from app.services.language_service import get_or_create_language
from app.services.note_service import move_task_files, validate_component


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _task_query():
    return select(Task).options(joinedload(Task.language), joinedload(Task.note_files))


def _get_task(session: Session, task_id: int) -> Task:
    task = session.scalar(_task_query().where(Task.id == task_id))
    if task is None:
        raise LookupError(f"任务不存在：{task_id}")
    return task


def list_tasks(
    session: Session,
    language: str | None = None,
    status: TaskStatus | None = None,
    keyword: str | None = None,
) -> list[Task]:
    query = _task_query().order_by(Task.created_at.desc())
    if language:
        query = query.join(Language).where(Language.name == language)
    if status is not None:
        query = query.where(Task.status == status)
    if keyword:
        like = f"%{keyword}%"
        query = query.where(or_(Task.title.like(like), Task.description.like(like)))
    return list(session.scalars(query).unique())


def create_task(
    session: Session, language_name: str, title: str, description: str = ""
) -> Task:
    language = get_or_create_language(session, language_name)
    clean_title = validate_component(title, "主题")
    exists = session.scalar(
        select(Task.id).where(
            Task.language_id == language.id, Task.title == clean_title
        )
    )
    if exists is not None:
        raise ValueError(f"该语言下已存在主题：{clean_title}")
    task = Task(language_id=language.id, title=clean_title, description=description)
    session.add(task)
    session.commit()
    return _get_task(session, task.id)


def update_task(
    session: Session,
    task_id: int,
    language_name: str | None = None,
    title: str | None = None,
    description: str | None = None,
    status: TaskStatus | None = None,
) -> Task:
    task = _get_task(session, task_id)
    old_language = task.language.name
    old_title = task.title

    if language_name is not None and language_name.strip() != old_language:
        new_lang = get_or_create_language(session, language_name)
        task.language_id = new_lang.id
    if title is not None:
        clean_title = validate_component(title, "主题")
        if clean_title != old_title:
            clash = session.scalar(
                select(Task.id).where(
                    Task.language_id == task.language_id,
                    Task.title == clean_title,
                    Task.id != task_id,
                )
            )
            if clash is not None:
                raise ValueError(f"该语言下已存在主题：{clean_title}")
            task.title = clean_title
    if description is not None:
        task.description = description
    if status is not None:
        task.status = status
        if status == TaskStatus.completed and task.completed_at is None:
            task.completed_at = _utcnow()
            task.summary_status = SummaryStatus.pending
            task.summary_error = None
    session.flush()
    rename_needed = (
        language_name is not None and language_name.strip() != old_language
    ) or (title is not None and title.strip() != old_title)
    if rename_needed:
        move_task_files(session, task_id, old_language, old_title)
    session.expire(task, ["note_files"])
    session.commit()
    return _get_task(session, task_id)


def set_status(session: Session, task_id: int, status: TaskStatus) -> Task:
    return update_task(session, task_id, status=status)
