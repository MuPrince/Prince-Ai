from typing import Callable

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.services.completion_service import run_summary_generation
from app.services.note_service import init_note_file, read_note_content


def build_note_tools(session_factory: Callable[[], Session]):
    @tool
    def init_note_tool(task_id: int) -> str:
        """为任务初始化一份空的笔记文件（不覆盖已有内容）。"""
        with session_factory() as session:
            existing = read_note_content(session, task_id)
            if existing:
                return "笔记文件已存在，未做修改"
            row = init_note_file(session, task_id)
        return f"已创建笔记文件：{row.rel_path}"

    @tool
    def read_note_tool(task_id: int) -> str:
        """读取任务笔记正文，供总结或起草参考。"""
        with session_factory() as session:
            content = read_note_content(session, task_id)
        return content if content else "（笔记为空）"

    @tool
    def draft_note_tool(task_id: int, requirements: str) -> str:
        """读取任务笔记素材并返回起草要求；Agent 结合素材在聊天中起草，不写入文件。"""
        with session_factory() as session:
            content = read_note_content(session, task_id)
        return f"笔记素材：\n{content}\n\n起草要求：{requirements}"

    @tool
    def summarize_task_tool(task_id: int) -> str:
        """按用户要求生成或更新某任务的总结文件。"""
        run_summary_generation(session_factory, task_id)
        return "总结生成任务已执行，请查看任务详情中的总结。"

    return [init_note_tool, read_note_tool, draft_note_tool, summarize_task_tool]
