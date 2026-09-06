from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Language
from app.services.note_service import validate_component


def get_or_create_language(session: Session, name: str) -> Language:
    clean = validate_component(name, "语言")
    lang = session.scalar(select(Language).where(Language.name == clean))
    if lang is None:
        lang = Language(name=clean)
        session.add(lang)
        session.flush()
    return lang


def list_languages(session: Session) -> list[Language]:
    return list(session.scalars(select(Language).order_by(Language.sort_order, Language.id)))
