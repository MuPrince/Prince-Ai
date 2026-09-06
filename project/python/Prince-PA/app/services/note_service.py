from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.entities import NoteFile, NoteKind, Task

_INVALID_CHARS = set('\\/:*?"<>|')


def validate_component(value: str, label: str) -> str:
    cleaned = value.strip()
    if not cleaned or cleaned in {".", ".."}:
        raise ValueError(f"{label}不能为空")
    if any(ch in _INVALID_CHARS or ord(ch) < 32 for ch in cleaned):
        raise ValueError(f"{label}包含非法字符（不允许 \\ / : * ? \" < > |）")
    return cleaned


def _task_with_language(session: Session, task_id: int) -> Task:
    task = session.scalar(
        select(Task).where(Task.id == task_id).options(joinedload(Task.language))
    )
    if task is None:
        raise LookupError(f"任务不存在：{task_id}")
    return task


def note_rel_path(task: Task) -> str:
    language = validate_component(task.language.name, "语言")
    title = validate_component(task.title, "主题")
    return f"{language}/{title}.md"


def summary_rel_path(task: Task) -> str:
    language = validate_component(task.language.name, "语言")
    title = validate_component(task.title, "主题")
    return f"{language}/{title}-总结.md"


def _write_file(rel_path: str, content: str) -> Path:
    full = settings.data_dir / "notes" / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    temp = full.with_suffix(full.suffix + ".tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(full)
    return full


def _row_for(session: Session, task_id: int, kind: NoteKind, rel_path: str) -> NoteFile:
    row = session.scalar(
        select(NoteFile).where(NoteFile.task_id == task_id, NoteFile.kind == kind)
    )
    if row is None:
        row = NoteFile(task_id=task_id, kind=kind, rel_path=rel_path)
        session.add(row)
    else:
        row.rel_path = rel_path
    return row


def _sync_relationship(task: Task, row: NoteFile) -> None:
    if "note_files" in task.__dict__ and row not in task.note_files:
        task.note_files.append(row)


def init_note_file(session: Session, task_id: int) -> NoteFile:
    task = _task_with_language(session, task_id)
    rel = note_rel_path(task)
    full = settings.data_dir / "notes" / rel
    if not full.exists():
        _write_file(rel, "")
    row = _row_for(session, task_id, NoteKind.note, rel)
    _sync_relationship(task, row)
    session.commit()
    return row


def read_note_content(session: Session, task_id: int) -> str:
    task = _task_with_language(session, task_id)
    path = settings.data_dir / "notes" / note_rel_path(task)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_note(session: Session, task_id: int, content: str) -> NoteFile:
    task = _task_with_language(session, task_id)
    rel = note_rel_path(task)
    _write_file(rel, content)
    row = _row_for(session, task_id, NoteKind.note, rel)
    _sync_relationship(task, row)
    session.commit()
    return row


def read_summary_content(session: Session, task_id: int) -> str | None:
    task = _task_with_language(session, task_id)
    path = settings.data_dir / "notes" / summary_rel_path(task)
    return path.read_text(encoding="utf-8") if path.exists() else None


def write_summary(session: Session, task_id: int, content: str) -> NoteFile:
    task = _task_with_language(session, task_id)
    rel = summary_rel_path(task)
    _write_file(rel, content)
    row = _row_for(session, task_id, NoteKind.summary, rel)
    _sync_relationship(task, row)
    session.commit()
    return row


def move_task_files(
    session: Session, task_id: int, old_language: str, old_title: str
) -> list[NoteFile]:
    task = _task_with_language(session, task_id)
    session.flush()
    session.expire(task, ["language", "title"])
    old_lang = validate_component(old_language, "原语言")
    old_name = validate_component(old_title, "原主题")
    moves = {
        NoteKind.note: f"{old_lang}/{old_name}.md",
        NoteKind.summary: f"{old_lang}/{old_name}-总结.md",
    }
    new_paths = {NoteKind.note: note_rel_path(task), NoteKind.summary: summary_rel_path(task)}
    for kind in (NoteKind.note, NoteKind.summary):
        old_full = settings.data_dir / "notes" / moves[kind]
        if old_full.exists():
            target = settings.data_dir / "notes" / new_paths[kind]
            target.parent.mkdir(parents=True, exist_ok=True)
            old_full.replace(target)
    rows = []
    for kind in (NoteKind.note, NoteKind.summary):
        row = session.scalar(
            select(NoteFile).where(NoteFile.task_id == task_id, NoteFile.kind == kind)
        )
        if row is not None:
            row.rel_path = new_paths[kind]
            rows.append(row)
    session.commit()
    return rows
