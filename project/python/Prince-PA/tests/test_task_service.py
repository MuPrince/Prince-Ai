from sqlalchemy import select

import pytest

from app.models.entities import Language, Task, TaskStatus
from app.services.language_service import get_or_create_language
from app.services.task_service import (
    create_task,
    list_tasks,
    set_status,
    update_task,
)


def test_create_task_creates_language_auto(db_session):
    task = create_task(db_session, "Python", "LangChain", "学工具")
    assert task.language.name == "Python"
    assert task.status == TaskStatus.todo


def test_create_duplicate_task_rejected(db_session):
    create_task(db_session, "Python", "LangChain", "")
    with pytest.raises(ValueError):
        create_task(db_session, "Python", "LangChain", "重复")


def test_list_tasks_filter_by_language_and_status(db_session):
    create_task(db_session, "Python", "P1", "")
    create_task(db_session, "Java", "J1", "")
    p1 = db_session.scalar(select(Task).where(Task.title == "P1"))
    set_status(db_session, p1.id, TaskStatus.in_progress)

    rows = list_tasks(db_session, language="Python", status=None, keyword=None)
    assert [t.title for t in rows] == ["P1"]


def test_update_task_moves_files(db_session):
    task = create_task(db_session, "Python", "旧主题", "")
    from app.services.note_service import write_note

    write_note(db_session, task.id, "body")
    get_or_create_language(db_session, "Java")
    updated = update_task(
        db_session, task.id, language_name="Java", title="新主题", description="d"
    )
    assert updated.language.name == "Java"
    assert updated.description == "d"
    old = db_session.scalar(select(Task).where(Task.id == task.id))
    assert old.note_files[0].rel_path == "Java/新主题.md"


def test_complete_task_sets_summary_pending(db_session):
    task = create_task(db_session, "Python", "Done", "")
    set_status(db_session, task.id, TaskStatus.completed)
    task = db_session.scalar(select(Task).where(Task.id == task.id))
    assert task.status == TaskStatus.completed
    assert task.completed_at is not None
    assert task.summary_status.value == "pending"
