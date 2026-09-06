from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import SummaryStatus, TaskStatus


class LanguageCreate(BaseModel):
    name: str


class LanguageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class TaskCreate(BaseModel):
    language: str
    title: str
    description: str = ""


class TaskUpdate(BaseModel):
    language: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    language: str
    title: str
    description: str
    status: TaskStatus
    summary_status: SummaryStatus
    summary_error: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
