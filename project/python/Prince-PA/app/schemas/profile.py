from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import PreferenceStatus, SourceType


class PreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dimension: str
    value: str
    source: SourceType
    status: PreferenceStatus
    confidence: float
    evidence: str | None = None
    updated_at: datetime


class ProfileSnapshotOut(BaseModel):
    profile: dict
    pending: list[PreferenceOut]
