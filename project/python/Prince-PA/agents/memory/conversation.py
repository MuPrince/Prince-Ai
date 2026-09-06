from sqlalchemy import select
from sqlalchemy.orm import Session
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.models.entities import ChatMessage, MessageRole


def load_langchain_history(db: Session, session_id: int) -> list[BaseMessage]:
    rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    result: list[BaseMessage] = []
    for row in rows:
        content = row.content or ""
        if row.role == MessageRole.user:
            result.append(HumanMessage(content=content))
        elif row.role == MessageRole.assistant:
            result.append(AIMessage(content=content))
        elif row.role == MessageRole.system:
            result.append(SystemMessage(content=content))
    return result
