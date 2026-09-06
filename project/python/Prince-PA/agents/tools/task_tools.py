import json
from typing import Callable

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from agents.memory.profile import trigger_after_summary
from app.models.entities import TaskStatus
from app.services.completion_service import run_summary_generation
from app.services.task_service import create_task, list_tasks, set_status, update_task


def build_task_tools(session_factory: Callable[[], Session]):
    @tool
    def create_task_tool(language: str, title: str, description: str = "") -> str:
        """新增一个学习任务；语言不存在时自动创建语言分类。"""
        with session_factory() as session:
            task = create_task(session, language, title, description)
        return json.dumps(
            {"id": task.id, "language": task.language.name, "title": task.title},
            ensure_ascii=False,
        )

    @tool
    def update_task_tool(
        task_id: int,
        language: str | None = None,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
    ) -> str:
        """更新任务；status 只能是 todo/in_progress/completed。"""
        mapped = TaskStatus(status) if status else None
        with session_factory() as session:
            task = update_task(session, task_id, language, title, description, mapped)
        return json.dumps(
            {"id": task.id, "title": task.title, "status": task.status.value},
            ensure_ascii=False,
        )

    @tool
    def list_tasks_tool(
        language: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
    ) -> str:
        """按语言/状态/关键词查询学习任务，用于向用户汇报进度。"""
        mapped = TaskStatus(status) if status else None
        with session_factory() as session:
            rows = list_tasks(session, language, mapped, keyword)
        return json.dumps(
            [
                {
                    "id": t.id,
                    "language": t.language.name,
                    "title": t.title,
                    "status": t.status.value,
                }
                for t in rows
            ],
            ensure_ascii=False,
        )

    @tool
    def complete_task_tool(task_id: int) -> str:
        """标记任务完成并同步生成总结文件。"""
        with session_factory() as session:
            task = set_status(session, task_id, TaskStatus.completed)
        run_summary_generation(
            session_factory, task_id, after_success=trigger_after_summary
        )
        return f"任务「{task.title}」已完成，总结已生成或记录失败状态。"

    return [create_task_tool, update_task_tool, list_tasks_tool, complete_task_tool]
