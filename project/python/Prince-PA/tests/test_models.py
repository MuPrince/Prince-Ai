from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.entities import Language, Task


def test_create_language_and_task(db_session):
    lang = Language(name="Python", sort_order=1)
    db_session.add(lang)
    db_session.flush()

    task = Task(language_id=lang.id, title="LangChain", description="入门")
    db_session.add(task)
    db_session.commit()

    saved = db_session.scalar(select(Task).where(Task.title == "LangChain"))
    assert saved is not None
    assert saved.language.name == "Python"
    assert saved.status.value == "todo"
    assert saved.summary_status.value == "pending"


def test_same_language_title_unique(db_session):
    lang = Language(name="Python", sort_order=1)
    db_session.add(lang)
    db_session.flush()
    db_session.add(Task(language_id=lang.id, title="LangChain", description="first"))
    db_session.commit()
    db_session.add(Task(language_id=lang.id, title="LangChain", description="again"))
    try:
        db_session.commit()
    except IntegrityError:
        db_session.rollback()
        return
    raise AssertionError("Expected IntegrityError for duplicate (language_id, title)")
