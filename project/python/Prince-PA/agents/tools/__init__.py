from typing import Callable

from langchain_core.tools import BaseTool
from sqlalchemy.orm import Session

from agents.tools.language_tools import build_language_tools
from agents.tools.note_tools import build_note_tools
from agents.tools.task_tools import build_task_tools


def build_all_tools(session_factory: Callable[[], Session]) -> list[BaseTool]:
    return [
        *build_language_tools(session_factory),
        *build_task_tools(session_factory),
        *build_note_tools(session_factory),
    ]
