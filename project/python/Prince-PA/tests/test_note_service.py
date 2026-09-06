from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.entities import Language, NoteFile, NoteKind, Task
from app.services.note_service import (
    init_note_file,
    move_task_files,
    read_note_content,
    read_summary_content,
    validate_component,
    write_note,
    write_summary,
)


def _make_task(db_session):
    lang = Language(name="Python", sort_order=1)
    db_session.add(lang)
    db_session.flush()
    task = Task(language_id=lang.id, title="LangChain", description="")
    db_session.add(task)
    db_session.flush()
    return task


def test_validate_component_rejects_path_characters():
    with pytest.raises(ValueError):
        validate_component("a/b", "主题")
    assert validate_component("LangChain", "主题") == "LangChain"


def test_write_and_read_note(db_session):
    task = _make_task(db_session)
    note = write_note(db_session, task.id, "# 标题\n正文")

    note_path = settings.data_dir / "notes" / note.rel_path
    assert note_path.read_text(encoding="utf-8") == "# 标题\n正文"
    assert read_note_content(db_session, task.id) == "# 标题\n正文"


def test_init_note_file_creates_empty_file(db_session):
    task = _make_task(db_session)
    note = init_note_file(db_session, task.id)
    note_path = settings.data_dir / "notes" / note.rel_path
    assert note_path.exists()
    assert note.kind == NoteKind.note


def test_summary_file_round_trip(db_session):
    task = _make_task(db_session)
    row = write_summary(db_session, task.id, "# 总结")
    assert row.rel_path.endswith("-总结.md")
    assert read_summary_content(db_session, task.id) == "# 总结"


def test_move_task_files(db_session):
    task = _make_task(db_session)
    write_note(db_session, task.id, "note-body")
    write_summary(db_session, task.id, "summary-body")
    old_rel = "Python/LangChain.md"
    old_path = settings.data_dir / "notes" / old_rel

    new_lang = Language(name="Java", sort_order=2)
    db_session.add(new_lang)
    db_session.flush()
    task.language_id = new_lang.id
    task.title = "LangChain4j"
    db_session.flush()

    move_task_files(db_session, task.id, "Python", "LangChain")
    db_session.commit()

    assert not old_path.exists()
    rows = db_session.scalars(select(NoteFile).where(NoteFile.task_id == task.id)).all()
    assert {Path(r.rel_path).parent.name for r in rows} == {"Java"}
