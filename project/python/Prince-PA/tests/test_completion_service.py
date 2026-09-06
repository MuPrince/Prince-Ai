from sqlalchemy import select

from app.models.entities import SummaryStatus, Task, TaskStatus
from app.services.completion_service import run_summary_generation
from app.services.note_service import write_note
from app.services.task_service import create_task, set_status


def test_run_summary_generation_success(db_session):
    task = create_task(db_session, "Python", "总结任务", "")
    write_note(db_session, task.id, "# 学到的内容\nLangChain 工具调用")
    set_status(db_session, task.id, TaskStatus.completed)

    def fake_generator(task, note_content, model=None):
        return f"# {task.title}-总结\n\n{note_content}"

    run_summary_generation(lambda: db_session, task.id, generator=fake_generator)

    task = db_session.scalar(select(Task).where(Task.id == task.id))
    assert task.summary_status == SummaryStatus.success
    assert task.summary_error is None
    assert any(row.rel_path.endswith("-总结.md") for row in task.note_files)


def test_run_summary_generation_failure(db_session):
    task = create_task(db_session, "Python", "失败任务", "")
    set_status(db_session, task.id, TaskStatus.completed)

    def boom_generator(task, note_content, model=None):
        raise RuntimeError("模型不可用")

    run_summary_generation(lambda: db_session, task.id, generator=boom_generator)

    task = db_session.scalar(select(Task).where(Task.id == task.id))
    assert task.summary_status == SummaryStatus.failed
    assert "模型不可用" in task.summary_error
