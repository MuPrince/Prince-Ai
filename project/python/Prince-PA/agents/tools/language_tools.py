from typing import Callable

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.services.language_service import list_languages


def build_language_tools(session_factory: Callable[[], Session]):
    @tool
    def list_languages_tool() -> str:
        """列出系统已有的编程语言分类。"""
        with session_factory() as session:
            rows = list_languages(session)
        return "\n".join(f"- {row.name}" for row in rows) or "暂无语言分类"

    return [list_languages_tool]
