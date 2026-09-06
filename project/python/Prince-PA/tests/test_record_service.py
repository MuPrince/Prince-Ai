from datetime import datetime, timezone

from app.models.entities import RecordType
from app.services.record_service import (
    create_auto_record,
    create_manual_record,
    list_records_by_task,
)
from app.services.task_service import create_task


def test_auto_record_uses_now(db_session):
    task = create_task(db_session, "Python", "T1", "")
    record = create_auto_record(db_session, task.id)
    assert record.record_type == RecordType.auto
    assert record.started_at is not None


def test_manual_record_with_given_start(db_session):
    task = create_task(db_session, "Python", "T2", "")
    started = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)
    record = create_manual_record(db_session, task.id, started, content="心得")
    assert record.content == "心得"
    assert record.started_at == started


def test_list_records_by_task(db_session):
    task = create_task(db_session, "Python", "T3", "")
    create_auto_record(db_session, task.id)
    create_manual_record(
        db_session, task.id, datetime(2026, 9, 6, 9, 0, tzinfo=timezone.utc), "m"
    )
    rows = list_records_by_task(db_session, task.id)
    assert len(rows) == 2
