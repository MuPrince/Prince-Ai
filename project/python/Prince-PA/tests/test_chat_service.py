from app.models.entities import MessageRole
from app.services.chat_service import (
    create_message,
    create_session,
    list_messages,
    list_sessions,
)


def test_create_session_and_message(db_session):
    session = create_session(db_session)
    assert session.title == "新会话"

    create_message(db_session, session.id, MessageRole.user, "帮我加任务")
    create_message(db_session, session.id, MessageRole.assistant, "好的")

    rows = list_messages(db_session, session.id)
    assert [m.role.value for m in rows] == ["user", "assistant"]
    assert len(list_sessions(db_session)) == 1
