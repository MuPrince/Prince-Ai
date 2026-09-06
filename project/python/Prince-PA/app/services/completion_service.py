from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from agents.summarizer import generate_summary
from app.models.entities import SummaryStatus, Task
from app.services.note_service import read_note_content, write_summary


def run_summary_generation(
    session_factory: Callable[[], Session],
    task_id: int,
    generator: Callable[..., str] | None = None,
    after_success: Callable[[Callable[[], Session], int], None] | None = None,
) -> None:
    generator = generator or generate_summary
    with session_factory() as session:
        task = session.scalar(select(Task).where(Task.id == task_id))
        if task is None:
            return
        try:
            note_content = read_note_content(session, task_id)
            content = generator(task, note_content)
            write_summary(session, task_id, content)
            task.summary_status = SummaryStatus.success
            task.summary_error = None
            session.commit()
            if after_success is not None:
                after_success(session_factory, task_id)
        except Exception as exc:  # noqa: BLE001 - 后台任务必须兜底
            task = session.scalar(select(Task).where(Task.id == task_id))
            if task is not None:
                task.summary_status = SummaryStatus.failed
                task.summary_error = str(exc)
                session.commit()
