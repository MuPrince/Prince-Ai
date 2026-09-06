from pydantic import BaseModel


class NoteContent(BaseModel):
    content: str


class NoteOut(BaseModel):
    content: str
    rel_path: str | None = None


class SummaryOut(BaseModel):
    status: str
    content: str | None = None
    error: str | None = None
