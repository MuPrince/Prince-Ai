from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import LearningRecord, RecordType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_auto_record(
    session: Session, task_id: int, started_at: datetime | None = None
) -> LearningRecord:
    record = LearningRecord(
        task_id=task_id,
        record_type=RecordType.auto,
        started_at=started_at or _utcnow(),
    )
    session.add(record)
    session.commit()
    return record


def create_manual_record(
    session: Session,
    task_id: int,
    started_at: datetime,
    content: str = "",
) -> LearningRecord:
    record = LearningRecord(
        task_id=task_id,
        record_type=RecordType.manual,
        started_at=started_at,
        content=content,
    )
    session.add(record)
    session.commit()
    return record


def list_records_by_task(session: Session, task_id: int) -> list[LearningRecord]:
    return list(
        session.scalars(
            select(LearningRecord)
            .where(LearningRecord.task_id == task_id)
            .order_by(LearningRecord.started_at.desc())
        )
    )
