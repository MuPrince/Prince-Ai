from agents.memory.conversation import load_langchain_history
from agents.memory.profile import (
    confirm_preference,
    dismiss_preference,
    list_pending,
)
from app.models.entities import MessageRole, PreferenceStatus, UserPreference
from app.services.chat_service import create_message, create_session


def test_load_langchain_history(db_session):
    session = create_session(db_session)
    create_message(db_session, session.id, MessageRole.user, "你好")
    create_message(db_session, session.id, MessageRole.assistant, "你好")
    history = load_langchain_history(db_session, session.id)
    assert history[0].type == "human"
    assert history[1].type == "ai"


def test_preference_confirm_and_dismiss(db_session):
    pref = UserPreference(
        user_id="local",
        dimension="summary_style",
        value="详细",
        source="auto",
        status=PreferenceStatus.pending,
        confidence=0.8,
    )
    db_session.add(pref)
    db_session.commit()

    assert len(list_pending(db_session, "local")) == 1
    confirmed = confirm_preference(db_session, pref.id)
    assert confirmed.status == PreferenceStatus.confirmed
    dismissed = dismiss_preference(db_session, pref.id)
    assert dismissed.status == PreferenceStatus.dismissed
