from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import RecordType


class RecordCreate(BaseModel):
    started_at: datetime
    content: str = ""

    @field_validator("started_at")
    @classmethod
    def ensure_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.now().astimezone().tzinfo)
        return value


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    record_type: RecordType
    content: str
    started_at: datetime
    created_at: datetime
