from enum import Enum


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    completed = "completed"


class SummaryStatus(str, Enum):
    pending = "pending"
    success = "success"
    failed = "failed"


class NoteKind(str, Enum):
    note = "note"
    summary = "summary"


class RecordType(str, Enum):
    auto = "auto"
    manual = "manual"


class SourceType(str, Enum):
    auto = "auto"
    manual = "manual"


class PreferenceStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    dismissed = "dismissed"


class MessageRole(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"
