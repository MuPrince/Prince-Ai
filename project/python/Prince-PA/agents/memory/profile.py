import json
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from agents.memory.extractor import extract_preferences
from app.core.config import settings
from app.models.entities import (
    ChatMessage,
    Language,
    MessageRole,
    PreferenceStatus,
    SourceType,
    SummaryStatus,
    Task,
    UserPreference,
    UserProfile,
)
from app.services.note_service import read_note_content, read_summary_content

USER_ID = "local"
DIMENSIONS = {"learning_focus", "learning_style", "summary_style", "response_style"}


def _add_pending(session: Session, user_id: str, item: dict) -> UserPreference:
    dimension = item.get("dimension")
    if dimension not in DIMENSIONS:
        raise ValueError(f"未知偏好维度：{dimension}")
    row = session.scalar(
        select(UserPreference).where(
            UserPreference.user_id == user_id,
            UserPreference.dimension == dimension,
            UserPreference.status == PreferenceStatus.pending,
        )
    )
    if row is None:
        row = UserPreference(user_id=user_id, dimension=dimension)
        session.add(row)
    row.value = str(item.get("value", ""))
    row.source = SourceType(item.get("source", "auto"))
    row.confidence = float(item.get("confidence", 0.5))
    row.evidence = item.get("evidence")
    session.commit()
    return row


def list_pending(session: Session, user_id: str = USER_ID) -> list[UserPreference]:
    return list(
        session.scalars(
            select(UserPreference).where(
                UserPreference.user_id == user_id,
                UserPreference.status == PreferenceStatus.pending,
            )
        )
    )


def confirm_preference(
    session: Session, preference_id: int, user_id: str = USER_ID
) -> UserPreference:
    row = session.get(UserPreference, preference_id)
    if row is None or row.user_id != user_id:
        raise LookupError("偏好项不存在")
    row.status = PreferenceStatus.confirmed
    session.commit()
    session.refresh(row)
    snapshot(session, user_id)
    return row


def dismiss_preference(
    session: Session, preference_id: int, user_id: str = USER_ID
) -> UserPreference:
    row = session.get(UserPreference, preference_id)
    if row is None or row.user_id != user_id:
        raise LookupError("偏好项不存在")
    row.status = PreferenceStatus.dismissed
    session.commit()
    return row


def snapshot(session: Session, user_id: str = USER_ID) -> UserProfile:
    confirmed = session.scalars(
        select(UserPreference).where(
            UserPreference.user_id == user_id,
            UserPreference.status == PreferenceStatus.confirmed,
        )
    ).all()
    payload = {
        row.dimension: {"value": row.value, "confirmed_at": row.updated_at.isoformat()}
        for row in confirmed
    }
    profile = UserProfile(
        user_id=user_id,
        profile_json=json.dumps(payload, ensure_ascii=False),
        source=SourceType.auto,
    )
    session.add(profile)
    session.commit()
    return profile


def latest_profile(session: Session, user_id: str = USER_ID) -> dict:
    row = session.scalar(
        select(UserProfile)
        .where(UserProfile.user_id == user_id)
        .order_by(UserProfile.id.desc())
        .limit(1)
    )
    if row is None:
        return {}
    return json.loads(row.profile_json)


def _recent_chat_snippets(session: Session, limit: int = 10) -> list[str]:
    rows = session.scalars(
        select(ChatMessage)
        .where(ChatMessage.role == MessageRole.user)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    return [row.content or "" for row in rows]


def _extract_from_materials(
    session: Session,
    language_name: str,
    title: str,
    note_content: str,
    summary_content: str,
    user_id: str,
    source: SourceType,
) -> int:
    if not settings.deepseek_api_key:
        return 0
    task = Task(language=Language(name=language_name), title=title)
    items = extract_preferences(
        task,
        note_content,
        summary_content,
        _recent_chat_snippets(session),
    )
    count = 0
    for item in items:
        try:
            item["source"] = source.value
            _add_pending(session, user_id, item)
            count += 1
        except ValueError:
            continue
    return count


def trigger_after_summary(
    session_factory: Callable[[], Session], task_id: int, user_id: str = USER_ID
) -> None:
    with session_factory() as session:
        task = session.get(Task, task_id)
        if task is None or task.summary_status != SummaryStatus.success:
            return
        _extract_from_materials(
            session,
            task.language.name,
            task.title,
            read_note_content(session, task_id),
            read_summary_content(session, task_id) or "",
            user_id,
            SourceType.auto,
        )


def trigger_manual_extract(
    session_factory: Callable[[], Session], user_id: str = USER_ID
) -> int:
    with session_factory() as session:
        task = session.scalar(
            select(Task)
            .where(Task.summary_status == SummaryStatus.success)
            .order_by(Task.completed_at.desc())
            .limit(1)
        )
        if task is None:
            return 0
        return _extract_from_materials(
            session,
            task.language.name,
            task.title,
            read_note_content(session, task.id),
            read_summary_content(session, task.id) or "",
            user_id,
            SourceType.manual,
        )
