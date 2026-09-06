from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import ChatMessage, ChatSession, MessageRole, utcnow


def create_session(db: Session) -> ChatSession:
    session = ChatSession()
    db.add(session)
    db.commit()
    return session


def list_sessions(db: Session) -> list[ChatSession]:
    return list(db.scalars(select(ChatSession).order_by(ChatSession.updated_at.desc())))


def get_session(db: Session, session_id: int) -> ChatSession:
    session = db.get(ChatSession, session_id)
    if session is None:
        raise LookupError(f"会话不存在：{session_id}")
    return session


def create_message(
    db: Session,
    session_id: int,
    role: MessageRole,
    content: str | None,
    tool_name: str | None = None,
    tool_input_json: str | None = None,
) -> ChatMessage:
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        tool_name=tool_name,
        tool_input_json=tool_input_json,
    )
    db.add(message)
    get_session(db, session_id).updated_at = utcnow()
    db.commit()
    return message


def list_messages(db: Session, session_id: int, limit: int = 100) -> list[ChatMessage]:
    return list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
    )
