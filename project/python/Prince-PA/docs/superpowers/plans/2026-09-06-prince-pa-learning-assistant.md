# Prince-PA 个人 Agent 开发学习助理 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 本地运行一个 FastAPI + Vue 3 的个人学习助理，支持语言分类任务看板、右侧常驻聊天 Agent、Markdown 笔记编辑、任务完成自动总结、学习记录与用户画像偏好存储。

**Architecture:** FastAPI 提供 REST API 并托管 `web/dist`；SQLite 存结构化数据，真实 `.md` 文件存笔记/总结；LangChain + DeepSeek 提供工具调用 Agent；`agents/memory/` 管理会话记忆与画像提炼；Vue 3 SPA 实现四块页面能力。

**Tech Stack:** Python 3.10+、FastAPI、SQLAlchemy 2.0、Pydantic v2、pydantic-settings、sse 协议（fetch 解析）、LangChain + langchain-deepseek、pytest；Node 18+、Vue 3 + TypeScript + Vite + Element Plus + Pinia + Vue Router + axios + md-editor-v3 + Vitest。

**Spec:** [设计文档](../specs/2026-09-06-prince-pa-learning-assistant-design.md)
**PRD:** [产品需求文档](../../../PRD.md)

## Global Constraints

- Python 3.10+，Windows PowerShell 为主；后端默认 `http://127.0.0.1:8002`。
- SQLAlchemy 2.0 ORM + SQLite；Pydantic v2 schema；统一 UTF-8。
- `.env` 只含配置，`DEEPSEEK_API_KEY` 由用户自管；`.env`、`data/`、`web/node_modules`、`web/dist` 不入库。
- 笔记路径 `data/notes/<语言>/<主题>.md`；总结路径 `data/notes/<语言>/<主题>-总结.md`；同一语言主题唯一。
- 任务状态枚举 `todo/in_progress/completed`；总结状态 `pending/success/failed`；文件 kind `note/summary`；记录类型 `auto/manual`。
- Agent 工具能力固定：增改任务、查询汇报、标记完成、初始化笔记文件、读取笔记、起草内容（不改正文）、生成总结、查询语言。
- Agent 不创建/不代写学习记录；自动学习记录只由“开始学习”动作产生。
- 画像/偏好提取仅任务完成+总结成功后自动一次或手动触发；结果为 `pending`，确认后 `confirmed`；本期不影响 Agent 行为。
- UI 中文；Vue 3 `<script setup lang="ts">`；主布局左筛选/中卡片/右聊天；仅笔记编辑页隐藏聊天。
- 每次任务结束时必须跑对应测试并提交；提交信息用中文，遵循仓库历史风格。
- 测试不得触碰真实 `data/`，通过环境变量 `PRINCE_PA_DATA_DIR` 指向临时目录。

## File Structure

后端（`Prince-PA/` 根）：

```text
requirements.txt
.env.example
.gitignore
app/
  main.py
  core/config.py
  core/database.py
  core/errors.py
  models/enums.py
  models/entities.py
  schemas/*.py
  services/language_service.py
  services/task_service.py
  services/note_service.py
  services/record_service.py
  services/completion_service.py
  services/profile_service.py
  api/deps.py
  api/languages.py
  api/tasks.py
  api/notes.py
  api/records.py
  api/summaries.py
  api/chat.py
  api/profile.py
agents/
  llm.py
  assistant.py
  summarizer.py
  memory/conversation.py
  memory/profile.py
  memory/extractor.py
  tools/__init__.py
  tools/language_tools.py
  tools/task_tools.py
  tools/note_tools.py
tests/
  conftest.py
  test_health.py
  test_models.py
  test_note_service.py
  test_task_service.py
  test_record_service.py
  test_summarizer.py
  test_completion_service.py
  test_api_tasks.py
  test_api_notes_records.py
  test_memory.py
  test_tools.py
  test_chat_api.py
```

前端（`Prince-PA/web/`）：

```text
web/package.json
web/vite.config.ts
web/.env.development
web/src/main.ts
web/src/App.vue
web/src/router/index.ts
web/src/utils/request.ts
web/src/utils/sse.ts
web/src/layouts/AppShell.vue
web/src/stores/task.ts
web/src/stores/chat.ts
web/src/stores/note.ts
web/src/stores/profile.ts
web/src/views/TaskBoard.vue
web/src/views/NoteEditor.vue
web/src/components/TaskCard.vue
web/src/components/TaskFilter.vue
web/src/components/TaskFormDialog.vue
web/src/components/TaskDetailDrawer.vue
web/src/components/ChatPanel.vue
web/src/components/ProfilePanel.vue
web/src/components/ResizableSplit.vue
web/tests/*.spec.ts
```

## Task Overview

1. 后端骨架、配置与健康检查
2. ORM 数据模型与会话工厂
3. 文件路径安全与笔记/总结读写服务
4. 语言与任务服务
5. 学习记录服务
6. 总结生成器（LangChain + DeepSeek，可 mock）
7. 任务完成流程与后台总结
8. 语言/任务 REST API
9. 笔记/总结/记录 REST API
10. 聊天会话与消息仓库
11. 会话记忆与用户画像/偏好服务
12. Agent 工具与对话编排（SSE 事件源）
13. 画像/偏好与聊天 REST API（SSE）
14. Vue 工程骨架与公共设施
15. 任务看板（卡片/筛选/手动新增/状态流转）
16. 任务详情与学习记录
17. Markdown 笔记编辑器（三栏+可拖拽+保存）
18. 聊天面板（流式对话）
19. 用户画像/偏好面板
20. FastAPI 托管前端与收尾文档

---

### Task 1: 后端骨架、配置与健康检查

**Files:**
- Create: `Prince-PA/requirements.txt`
- Create: `Prince-PA/.env.example`
- Create: `Prince-PA/.gitignore`
- Create: `Prince-PA/app/__init__.py`
- Create: `Prince-PA/app/core/__init__.py`
- Create: `Prince-PA/app/core/config.py`
- Create: `Prince-PA/app/main.py`
- Create: `Prince-PA/tests/conftest.py`
- Create: `Prince-PA/tests/test_health.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `app.core.config.Settings`：字段 `deepseek_api_key: str`、`data_dir: Path`、属性 `sqlite_url: str`；支持环境变量 `DEEPSEEK_API_KEY`、`PRINCE_PA_DATA_DIR`。
  - `app.main:app`：FastAPI 实例，路由 `/api/health`。

**Step 1: 写失败测试**

```python
# tests/conftest.py
import os

os.environ.setdefault("PRINCE_PA_DATA_DIR", "tests_tmp_data")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PRINCE_PA_DATA_DIR", str(tmp_path / "data"))
    from app.core.config import settings
    settings.data_dir = tmp_path / "data"
    return TestClient(app)
```

```python
# tests/test_health.py
def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

**Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_health.py -v`
Expected: 失败：`ModuleNotFoundError: app.core.config` 或 FastAPI 未安装。

**Step 3: 创建依赖与配置**

```text
# requirements.txt
fastapi>=0.115,<1.0
uvicorn[standard]>=0.30,<1.0
sqlalchemy>=2.0.30,<2.1
pydantic>=2.7,<3.0
pydantic-settings>=2.2,<3.0
sse-starlette>=2.0,<3.0
python-dotenv>=1.0,<2.0
langchain>=0.3,<1.0
langchain-core>=0.3,<1.0
langchain-deepseek>=0.1,<1.0
httpx>=0.27,<1.0
pytest>=8.2,<9.0
ruff>=0.6,<1.0
```

```text
# .env.example
DEEPSEEK_API_KEY=
```

```text
# .gitignore
.env
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
data/
web/node_modules/
web/dist/
```

```python
# app/core/config.py
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Prince-PA"
    deepseek_api_key: str = ""
    data_dir: Path = Path(__file__).resolve().parents[2] / "data"

    @property
    def sqlite_url(self) -> str:
        return f"sqlite:///{self.data_dir / 'app.db'}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

```python
# app/main.py
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Prince-PA", version="0.1.0")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
```

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_health.py -v`
Expected: PASS（1 passed）。

**Step 5: 提交**

```bash
git add requirements.txt .env.example .gitignore app tests
git commit -m "搭建Prince-PA后端骨架与健康检查"
```

---

### Task 2: ORM 数据模型与会话工厂

**Files:**
- Modify: `Prince-PA/tests/conftest.py`
- Create: `Prince-PA/app/core/database.py`
- Create: `Prince-PA/app/models/__init__.py`
- Create: `Prince-PA/app/models/enums.py`
- Create: `Prince-PA/app/models/entities.py`
- Create: `Prince-PA/tests/test_models.py`

**Interfaces:**
- Consumes: `app.core.config.settings.data_dir`、`settings.sqlite_url`。
- Produces:
  - `app.core.database.init_db()`：调用 `Base.metadata.create_all(engine)`。
  - `app.core.database.SessionLocal`、`app.core.database.get_db()`。
  - `app.models.enums`：`TaskStatus`、`SummaryStatus`、`NoteKind`、`RecordType`、`SourceType`、`PreferenceStatus`、`MessageRole`。
  - `app.models.entities`：`Base`、`Language`、`Task`、`NoteFile`、`LearningRecord`、`ChatSession`、`ChatMessage`、`UserProfile`、`UserPreference`。

**Step 1: 写失败测试**

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.entities import Base


def _make_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False, class_=Session
    )
    settings.data_dir = tmp_path / "data"
    return session_factory


@pytest.fixture()
def db_session(tmp_path) -> Session:
    session_factory = _make_session(tmp_path)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(tmp_path):
    session_factory = _make_session(tmp_path)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
```

```python
# tests/test_models.py
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
    db_session.add(Task(language_id=lang.id, title="LangChain", description="again"))
    try:
        db_session.commit()
    except IntegrityError:
        db_session.rollback()
        return
    raise AssertionError("Expected IntegrityError for duplicate (language_id, title)")
```

**Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_models.py -v`
Expected: FAIL（`app.models` 不存在）。

**Step 3: 创建枚举与实体**

```python
# app/models/enums.py
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
```

```python
# app/models/entities.py
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.models.enums import (
    NoteKind,
    PreferenceStatus,
    RecordType,
    SourceType,
    SummaryStatus,
    TaskStatus,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Language(Base):
    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    tasks: Mapped[list["Task"]] = relationship(back_populates="language")


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (UniqueConstraint("language_id", "title", name="uq_task_language_title"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.todo)
    summary_status: Mapped[SummaryStatus] = mapped_column(
        Enum(SummaryStatus), default=SummaryStatus.pending
    )
    summary_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    language: Mapped[Language] = relationship(back_populates="tasks")
    note_files: Mapped[list["NoteFile"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    records: Mapped[list["LearningRecord"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class NoteFile(Base):
    __tablename__ = "note_files"
    __table_args__ = (UniqueConstraint("task_id", "kind", name="uq_note_file_task_kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    kind: Mapped[NoteKind] = mapped_column(Enum(NoteKind))
    rel_path: Mapped[str] = mapped_column(String(500), unique=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    task: Mapped[Task] = relationship(back_populates="note_files")


class LearningRecord(Base):
    __tablename__ = "learning_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    record_type: Mapped[RecordType] = mapped_column(Enum(RecordType))
    content: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    task: Mapped[Task] = relationship(back_populates="records")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="新会话")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole))
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tool_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tool_input_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    session: Mapped[ChatSession] = relationship(back_populates="messages")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), index=True)
    profile_json: Mapped[str] = mapped_column(Text, default="{}")
    source: Mapped[SourceType] = mapped_column(Enum(SourceType))
    extracted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), index=True)
    dimension: Mapped[str] = mapped_column(String(50))
    value: Mapped[str] = mapped_column(Text)
    source: Mapped[SourceType] = mapped_column(Enum(SourceType))
    status: Mapped[PreferenceStatus] = mapped_column(
        Enum(PreferenceStatus), default=PreferenceStatus.pending
    )
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )
```

```python
# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.entities import Base

engine = create_engine(
    settings.sqlite_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, expire_on_commit=False, class_=Session
)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`app/models/__init__.py` 只导出实体：

```python
from app.models.entities import (
    Base,
    ChatMessage,
    ChatSession,
    Language,
    LearningRecord,
    NoteFile,
    Task,
    UserPreference,
    UserProfile,
)

__all__ = [
    "Base",
    "Language",
    "Task",
    "NoteFile",
    "LearningRecord",
    "ChatSession",
    "ChatMessage",
    "UserProfile",
    "UserPreference",
]
```

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_models.py -v`
Expected: PASS（2 passed）。

**Step 5: 提交**

```bash
git add app/core/database.py app/models tests/conftest.py tests/test_models.py .gitignore
git commit -m "新增ORM数据模型与会话工厂"
```

---

### Task 3: 文件路径安全与笔记/总结读写服务

**Files:**
- Create: `Prince-PA/app/services/__init__.py`
- Create: `Prince-PA/app/services/note_service.py`
- Create: `Prince-PA/tests/test_note_service.py`

**Interfaces:**
- Consumes: `Task`、`NoteFile`、`NoteKind`、`Session`、`utcnow()`。
- Produces:
  - `validate_component(value: str, label: str) -> str`：去空格、拒绝空/`.`/`..`、拒绝 `\ / : * ? " < > |` 与控制字符，返回原值。
  - `note_rel_path(task) -> str`、`summary_rel_path(task) -> str`（相对 `data/notes/` 的 posix 风格字符串）。
  - `init_note_file(session, task_id) -> NoteFile`
  - `read_note_content(session, task_id) -> str`
  - `write_note(session, task_id, content) -> NoteFile`
  - `read_summary_content(session, task_id) -> str | None`
  - `write_summary(session, task_id, content) -> NoteFile`
  - `move_task_files(session, task_id, old_language, old_title) -> list[NoteFile]`

**Step 1: 写失败测试**

```python
# tests/test_note_service.py
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

    note_path = settings.data_dir / note.rel_path
    assert note_path.read_text(encoding="utf-8") == "# 标题\n正文"
    assert read_note_content(db_session, task.id) == "# 标题\n正文"


def test_init_note_file_creates_empty_file(db_session):
    task = _make_task(db_session)
    note = init_note_file(db_session, task.id)
    note_path = settings.data_dir / note.rel_path
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
    old_rel = f"Python/LangChain.md"
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
```

**Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_note_service.py -v`
Expected: FAIL（`app.services.note_service` 不存在）。

**Step 3: 实现路径与文件服务**

```python
# app/services/note_service.py
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

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


def init_note_file(session: Session, task_id: int) -> NoteFile:
    task = _task_with_language(session, task_id)
    rel = note_rel_path(task)
    _write_file(rel, "")
    row = _row_for(session, task_id, NoteKind.note, rel)
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
    session.commit()
    return row


def move_task_files(
    session: Session, task_id: int, old_language: str, old_title: str
) -> list[NoteFile]:
    task = _task_with_language(session, task_id)
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
```

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_note_service.py -v`
Expected: PASS（5 passed）。

**Step 5: 提交**

```bash
git add app/services tests/test_note_service.py
git commit -m "实现笔记总结文件路径与读写服务"
```

---

### Task 4: 语言与任务服务

**Files:**
- Create: `Prince-PA/app/services/language_service.py`
- Create: `Prince-PA/app/services/task_service.py`
- Create: `Prince-PA/tests/test_task_service.py`

**Interfaces:**
- Consumes: `validate_component`、`move_task_files`、`NoteKind`、实体。
- Produces:
  - `language_service.get_or_create_language(session, name) -> Language`
  - `language_service.list_languages(session) -> list[Language]`
  - `task_service.list_tasks(session, language: str | None, status: TaskStatus | None, keyword: str | None) -> list[Task]`
  - `task_service.create_task(session, language_name, title, description) -> Task`
  - `task_service.update_task(session, task_id, language_name | None, title | None, description | None, status | None) -> Task`
  - `task_service.set_status(session, task_id, status) -> Task`

**Step 1: 写失败测试**

```python
# tests/test_task_service.py
from sqlalchemy import select

import pytest

from app.models.entities import Language, Task, TaskStatus
from app.services.language_service import get_or_create_language
from app.services.task_service import (
    create_task,
    list_tasks,
    set_status,
    update_task,
)


def test_create_task_creates_language_auto(db_session):
    task = create_task(db_session, "Python", "LangChain", "学工具")
    assert task.language.name == "Python"
    assert task.status == TaskStatus.todo


def test_create_duplicate_task_rejected(db_session):
    create_task(db_session, "Python", "LangChain", "")
    with pytest.raises(ValueError):
        create_task(db_session, "Python", "LangChain", "重复")


def test_list_tasks_filter_by_language_and_status(db_session):
    create_task(db_session, "Python", "P1", "")
    create_task(db_session, "Java", "J1", "")
    p1 = db_session.scalar(select(Task).where(Task.title == "P1"))
    set_status(db_session, p1.id, TaskStatus.in_progress)

    rows = list_tasks(db_session, language="Python", status=None, keyword=None)
    assert [t.title for t in rows] == ["P1"]


def test_update_task_moves_files(db_session):
    task = create_task(db_session, "Python", "旧主题", "")
    from app.services.note_service import write_note

    write_note(db_session, task.id, "body")
    get_or_create_language(db_session, "Java")
    updated = update_task(
        db_session, task.id, language_name="Java", title="新主题", description="d"
    )
    assert updated.language.name == "Java"
    assert updated.description == "d"
    old = db_session.scalar(select(Task).where(Task.id == task.id))
    assert old.note_files[0].rel_path == "Java/新主题.md"


def test_complete_task_sets_summary_pending(db_session):
    task = create_task(db_session, "Python", "Done", "")
    set_status(db_session, task.id, TaskStatus.completed)
    task = db_session.scalar(select(Task).where(Task.id == task.id))
    assert task.status == TaskStatus.completed
    assert task.completed_at is not None
    assert task.summary_status.value == "pending"
```

**Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_task_service.py -v`
Expected: FAIL（`app.services.task_service` 不存在）。

**Step 3: 实现服务**

```python
# app/services/language_service.py
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Language
from app.services.note_service import validate_component


def get_or_create_language(session: Session, name: str) -> Language:
    clean = validate_component(name, "语言")
    lang = session.scalar(select(Language).where(Language.name == clean))
    if lang is None:
        lang = Language(name=clean)
        session.add(lang)
        session.flush()
    return lang


def list_languages(session: Session) -> list[Language]:
    return list(session.scalars(select(Language).order_by(Language.sort_order, Language.id)))
```

```python
# app/services/task_service.py
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.entities import Language, SummaryStatus, Task, TaskStatus
from app.services.language_service import get_or_create_language
from app.services.note_service import move_task_files, validate_component


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _task_query():
    return select(Task).options(joinedload(Task.language), joinedload(Task.note_files))


def _get_task(session: Session, task_id: int) -> Task:
    task = session.scalar(_task_query().where(Task.id == task_id))
    if task is None:
        raise LookupError(f"任务不存在：{task_id}")
    return task


def list_tasks(
    session: Session,
    language: str | None = None,
    status: TaskStatus | None = None,
    keyword: str | None = None,
) -> list[Task]:
    query = _task_query().order_by(Task.created_at.desc())
    if language:
        query = query.join(Language).where(Language.name == language)
    if status is not None:
        query = query.where(Task.status == status)
    if keyword:
        like = f"%{keyword}%"
        query = query.where(or_(Task.title.like(like), Task.description.like(like)))
    return list(session.scalars(query))


def create_task(
    session: Session, language_name: str, title: str, description: str = ""
) -> Task:
    language = get_or_create_language(session, language_name)
    clean_title = validate_component(title, "主题")
    exists = session.scalar(
        select(Task.id).where(
            Task.language_id == language.id, Task.title == clean_title
        )
    )
    if exists is not None:
        raise ValueError(f"该语言下已存在主题：{clean_title}")
    task = Task(language_id=language.id, title=clean_title, description=description)
    session.add(task)
    session.commit()
    return _get_task(session, task.id)


def update_task(
    session: Session,
    task_id: int,
    language_name: str | None = None,
    title: str | None = None,
    description: str | None = None,
    status: TaskStatus | None = None,
) -> Task:
    task = _get_task(session, task_id)
    old_language = task.language.name
    old_title = task.title

    if language_name is not None and language_name.strip() != old_language:
        new_lang = get_or_create_language(session, language_name)
        task.language_id = new_lang.id
    if title is not None:
        clean_title = validate_component(title, "主题")
        if clean_title != old_title:
            clash = session.scalar(
                select(Task.id).where(
                    Task.language_id == task.language_id,
                    Task.title == clean_title,
                    Task.id != task_id,
                )
            )
            if clash is not None:
                raise ValueError(f"该语言下已存在主题：{clean_title}")
            task.title = clean_title
    if description is not None:
        task.description = description
    if status is not None:
        task.status = status
        if status == TaskStatus.completed and task.completed_at is None:
            task.completed_at = _utcnow()
            task.summary_status = SummaryStatus.pending
            task.summary_error = None
    session.flush()
    rename_needed = (
        language_name is not None and language_name.strip() != old_language
    ) or (title is not None and title.strip() != old_title)
    if rename_needed:
        move_task_files(session, task_id, old_language, old_title)
    session.commit()
    return _get_task(session, task_id)


def set_status(session: Session, task_id: int, status: TaskStatus) -> Task:
    return update_task(session, task_id, status=status)
```

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_task_service.py -v`
Expected: PASS（5 passed）。

**Step 5: 提交**

```bash
git add app/services tests/test_task_service.py
git commit -m "实现语言分类与学习任务服务"
```

---

### Task 5: 学习记录服务

**Files:**
- Create: `Prince-PA/app/services/record_service.py`
- Create: `Prince-PA/tests/test_record_service.py`

**Interfaces:**
- Consumes: `LearningRecord`、`RecordType`、`utcnow`。
- Produces:
  - `create_auto_record(session, task_id, started_at: datetime | None = None) -> LearningRecord`
  - `create_manual_record(session, task_id, started_at, content: str = "") -> LearningRecord`
  - `list_records_by_task(session, task_id) -> list[LearningRecord]`

**Step 1: 写失败测试**

```python
# tests/test_record_service.py
from datetime import datetime, timezone

from sqlalchemy import select

from app.models.entities import LearningRecord, RecordType
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
```

**Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_record_service.py -v`
Expected: FAIL（`app.services.record_service` 不存在）。

**Step 3: 实现服务**

```python
# app/services/record_service.py
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
```

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_record_service.py -v`
Expected: PASS（3 passed）。

**Step 5: 提交**

```bash
git add app/services/record_service.py tests/test_record_service.py
git commit -m "实现学习记录服务"
```

---

### Task 6: 总结生成器（LangChain + DeepSeek，可 mock）

**Files:**
- Create: `Prince-PA/agents/__init__.py`
- Create: `Prince-PA/agents/llm.py`
- Create: `Prince-PA/agents/summarizer.py`
- Create: `Prince-PA/tests/test_summarizer.py`

**Interfaces:**
- Consumes: `settings.deepseek_api_key`、`Task`。
- Produces:
  - `agents.llm.build_chat_model() -> ChatDeepSeek`
  - `agents.summarizer.generate_summary(task: Task, note_content: str, model: BaseChatModel | None = None) -> str`

**Step 1: 写失败测试**

```python
# tests/test_summarizer.py
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from agents.summarizer import generate_summary
from app.models.entities import Language, Task


class FakeChatModel(BaseChatModel):
    """记录收到的消息并返回固定总结。"""

    received_messages = []

    @property
    def _llm_type(self) -> str:
        return "fake-chat"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        type(self).received_messages = list(messages)
        content = "# 总结\n\n来自 fake 模型的输出"
        message = AIMessage(content=content)
        return ChatResult(generations=[ChatGeneration(message=message)])


def _task():
    return Task(id=1, language=Language(name="Python"), title="LangChain", description="d")


def test_generate_summary_uses_model(db_session):
    model = FakeChatModel()
    result = generate_summary(_task(), "# 笔记正文", model=model)
    assert result == "# 总结\n\n来自 fake 模型的输出"
    joined = "\n".join(m.content for m in FakeChatModel.received_messages)
    assert "LangChain" in joined
    assert "# 笔记正文" in joined
```

**Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_summarizer.py -v`
Expected: FAIL（`agents.summarizer` 不存在）。

**Step 3: 实现模型与总结生成**

```python
# agents/llm.py
from langchain_deepseek import ChatDeepSeek

from app.core.config import settings


def build_chat_model() -> ChatDeepSeek:
    return ChatDeepSeek(
        model="deepseek-chat",
        api_key=settings.deepseek_api_key,
        temperature=0.3,
        max_tokens=4000,
    )
```

```python
# agents/summarizer.py
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import build_chat_model
from app.models.entities import Task


def generate_summary(
    task: Task,
    note_content: str,
    model: BaseChatModel | None = None,
) -> str:
    chat = model or build_chat_model()
    system = (
        "你是Prince-PA学习助理的总结引擎。根据任务信息和笔记内容生成结构化"
        "中文Markdown总结，使用如下结构：# <主题>总结；## 学习要点；## 实践记录；"
        "## 问题与反思。笔记为空时，基于任务描述输出要点并注明'笔记尚未填写'。"
        "不要虚构未出现在素材中的事实。"
    )
    material = note_content or task.description or "（该任务暂无可参考笔记）"
    user_text = f"任务语言：{task.language.name}\n任务主题：{task.title}\n参考素材：\n{material}"
    response = chat.invoke([SystemMessage(content=system), HumanMessage(content=user_text)])
    return str(response.content)
```

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_summarizer.py -v`
Expected: PASS（1 passed）。

**Step 5: 提交**

```bash
git add agents tests/test_summarizer.py
git commit -m "实现LangChain DeepSeek总结生成器"
```

---

### Task 7: 任务完成流程与后台总结

**Files:**
- Create: `Prince-PA/app/services/completion_service.py`
- Create: `Prince-PA/tests/test_completion_service.py`

**Interfaces:**
- Consumes: `read_note_content`、`write_summary`、`generate_summary`、`Task`。
- Produces:
  - `run_summary_generation(session_factory: Callable[[], Session], task_id: int, generator: Callable[..., str] | None = None) -> None`
  - 成功：`task.summary_status=success`；失败：`summary_status=failed`、`summary_error=原因`。

**Step 1: 写失败测试**

```python
# tests/test_completion_service.py
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.entities import SummaryStatus, Task, TaskStatus
from app.services.completion_service import run_summary_generation
from app.services.note_service import write_note
from app.services.task_service import create_task, set_status


def test_run_summary_generation_success(db_session):
    task = create_task(db_session, "Python", "总结任务", "")
    write_note(db_session, task.id, "# 学到的内容\nLangChain 工具调用")
    set_status(db_session, task.id, TaskStatus.completed)

    def fake_generator(task, note_content, model=None):
        return f"# {task.title}-总结\n\n{note_content}"

    run_summary_generation(lambda: db_session, task.id, generator=fake_generator)

    task = db_session.scalar(select(Task).where(Task.id == task.id))
    assert task.summary_status == SummaryStatus.success
    assert task.summary_error is None
    assert task.note_files[0].rel_path.endswith("-总结.md")


def test_run_summary_generation_failure(db_session):
    task = create_task(db_session, "Python", "失败任务", "")
    set_status(db_session, task.id, TaskStatus.completed)

    def boom_generator(task, note_content, model=None):
        raise RuntimeError("模型不可用")

    run_summary_generation(lambda: db_session, task.id, generator=boom_generator)

    task = db_session.scalar(select(Task).where(Task.id == task.id))
    assert task.summary_status == SummaryStatus.failed
    assert "模型不可用" in task.summary_error
```

**Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_completion_service.py -v`
Expected: FAIL（`app.services.completion_service` 不存在）。

**Step 3: 实现完成服务**

```python
# app/services/completion_service.py
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from agents.summarizer import generate_summary
from app.models.entities import SummaryStatus, Task
from app.services.note_service import read_note_content, write_summary


def run_summary_generation(
    session_factory: Callable[[], Session],
    task_id: int,
    generator: Callable[..., str] | None = None,
) -> None:
    generator = generator or generate_summary
    with session_factory() as session:
        task = session.scalar(select(Task).where(Task.id == task_id))
        if task is None:
            return
        try:
            note_content = read_note_content(session, task_id)
            content = generator(task, note_content)
            write_summary(session, task_id, content)
            task.summary_status = SummaryStatus.success
            task.summary_error = None
            session.commit()
        except Exception as exc:  # noqa: BLE001 - 后台任务必须兜底
            task = session.scalar(select(Task).where(Task.id == task_id))
            if task is not None:
                task.summary_status = SummaryStatus.failed
                task.summary_error = str(exc)
                session.commit()
```

> 注意：`write_summary` 内部已提交一次；随后再更新状态并提交是幂等的。`lambda: db_session`
> 在测试中返回同一会话，`with` 只负责上下文退出，不关闭该会话。

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_completion_service.py -v`
Expected: PASS（2 passed）。

**Step 5: 提交**

```bash
git add app/services/completion_service.py tests/test_completion_service.py
git commit -m "实现任务完成后台总结流程"
```

---

### Task 8: 语言与任务 REST API

**Files:**
- Create: `Prince-PA/app/schemas/__init__.py`
- Create: `Prince-PA/app/schemas/task.py`
- Create: `Prince-PA/app/core/errors.py`
- Create: `Prince-PA/app/api/__init__.py`
- Create: `Prince-PA/app/api/languages.py`
- Create: `Prince-PA/app/api/tasks.py`
- Modify: `Prince-PA/app/main.py`
- Create: `Prince-PA/tests/test_api_tasks.py`

**Interfaces:**
- Consumes: `get_db`、任务/语言/记录服务、`BackgroundTasks`、`SessionLocal`、`run_summary_generation`。
- Produces:
  - `GET/POST /api/languages`
  - `GET/POST /api/tasks`、`GET/PATCH /api/tasks/{id}`
  - `POST /api/tasks/{id}/start`、`POST /api/tasks/{id}/complete`

**Step 1: 写失败测试**

```python
# tests/test_api_tasks.py
import app.api.tasks as tasks_api
from app.models.entities import Language


def _add_language_and_task(db_session):
    lang = Language(name="Python", sort_order=1)
    db_session.add(lang)
    db_session.commit()


def test_create_and_list_task(client):
    resp = client.post(
        "/api/tasks",
        json={"language": "Python", "title": "LangChain", "description": "d"},
    )
    assert resp.status_code == 201
    task = resp.json()
    assert task["language"] == "Python"

    rows = client.get("/api/tasks?language=Python").json()
    assert len(rows) == 1


def test_duplicate_task_returns_400(client):
    payload = {"language": "Python", "title": "重复任务", "description": ""}
    assert client.post("/api/tasks", json=payload).status_code == 201
    assert client.post("/api/tasks", json=payload).status_code == 400


def test_start_creates_auto_record(client):
    task_id = client.post(
        "/api/tasks",
        json={"language": "Python", "title": "开始任务", "description": ""},
    ).json()["id"]

    resp = client.post(f"/api/tasks/{task_id}/start")
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"
    records = client.get(f"/api/tasks/{task_id}/records").json()
    assert len(records) == 1
    assert records[0]["record_type"] == "auto"


def test_complete_schedules_summary(client, monkeypatch):
    calls = []

    def fake_run(session_factory, task_id, generator=None):
        calls.append(task_id)

    monkeypatch.setattr(tasks_api, "run_summary_generation", fake_run)
    task_id = client.post(
        "/api/tasks",
        json={"language": "Python", "title": "完成任务", "description": ""},
    ).json()["id"]

    resp = client.post(f"/api/tasks/{task_id}/complete")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert calls == [task_id]
```

**Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_api_tasks.py -v`
Expected: FAIL（`app.api.tasks` 不存在）。

**Step 3: 实现 schema、错误与路由**

```python
# app/schemas/task.py
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
```

`TaskOut` 中 `language` 由路由层从 `task.language.name` 组装，因此后续在服务层返回时统一使用 `task_to_out(task)` 辅助函数，避免 ORM 字段与 schema 不一致：

```python
# app/api/tasks.py（节选，包含辅助函数与全部路由）
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.models.entities import Task as TaskModel
from app.models.entities import TaskStatus
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate
from app.services.record_service import create_auto_record
from app.services.task_service import (
    create_task,
    list_tasks,
    set_status,
    update_task,
)
from app.services.completion_service import run_summary_generation

router = APIRouter(prefix="/api")


def _get_task_or_404(session: Session, task_id: int) -> TaskModel:
    task = session.scalar(select(TaskModel).where(TaskModel.id == task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


def task_to_out(task: TaskModel) -> TaskOut:
    return TaskOut(
        id=task.id,
        language=task.language.name,
        title=task.title,
        description=task.description,
        status=task.status,
        summary_status=task.summary_status,
        summary_error=task.summary_error,
        completed_at=task.completed_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get("/tasks", response_model=list[TaskOut])
def api_list_tasks(
    language: str | None = None,
    status: TaskStatus | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
):
    return [task_to_out(t) for t in list_tasks(db, language, status, keyword)]


@router.post("/tasks", response_model=TaskOut, status_code=201)
def api_create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    try:
        task = create_task(db, payload.language, payload.title, payload.description)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return task_to_out(task)


@router.get("/tasks/{task_id}", response_model=TaskOut)
def api_get_task(task_id: int, db: Session = Depends(get_db)):
    return task_to_out(_get_task_or_404(db, task_id))


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def api_update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    try:
        task = update_task(
            db,
            task_id,
            language_name=payload.language,
            title=payload.title,
            description=payload.description,
            status=payload.status,
        )
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=400 if isinstance(exc, ValueError) else 404, detail=str(exc))
    return task_to_out(task)


@router.post("/tasks/{task_id}/start", response_model=TaskOut)
def api_start_task(task_id: int, db: Session = Depends(get_db)):
    task = _get_task_or_404(db, task_id)
    if task.status == TaskStatus.completed:
        task.completed_at = None
    task = set_status(db, task_id, TaskStatus.in_progress)
    create_auto_record(db, task_id)
    return task_to_out(task)


@router.post("/tasks/{task_id}/complete", response_model=TaskOut)
def api_complete_task(
    task_id: int,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    task = _get_task_or_404(db, task_id)
    if task.status != TaskStatus.completed:
        task = set_status(db, task_id, TaskStatus.completed)
        background.add_task(run_summary_generation, SessionLocal, task_id)
    return task_to_out(task)
```

```python
# app/core/errors.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"code": "bad_request", "message": str(exc)})

    @app.exception_handler(LookupError)
    async def not_found_handler(request: Request, exc: LookupError):
        return JSONResponse(status_code=404, content={"code": "not_found", "message": str(exc)})
```

`languages.py`：

```python
# app/api/languages.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.task import LanguageCreate, LanguageOut
from app.services.language_service import get_or_create_language, list_languages

router = APIRouter(prefix="/api/languages", tags=["languages"])


@router.get("", response_model=list[LanguageOut])
def api_list_languages(db: Session = Depends(get_db)):
    return list_languages(db)


@router.post("", response_model=LanguageOut, status_code=201)
def api_create_language(payload: LanguageCreate, db: Session = Depends(get_db)):
    try:
        lang = get_or_create_language(db, payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    db.commit()
    return LanguageOut.model_validate(lang)
```

`app/main.py` 装配：

```python
from fastapi import FastAPI

from app.api import languages, tasks
from app.core.errors import install_exception_handlers

app = FastAPI(title="Prince-PA", version="0.1.0")
install_exception_handlers(app)
app.include_router(languages.router)
app.include_router(tasks.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
```

> 说明：`test_start_creates_auto_record` 依赖 `/api/tasks/{id}/records`，该路由在 Task 9 实现；因此本任务实现后，该测试标记为 **skip**（加 `@pytest.mark.skip(reason="records API in task 9")`），Task 9 完成时移除 skip。

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_api_tasks.py -v`
Expected: 4 passed、1 skipped。

**Step 5: 提交**

```bash
git add app/schemas app/core/errors.py app/api app/main.py tests/test_api_tasks.py
git commit -m "实现语言与任务REST API"
```

---

### Task 9: 笔记、总结与学习记录 REST API

**Files:**
- Create: `Prince-PA/app/schemas/note.py`
- Create: `Prince-PA/app/schemas/record.py`
- Create: `Prince-PA/app/api/notes.py`
- Create: `Prince-PA/app/api/summaries.py`
- Create: `Prince-PA/app/api/records.py`
- Modify: `Prince-PA/app/main.py`
- Modify: `Prince-PA/tests/test_api_tasks.py`（移除 skip）
- Create: `Prince-PA/tests/test_api_notes_records.py`

**Interfaces:**
- Consumes: `read_note_content`、`write_note`、`read_summary_content`、`write_summary`、记录服务、`run_summary_generation`。
- Produces:
  - `GET/PUT /api/tasks/{task_id}/note`
  - `GET /api/tasks/{task_id}/summary`、`POST /api/tasks/{task_id}/summary/regenerate`
  - `GET/POST /api/tasks/{task_id}/records`

**Step 1: 写失败测试**

```python
# tests/test_api_notes_records.py
import app.api.summaries as summaries_api
from app.models.entities import SummaryStatus, Task, TaskStatus
from app.services.task_service import create_task, set_status


def _task(client):
    resp = client.post(
        "/api/tasks",
        json={"language": "Python", "title": "API笔记任务", "description": ""},
    )
    return resp.json()


def test_note_put_and_get(client):
    task = _task(client)
    put = client.put(f"/api/tasks/{task['id']}/note", json={"content": "# 正文"})
    assert put.status_code == 200
    got = client.get(f"/api/tasks/{task['id']}/note").json()
    assert got["content"] == "# 正文"
    assert got["rel_path"].endswith("API笔记任务.md")


def test_manual_record_post_and_list(client):
    task = _task(client)
    payload = {
        "started_at": "2026-09-06T10:00:00Z",
        "content": "今天学了工具调用",
    }
    resp = client.post(f"/api/tasks/{task['id']}/records", json=payload)
    assert resp.status_code == 201
    assert resp.json()["record_type"] == "manual"
    rows = client.get(f"/api/tasks/{task['id']}/records").json()
    assert len(rows) == 1


def test_summary_get_and_regenerate(client, monkeypatch, db_session):
    calls = []

    def fake_run(session_factory, task_id, generator=None):
        calls.append(task_id)

    monkeypatch.setattr(summaries_api, "run_summary_generation", fake_run)
    task = _task(client)
    task_id = task["id"]

    # 先让任务完成并直接落库成功状态，模拟后台已生成
    model_task = db_session.get(Task, task_id)
    model_task.summary_status = SummaryStatus.success
    db_session.commit()

    got = client.get(f"/api/tasks/{task_id}/summary")
    assert got.status_code == 200
    resp = client.post(f"/api/tasks/{task_id}/summary/regenerate")
    assert resp.status_code == 200
    assert calls == [task_id]
```

**Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_api_notes_records.py -v`
Expected: FAIL（`app.api.notes` 不存在）。

**Step 3: 实现 schemas 与路由**

```python
# app/schemas/note.py
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
```

```python
# app/schemas/record.py
from datetime import datetime
from typing import Optional

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
```

```python
# app/api/notes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.note import NoteContent, NoteOut
from app.services.note_service import (
    init_note_file,
    read_note_content,
    write_note,
)
from app.services.task_service import _get_task

router = APIRouter(prefix="/api/tasks/{task_id}", tags=["notes"])


@router.get("/note", response_model=NoteOut)
def api_get_note(task_id: int, db: Session = Depends(get_db)):
    try:
        _get_task(db, task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return NoteOut(content=read_note_content(db, task_id))


@router.put("/note", response_model=NoteOut)
def api_save_note(task_id: int, payload: NoteContent, db: Session = Depends(get_db)):
    try:
        row = write_note(db, task_id, payload.content)
    except (LookupError, ValueError) as exc:
        status = 404 if isinstance(exc, LookupError) else 400
        raise HTTPException(status_code=status, detail=str(exc))
    return NoteOut(content=payload.content, rel_path=row.rel_path)
```

```python
# app/api/records.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.record import RecordCreate, RecordOut
from app.services.record_service import (
    create_manual_record,
    list_records_by_task,
)
from app.services.task_service import _get_task

router = APIRouter(prefix="/api/tasks/{task_id}/records", tags=["records"])


@router.get("", response_model=list[RecordOut])
def api_list_records(task_id: int, db: Session = Depends(get_db)):
    try:
        _get_task(db, task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return list_records_by_task(db, task_id)


@router.post("", response_model=RecordOut, status_code=201)
def api_create_record(task_id: int, payload: RecordCreate, db: Session = Depends(get_db)):
    try:
        _get_task(db, task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return create_manual_record(db, task_id, payload.started_at, payload.content)
```

```python
# app/api/summaries.py
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.models.entities import SummaryStatus, Task
from app.schemas.note import SummaryOut
from app.services.completion_service import run_summary_generation
from app.services.note_service import read_summary_content
from app.services.task_service import _get_task

router = APIRouter(prefix="/api/tasks/{task_id}/summary", tags=["summaries"])


@router.get("", response_model=SummaryOut)
def api_get_summary(task_id: int, db: Session = Depends(get_db)):
    try:
        task = _get_task(db, task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return SummaryOut(
        status=task.summary_status.value,
        content=read_summary_content(db, task_id),
        error=task.summary_error,
    )


@router.post("/regenerate", response_model=SummaryOut)
def api_regenerate_summary(
    task_id: int,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    task = db.scalar(select(Task).where(Task.id == task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.summary_status = SummaryStatus.pending
    task.summary_error = None
    db.commit()
    background.add_task(run_summary_generation, SessionLocal, task_id)
    return SummaryOut(status="pending")
```

`app/main.py` 增加三个 router：

```python
from app.api import languages, notes, records, summaries, tasks

app.include_router(notes.router)
app.include_router(summaries.router)
app.include_router(records.router)
```

**Step 4: 移除 Task 8 的 skip**

将 `tests/test_api_tasks.py` 中 `test_start_creates_auto_record` 上的
`@pytest.mark.skip(...)` 删除；该测试现在依赖的记录路由已存在。

**Step 5: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_api_tasks.py tests/test_api_notes_records.py -v`
Expected: 全部 PASS。

**Step 6: 提交**

```bash
git add app/schemas/note.py app/schemas/record.py app/api tests/test_api_notes_records.py app/main.py
git commit -m "实现笔记总结学习记录REST API"
```

---

### Task 10: 聊天会话与消息仓库

**Files:**
- Create: `Prince-PA/app/services/chat_service.py`
- Create: `Prince-PA/tests/test_chat_service.py`

**Interfaces:**
- Produces:
  - `create_session(db) -> ChatSession`
  - `list_sessions(db) -> list[ChatSession]`
  - `get_session(db, session_id) -> ChatSession`
  - `create_message(db, session_id, role: MessageRole, content: str | None, tool_name: str | None = None, tool_input_json: str | None = None) -> ChatMessage`
  - `list_messages(db, session_id, limit: int = 100) -> list[ChatMessage]`

**Step 1: 写失败测试**

```python
# tests/test_chat_service.py
from sqlalchemy import select

from app.models.entities import ChatMessage, ChatSession, MessageRole
from app.services.chat_service import (
    create_message,
    create_session,
    list_messages,
    list_sessions,
)


def test_create_session_and_message(db_session):
    session = create_session(db_session)
    assert session.title == "新会话"

    create_message(db_session, session.id, MessageRole.user, "帮我加任务")
    create_message(db_session, session.id, MessageRole.assistant, "好的")

    rows = list_messages(db_session, session.id)
    assert [m.role.value for m in rows] == ["user", "assistant"]
    assert len(list_sessions(db_session)) == 1
```

**Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_chat_service.py -v`
Expected: FAIL。

**Step 3: 实现仓库**

```python
# app/services/chat_service.py
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    ChatMessage,
    ChatSession,
    MessageRole,
)


def create_session(db: Session) -> ChatSession:
    session = ChatSession()
    db.add(session)
    db.commit()
    return session


def list_sessions(db: Session) -> list[ChatSession]:
    return list(
        db.scalars(
            select(ChatSession).order_by(ChatSession.updated_at.desc())
        )
    )


def get_session(db: Session, session_id: int) -> ChatSession:
    session = db.get(ChatSession, session_id)
    if session is None:
        raise LookupError(f"会话不存在：{session_id}")
    return session


def create_message(
    db: Session,
    session_id: int,
    role: MessageRole,
    content: str | None,
    tool_name: str | None = None,
    tool_input_json: str | None = None,
) -> ChatMessage:
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        tool_name=tool_name,
        tool_input_json=tool_input_json,
    )
    db.add(message)
    get_session(db, session_id).updated_at = message.created_at
    db.commit()
    return message


def list_messages(db: Session, session_id: int, limit: int = 100) -> list[ChatMessage]:
    return list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
    )
```

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_chat_service.py -v`
Expected: PASS。

**Step 5: 提交**

```bash
git add app/services/chat_service.py tests/test_chat_service.py
git commit -m "实现聊天会话与消息仓库"
```

---

### Task 11: 会话记忆与用户画像/偏好服务

**Files:**
- Create: `Prince-PA/agents/memory/__init__.py`
- Create: `Prince-PA/agents/memory/conversation.py`
- Create: `Prince-PA/agents/memory/profile.py`
- Create: `Prince-PA/agents/memory/extractor.py`
- Modify: `Prince-PA/app/services/completion_service.py`
- Modify: `Prince-PA/app/api/tasks.py`
- Modify: `Prince-PA/app/api/summaries.py`
- Create: `Prince-PA/tests/test_memory.py`

**Interfaces:**
- Produces:
  - `conversation.load_langchain_history(db, session_id) -> list[BaseMessage]`
  - `extractor.extract_preferences(task, note_content, summary_content, chat_snippets, model=None) -> list[dict]`
  - `profile.trigger_after_summary(session_factory, task_id) -> None`
  - `profile.trigger_manual_extract(session_factory, user_id) -> int`
  - `profile.list_pending(session, user_id) -> list[UserPreference]`
  - `profile.confirm_preference(session, preference_id) -> UserPreference`
  - `profile.dismiss_preference(session, preference_id) -> UserPreference`
  - `profile.latest_profile(session, user_id) -> dict`

**Step 1: 写失败测试**

```python
# tests/test_memory.py
from sqlalchemy import select

from agents.memory.conversation import load_langchain_history
from agents.memory.profile import (
    confirm_preference,
    dismiss_preference,
    list_pending,
)
from app.models.entities import (
    ChatMessage,
    ChatSession,
    MessageRole,
    PreferenceStatus,
    UserPreference,
)
from app.services.chat_service import create_message, create_session


def test_load_langchain_history(db_session):
    session = create_session(db_session)
    create_message(db_session, session.id, MessageRole.user, "你好")
    create_message(db_session, session.id, MessageRole.assistant, "你好")
    history = load_langchain_history(db_session, session.id)
    assert history[0].type == "human"
    assert history[1].type == "ai"


def test_preference_confirm_and_dismiss(db_session):
    pref = UserPreference(
        user_id="local",
        dimension="summary_style",
        value="详细",
        source="auto",
        status=PreferenceStatus.pending,
        confidence=0.8,
    )
    db_session.add(pref)
    db_session.commit()

    assert len(list_pending(db_session, "local")) == 1
    confirmed = confirm_preference(db_session, pref.id)
    assert confirmed.status == PreferenceStatus.confirmed
    dismissed = dismiss_preference(db_session, pref.id)
    assert dismissed.status == PreferenceStatus.dismissed
```

**Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_memory.py -v`
Expected: FAIL。

**Step 3: 实现会话记忆**

```python
# agents/memory/conversation.py
from sqlalchemy import select
from sqlalchemy.orm import Session
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.models.entities import ChatMessage, MessageRole


def load_langchain_history(db: Session, session_id: int) -> list[BaseMessage]:
    rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    result: list[BaseMessage] = []
    for row in rows:
        content = row.content or ""
        if row.role == MessageRole.user:
            result.append(HumanMessage(content=content))
        elif row.role == MessageRole.assistant:
            result.append(AIMessage(content=content))
        elif row.role == MessageRole.system:
            result.append(SystemMessage(content=content))
    return result
```

**Step 4: 实现画像与偏好服务**

```python
# agents/memory/profile.py
import json
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from agents.memory.extractor import extract_preferences
from app.core.config import settings
from app.models.entities import (
    ChatMessage,
    Language,
    MessageRole,
    PreferenceStatus,
    SourceType,
    SummaryStatus,
    Task,
    UserPreference,
    UserProfile,
)
from app.services.note_service import read_note_content, read_summary_content

USER_ID = "local"
DIMENSIONS = {"learning_focus", "learning_style", "summary_style", "response_style"}


def _add_pending(session: Session, user_id: str, item: dict) -> UserPreference:
    dimension = item.get("dimension")
    if dimension not in DIMENSIONS:
        raise ValueError(f"未知偏好维度：{dimension}")
    row = session.scalar(
        select(UserPreference).where(
            UserPreference.user_id == user_id,
            UserPreference.dimension == dimension,
            UserPreference.status == PreferenceStatus.pending,
        )
    )
    if row is None:
        row = UserPreference(user_id=user_id, dimension=dimension)
        session.add(row)
    row.value = str(item.get("value", ""))
    row.source = SourceType(item.get("source", "auto"))
    row.confidence = float(item.get("confidence", 0.5))
    row.evidence = item.get("evidence")
    session.commit()
    return row


def list_pending(session: Session, user_id: str = USER_ID) -> list[UserPreference]:
    return list(
        session.scalars(
            select(UserPreference).where(
                UserPreference.user_id == user_id,
                UserPreference.status == PreferenceStatus.pending,
            )
        )
    )


def confirm_preference(
    session: Session, preference_id: int, user_id: str = USER_ID
) -> UserPreference:
    row = session.get(UserPreference, preference_id)
    if row is None or row.user_id != user_id:
        raise LookupError("偏好项不存在")
    row.status = PreferenceStatus.confirmed
    session.commit()
    snapshot(session, user_id)
    return row


def dismiss_preference(
    session: Session, preference_id: int, user_id: str = USER_ID
) -> UserPreference:
    row = session.get(UserPreference, preference_id)
    if row is None or row.user_id != user_id:
        raise LookupError("偏好项不存在")
    row.status = PreferenceStatus.dismissed
    session.commit()
    return row


def snapshot(session: Session, user_id: str = USER_ID) -> UserProfile:
    confirmed = session.scalars(
        select(UserPreference).where(
            UserPreference.user_id == user_id,
            UserPreference.status == PreferenceStatus.confirmed,
        )
    ).all()
    payload = {row.dimension: {"value": row.value, "confirmed_at": row.updated_at.isoformat()} for row in confirmed}
    profile = UserProfile(user_id=user_id, profile_json=json.dumps(payload, ensure_ascii=False), source="auto")
    session.add(profile)
    session.commit()
    return profile


def latest_profile(session: Session, user_id: str = USER_ID) -> dict:
    row = session.scalar(
        select(UserProfile)
        .where(UserProfile.user_id == user_id)
        .order_by(UserProfile.id.desc())
        .limit(1)
    )
    if row is None:
        return {}
    return json.loads(row.profile_json)


def _recent_chat_snippets(session: Session, limit: int = 10) -> list[str]:
    rows = session.scalars(
        select(ChatMessage)
        .where(ChatMessage.role == MessageRole.user)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    return [row.content or "" for row in rows]


def _extract_from_materials(
    session: Session,
    language_name: str,
    title: str,
    note_content: str,
    summary_content: str,
    user_id: str,
    source: SourceType,
) -> int:
    if not settings.deepseek_api_key:
        return 0
    task = Task(language=Language(name=language_name), title=title)
    items = extract_preferences(
        task,
        note_content,
        summary_content,
        _recent_chat_snippets(session),
    )
    count = 0
    for item in items:
        try:
            item["source"] = source.value
            _add_pending(session, user_id, item)
            count += 1
        except ValueError:
            continue
    return count


def trigger_after_summary(
    session_factory: Callable[[], Session], task_id: int, user_id: str = USER_ID
) -> None:
    with session_factory() as session:
        task = session.get(Task, task_id)
        if task is None or task.summary_status != SummaryStatus.success:
            return
        _extract_from_materials(
            session,
            task.language.name,
            task.title,
            read_note_content(session, task_id),
            read_summary_content(session, task_id) or "",
            user_id,
            SourceType.auto,
        )


def trigger_manual_extract(
    session_factory: Callable[[], Session], user_id: str = USER_ID
) -> int:
    with session_factory() as session:
        task = session.scalar(
            select(Task)
            .where(Task.summary_status == SummaryStatus.success)
            .order_by(Task.completed_at.desc())
            .limit(1)
        )
        if task is None:
            return 0
        return _extract_from_materials(
            session,
            task.language.name,
            task.title,
            read_note_content(session, task.id),
            read_summary_content(session, task.id) or "",
            user_id,
            SourceType.manual,
        )
```

**Step 5: 实现提炼器**

```python
# agents/memory/extractor.py
import json

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import build_chat_model
from app.models.entities import Task


def extract_preferences(
    task: Task,
    note_content: str,
    summary_content: str,
    chat_snippets: list[str],
    model: BaseChatModel | None = None,
) -> list[dict]:
    chat = model or build_chat_model()
    system = (
        "你是Prince-PA的用户画像提炼器。根据任务信息、笔记、总结与对话片段，"
        "提炼用户偏好。只输出JSON数组："
        '[{"dimension":"learning_focus|learning_style|summary_style|response_style",'
        '"value":"中文摘要","confidence":0到1,"evidence":"来源摘录"}]。'
        "没有依据的维度不要输出。"
    )
    user = (
        f"任务：{task.language.name} / {task.title}\n"
        f"笔记：{note_content}\n总结：{summary_content}\n对话：{chr(10).join(chat_snippets[-20:])}"
    )
    response = chat.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    raw = response.content
    if isinstance(raw, list):
        raw = "".join(str(part.get("text", "")) for part in raw if isinstance(part, dict))
    text = str(raw).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    parsed = json.loads(text)
    if isinstance(parsed, dict):
        parsed = parsed.get("preferences", [])
    return [item for item in parsed if isinstance(item, dict)]
```

**Step 6: 将自动提炼挂到完成流程**

将 `app/services/completion_service.py` 全文替换为以下实现（增加可选回调）：

```python
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from agents.summarizer import generate_summary
from app.models.entities import SummaryStatus, Task
from app.services.note_service import read_note_content, write_summary


def run_summary_generation(
    session_factory: Callable[[], Session],
    task_id: int,
    generator: Callable[..., str] | None = None,
    after_success: Callable[[Callable[[], Session], int], None] | None = None,
) -> None:
    generator = generator or generate_summary
    with session_factory() as session:
        task = session.scalar(select(Task).where(Task.id == task_id))
        if task is None:
            return
        try:
            note_content = read_note_content(session, task_id)
            content = generator(task, note_content)
            write_summary(session, task_id, content)
            task.summary_status = SummaryStatus.success
            task.summary_error = None
            session.commit()
            if after_success is not None:
                after_success(session_factory, task_id)
        except Exception as exc:  # noqa: BLE001 - 后台任务必须兜底
            task = session.scalar(select(Task).where(Task.id == task_id))
            if task is not None:
                task.summary_status = SummaryStatus.failed
                task.summary_error = str(exc)
                session.commit()
```

在 `app/api/tasks.py` 与 `app/api/summaries.py` 的调用处传入
`after_success=profile.trigger_after_summary`（Task 12 的测试通过 monkeypatch
`profile.trigger_after_summary` 验证被调用；`extract_preferences` 只在有真实
API Key 时执行，无 Key 时应在 `profile._extract_from_materials` 中直接返回，
避免测试环境联网）。

两个文件均需新增导入：

```python
from agents.memory.profile import trigger_after_summary
```

并把后台调度改成：

```python
background.add_task(
    run_summary_generation,
    SessionLocal,
    task_id,
    after_success=trigger_after_summary,
)
```

**Step 7: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_memory.py tests/test_completion_service.py tests/test_api_tasks.py -v`
Expected: PASS。

**Step 8: 提交**

```bash
git add agents/memory app/services/completion_service.py app/api tests/test_memory.py
git commit -m "实现会话记忆与用户画像偏好服务"
```

---

### Task 12: Agent 工具与对话编排

**Files:**
- Create: `Prince-PA/agents/tools/__init__.py`
- Create: `Prince-PA/agents/tools/language_tools.py`
- Create: `Prince-PA/agents/tools/task_tools.py`
- Create: `Prince-PA/agents/tools/note_tools.py`
- Create: `Prince-PA/agents/assistant.py`
- Create: `Prince-PA/tests/test_tools.py`

**Interfaces:**
- Consumes: 各服务、`run_summary_generation`、`build_chat_model`、`load_langchain_history`。
- Produces:
  - `tools.build_all_tools(session_factory) -> list[BaseTool]`
  - `assistant.build_agent_executor(session_factory) -> AgentExecutor`
  - `assistant.stream_agent_response(session_factory, session_id, user_text) -> AsyncIterator[dict]`

**Step 1: 写失败测试**

```python
# tests/test_tools.py
from agents.tools.note_tools import build_note_tools
from agents.tools.task_tools import build_task_tools


def _factory(db_session):
    return lambda: db_session


def test_create_and_read_task_tool(db_session):
    task_tools = build_task_tools(_factory(db_session))
    created = task_tools[0].invoke(
        {"language": "Python", "title": "工具任务", "description": "通过工具创建"}
    )
    assert "id" in created

    note_tools = build_note_tools(_factory(db_session))
    init_result = note_tools[0].invoke({"task_id": 1})
    assert "已创建笔记文件" in init_result
    read_result = note_tools[1].invoke({"task_id": 1})
    assert "空" in read_result
```

**Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_tools.py -v`
Expected: FAIL。

**Step 3: 实现工具目录**

```python
# agents/tools/language_tools.py
from typing import Callable

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.services.language_service import list_languages


def build_language_tools(session_factory: Callable[[], Session]):
    @tool
    def list_languages_tool() -> str:
        """列出系统已有的编程语言分类。"""
        with session_factory() as session:
            rows = list_languages(session)
        return "\n".join(f"- {row.name}" for row in rows) or "暂无语言分类"

    return [list_languages_tool]
```

```python
# agents/tools/task_tools.py
import json
from typing import Callable

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from agents.memory.profile import trigger_after_summary
from app.models.entities import TaskStatus
from app.services.task_service import create_task, list_tasks, set_status, update_task
from app.services.completion_service import run_summary_generation


def build_task_tools(session_factory: Callable[[], Session]):
    @tool
    def create_task_tool(language: str, title: str, description: str = "") -> str:
        """新增一个学习任务；语言不存在时自动创建语言分类。"""
        with session_factory() as session:
            task = create_task(session, language, title, description)
        return json.dumps({"id": task.id, "language": task.language.name, "title": task.title}, ensure_ascii=False)

    @tool
    def update_task_tool(
        task_id: int,
        language: str | None = None,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
    ) -> str:
        """更新任务；status 只能是 todo/in_progress/completed。"""
        mapped = TaskStatus(status) if status else None
        with session_factory() as session:
            task = update_task(session, task_id, language, title, description, mapped)
        return json.dumps({"id": task.id, "title": task.title, "status": task.status.value}, ensure_ascii=False)

    @tool
    def list_tasks_tool(language: str | None = None, status: str | None = None, keyword: str | None = None) -> str:
        """按语言/状态/关键词查询学习任务，用于向用户汇报进度。"""
        mapped = TaskStatus(status) if status else None
        with session_factory() as session:
            rows = list_tasks(session, language, mapped, keyword)
        return json.dumps(
            [{"id": t.id, "language": t.language.name, "title": t.title, "status": t.status.value} for t in rows],
            ensure_ascii=False,
        )

    @tool
    def complete_task_tool(task_id: int) -> str:
        """标记任务完成并同步生成总结文件。"""
        with session_factory() as session:
            task = set_status(session, task_id, TaskStatus.completed)
        run_summary_generation(
            session_factory, task_id, after_success=trigger_after_summary
        )
        return f"任务「{task.title}」已完成，总结已生成或记录失败状态。"

    return [create_task_tool, update_task_tool, list_tasks_tool, complete_task_tool]
```

```python
# agents/tools/note_tools.py
from typing import Callable

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.services.note_service import init_note_file, read_note_content
from app.services.completion_service import run_summary_generation


def build_note_tools(session_factory: Callable[[], Session]):
    @tool
    def init_note_tool(task_id: int) -> str:
        """为任务初始化一份空的笔记文件（不覆盖已有内容）。"""
        with session_factory() as session:
            existing = read_note_content(session, task_id)
            if existing:
                return "笔记文件已存在，未做修改"
            row = init_note_file(session, task_id)
        return f"已创建笔记文件：{row.rel_path}"

    @tool
    def read_note_tool(task_id: int) -> str:
        """读取任务笔记正文，供总结或起草参考。"""
        with session_factory() as session:
            content = read_note_content(session, task_id)
        return content if content else "（笔记为空）"

    @tool
    def draft_note_tool(task_id: int, requirements: str) -> str:
        """读取任务笔记素材并返回起草要求；Agent 结合素材在聊天中起草，不写入文件。"""
        with session_factory() as session:
            content = read_note_content(session, task_id)
        return f"笔记素材：\n{content}\n\n起草要求：{requirements}"

    @tool
    def summarize_task_tool(task_id: int) -> str:
        """按用户要求生成或更新某任务的总结文件。"""
        run_summary_generation(session_factory, task_id)
        return "总结生成任务已执行，请查看任务详情中的总结。"

    return [init_note_tool, read_note_tool, draft_note_tool, summarize_task_tool]
```

```python
# agents/tools/__init__.py
from typing import Callable

from langchain_core.tools import BaseTool
from sqlalchemy.orm import Session

from agents.tools.language_tools import build_language_tools
from agents.tools.note_tools import build_note_tools
from agents.tools.task_tools import build_task_tools


def build_all_tools(session_factory: Callable[[], Session]) -> list[BaseTool]:
    return [
        *build_language_tools(session_factory),
        *build_task_tools(session_factory),
        *build_note_tools(session_factory),
    ]
```

```python
# agents/assistant.py
from typing import AsyncIterator, Callable

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from sqlalchemy.orm import Session

from agents.llm import build_chat_model
from agents.memory.conversation import load_langchain_history
from agents.tools import build_all_tools

SYSTEM_PROMPT = (
    "你是Prince-PA学习助理，帮助用户管理编程语言学习任务、笔记与总结。"
    "先理解用户意图，再调用工具完成任务。工具完成后用简体中文简洁汇报；"
    "绝不创建或代写学习记录，不直接改写用户笔记正文。"
)


def build_agent_executor(session_factory: Callable[[], Session]) -> AgentExecutor:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )
    agent = create_tool_calling_agent(build_chat_model(), build_all_tools(session_factory), prompt)
    return AgentExecutor(
        agent=agent,
        tools=build_all_tools(session_factory),
        handle_parsing_errors=True,
        max_iterations=6,
    )


async def stream_agent_response(
    session_factory: Callable[[], Session],
    session_id: int,
    user_text: str,
) -> AsyncIterator[dict]:
    with session_factory() as db:
        history = load_langchain_history(db, session_id)
    executor = build_agent_executor(session_factory)
    full_text = ""
    async for event in executor.astream_events(
        {"chat_history": history, "input": user_text}, version="v1"
    ):
        event_type = event["event"]
        if event_type == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            content = getattr(chunk, "content", None) if chunk is not None else None
            if isinstance(content, str) and content:
                full_text += content
                yield {"type": "token", "content": content}
        elif event_type == "on_tool_start":
            yield {"type": "tool_start", "name": event.get("name", ""), "input": event.get("data", {}).get("input")}
        elif event_type == "on_tool_end":
            yield {"type": "tool_end", "name": event.get("name", "")}
    yield {"type": "done"}
```

> 说明：聊天 API 负责在调用本函数前把用户消息落库，并在流结束后把助手完整
> 回复落库。本函数不负责持久化，工具调用细节通过 SSE 事件实时展示。

**Step 4: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_tools.py -v`
Expected: PASS（1 passed）。

**Step 5: 提交**

```bash
git add agents/tools agents/assistant.py tests/test_tools.py
git commit -m "实现Agent工具与对话编排"
```

---

### Task 13: 聊天与画像 REST API（SSE）

**Files:**
- Create: `Prince-PA/app/schemas/chat.py`
- Create: `Prince-PA/app/schemas/profile.py`
- Create: `Prince-PA/app/api/chat.py`
- Create: `Prince-PA/app/api/profile.py`
- Create: `Prince-PA/app/api/deps.py`
- Modify: `Prince-PA/app/main.py`
- Modify: `Prince-PA/tests/conftest.py`
- Create: `Prince-PA/tests/test_chat_api.py`

**Interfaces:**
- Consumes: `chat_service`、`profile`、`assistant.stream_agent_response`、`BackgroundTasks`。
- Produces:
  - `POST/GET /api/chat/sessions`
  - `GET /api/chat/sessions/{id}/messages`
  - `POST /api/chat/sessions/{id}/messages`（SSE）
  - `GET /api/profile`、`POST /api/profile/extract`
  - `POST /api/profile/preferences/{id}/confirm|dismiss`

**Step 1: 写失败测试**

```python
# tests/test_chat_api.py
import json

import app.api.chat as chat_api
from app.models.entities import MessageRole, PreferenceStatus, UserPreference


async def fake_stream(session_factory, session_id, user_text):
    yield {"type": "token", "content": "你好，"}
    yield {"type": "token", "content": "已创建任务。"}
    yield {"type": "done"}


def test_chat_send_message_stream(client, monkeypatch):
    monkeypatch.setattr(chat_api, "stream_agent_response", fake_stream)
    session_id = client.post("/api/chat/sessions").json()["id"]
    with client.stream(
        "POST",
        f"/api/chat/sessions/{session_id}/messages",
        json={"content": "帮我添加 Python 任务"},
    ) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())
    assert "你好，" in body
    assert "data:" in body
    messages = client.get(f"/api/chat/sessions/{session_id}/messages").json()
    assert [m["role"] for m in messages] == ["user", "assistant"]


def test_profile_confirm_and_snapshot(client, db_session):
    pref = UserPreference(
        user_id="local",
        dimension="response_style",
        value="简洁",
        source="auto",
        status=PreferenceStatus.pending,
        confidence=0.9,
    )
    db_session.add(pref)
    db_session.commit()

    pending = client.get("/api/profile").json()["pending"]
    assert len(pending) == 1
    resp = client.post(f"/api/profile/preferences/{pref.id}/confirm")
    assert resp.status_code == 200
    profile = client.get("/api/profile").json()["profile"]
    assert profile["response_style"]["value"] == "简洁"
```

**Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_chat_api.py -v`
Expected: FAIL。

**Step 3: 实现 schemas**

```python
# app/schemas/chat.py
from pydantic import BaseModel


class ChatRequest(BaseModel):
    content: str
```

```python
# app/schemas/profile.py
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
```

**Step 4: 实现路由**

```python
# app/api/chat.py
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from agents.assistant import stream_agent_response
from app.api.deps import get_session_factory
from app.core.database import get_db
from app.models.entities import MessageRole
from app.schemas.chat import ChatRequest
from app.services.chat_service import (
    create_message,
    create_session,
    get_session,
    list_messages,
    list_sessions,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/sessions")
def api_create_session(db: Session = Depends(get_db)):
    return create_session(db)


@router.get("/sessions")
def api_list_sessions(db: Session = Depends(get_db)):
    return list_sessions(db)


@router.get("/sessions/{session_id}/messages")
def api_list_messages(session_id: int, db: Session = Depends(get_db)):
    try:
        get_session(db, session_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="会话不存在")
    return list_messages(db, session_id)


@router.post("/sessions/{session_id}/messages")
def api_send_message(
    session_id: int,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    session_factory=Depends(get_session_factory),
):
    try:
        get_session(db, session_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="会话不存在")
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    create_message(db, session_id, MessageRole.user, payload.content)

    async def events():
        assistant_text = ""
        try:
            async for item in stream_agent_response(session_factory, session_id, payload.content):
                if item.get("type") == "token":
                    assistant_text += item["content"]
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)}, ensure_ascii=False)}\n\n"
        finally:
            with session_factory() as persist_db:
                create_message(persist_db, session_id, MessageRole.assistant, assistant_text or "（无回复）")

    return StreamingResponse(events(), media_type="text/event-stream")
```

```python
# app/api/deps.py
from app.core.database import SessionLocal


def get_session_factory():
    """供后台任务与流式生成获取独立 Session 工厂。"""
    return SessionLocal
```

```python
# app/api/profile.py
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from agents.memory import profile as memory_profile
from app.core.database import SessionLocal, get_db
from app.schemas.profile import PreferenceOut, ProfileSnapshotOut

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileSnapshotOut)
def api_get_profile(db: Session = Depends(get_db)):
    return ProfileSnapshotOut(
        profile=memory_profile.latest_profile(db),
        pending=[PreferenceOut.model_validate(p) for p in memory_profile.list_pending(db)],
    )


@router.post("/extract")
def api_extract_profile(background: BackgroundTasks):
    background.add_task(memory_profile.trigger_manual_extract, SessionLocal)
    return {"status": "started"}


@router.post("/preferences/{preference_id}/confirm", response_model=PreferenceOut)
def api_confirm_preference(preference_id: int, db: Session = Depends(get_db)):
    try:
        return memory_profile.confirm_preference(db, preference_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="偏好项不存在")


@router.post("/preferences/{preference_id}/dismiss", response_model=PreferenceOut)
def api_dismiss_preference(preference_id: int, db: Session = Depends(get_db)):
    try:
        return memory_profile.dismiss_preference(db, preference_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="偏好项不存在")
```

`app/main.py` 增加路由并挂载 API：

```python
from app.api import chat, languages, notes, profile, records, summaries, tasks

app.include_router(chat.router)
app.include_router(profile.router)
```

**Step 5: 运行测试确认通过**

先修改 `tests/conftest.py`，让客户端依赖与会话工厂都指向同一测试库：

```python
from app.api.deps import get_session_factory


@pytest.fixture()
def client(tmp_path):
    session_factory = _make_session(tmp_path)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    def override_session_factory():
        return session_factory

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session_factory] = override_session_factory
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_chat_api.py tests/test_memory.py -v`
Expected: PASS。

**Step 6: 提交**

```bash
git add app/schemas/chat.py app/schemas/profile.py app/api/chat.py app/api/profile.py app/main.py tests/test_chat_api.py
git commit -m "实现聊天SSE与用户画像REST API"
```

---

### Task 14: Vue 工程骨架与公共设施

**Files:**
- Create: `Prince-PA/web/package.json`
- Create: `Prince-PA/web/vite.config.ts`
- Create: `Prince-PA/web/tsconfig.json`
- Create: `Prince-PA/web/index.html`
- Create: `Prince-PA/web/.env.development`
- Create: `Prince-PA/web/src/main.ts`
- Create: `Prince-PA/web/src/App.vue`
- Create: `Prince-PA/web/src/router/index.ts`
- Create: `Prince-PA/web/src/utils/request.ts`
- Create: `Prince-PA/web/src/env.d.ts`
- Create: `Prince-PA/web/src/styles/main.css`

**Interfaces:**
- Produces:
  - `request`（axios 实例，读取 `VITE_API_BASE_URL`）
  - 路由：`/` → `TaskBoard`、`/tasks/:id/note` → `NoteEditor`

**Step 1: 初始文件**

```json
// web/package.json
{
  "name": "prince-pa-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "lint": "eslint . --ext .vue,.ts --fix"
  },
  "dependencies": {
    "@element-plus/icons-vue": "^2.3.1",
    "axios": "^1.7.7",
    "element-plus": "^2.8.4",
    "md-editor-v3": "^4.19.2",
    "pinia": "^2.2.2",
    "vue": "^3.5.6",
    "vue-router": "^4.4.3"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.1.2",
    "@vue/test-utils": "^2.4.6",
    "@types/node": "^20.14.0",
    "happy-dom": "^15.0.0",
    "typescript": "^5.5.4",
    "vite": "^5.4.3",
    "vitest": "^2.0.5",
    "vue-tsc": "^2.1.4"
  }
}
```

```jsonc
// web/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "jsx": "preserve",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "noEmit": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] },
    "types": ["vite/client", "vitest/globals", "node"]
  },
  "include": ["src/**/*.ts", "src/**/*.vue", "src/**/*.d.ts", "tests/**/*.ts", "vite.config.ts"]
}
```

```ts
// web/vite.config.ts
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://127.0.0.1:8002', changeOrigin: true } }
  },
  test: { environment: 'happy-dom' }
})
```

```ts
// web/src/utils/request.ts
import axios from 'axios'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 60000
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => Promise.reject(error?.response?.data || error)
)

export default request
```

```ts
// web/src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'board', component: () => import('@/views/TaskBoard.vue') },
    { path: '/tasks/:id/note', name: 'note', component: () => import('@/views/NoteEditor.vue') }
  ]
})

export default router
```

```vue
<!-- web/src/App.vue -->
<template>
  <RouterView />
</template>
```

```css
/* web/src/styles/main.css */
html, body, #app { height: 100%; margin: 0; }
body { font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }
```

```ts
// web/src/env.d.ts
/// <reference types="vite/client" />
```

`web/.env.development`：`VITE_API_BASE_URL=/api`

**Step 2: 安装依赖并跑通类型检查**

Run: `cd web; npm install; npm run build`
Expected: 构建成功。先创建可运行的最小视图（后续 Task 15、17 完整替换）：

```vue
<!-- web/src/views/TaskBoard.vue -->
<template><div>任务看板建设中</div></template>

<!-- web/src/views/NoteEditor.vue -->
<template><div>笔记编辑建设中</div></template>
```

**Step 3: 提交**

```bash
git add web
git commit -m "初始化Prince-PA前端Vue工程"
```

---

### Task 15: 任务看板（卡片/筛选/手动新增/状态流转）

**Files:**
- Create: `Prince-PA/web/src/types.ts`
- Create: `Prince-PA/web/src/stores/task.ts`
- Create: `Prince-PA/web/src/components/TaskFilter.vue`
- Create: `Prince-PA/web/src/components/TaskCard.vue`
- Create: `Prince-PA/web/src/components/TaskFormDialog.vue`
- Modify: `Prince-PA/web/src/views/TaskBoard.vue`
- Create: `Prince-PA/web/tests/taskStore.spec.ts`

**Interfaces:**
- Consumes: `request`。
- Produces:
  - `Task`/`TaskStatus`/`Language` 类型
  - `useTaskStore`：`languages`、`tasks`、`filter`、`fetchLanguages`、`fetchTasks`、`createTask`、`updateTask`、`startTask`、`completeTask`

**Step 1: 写失败测试**

```ts
// web/tests/taskStore.spec.ts
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/utils/request', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn()
  }
}))

import request from '@/utils/request'
import { useTaskStore } from '@/stores/task'

const get = request.get as ReturnType<typeof vi.fn>
const post = request.post as ReturnType<typeof vi.fn>

describe('task store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetch tasks and languages', async () => {
    get.mockResolvedValueOnce([{ id: 1, name: 'Python' }])
    get.mockResolvedValueOnce([{ id: 10, language: 'Python', title: 'LangChain', status: 'todo' }])
    const store = useTaskStore()
    await store.init()
    expect(store.languages.length).toBe(1)
    expect(store.tasks.length).toBe(1)
  })

  it('create task and complete', async () => {
    post.mockResolvedValueOnce({ id: 1, language: 'Python', title: 'T', status: 'todo' })
    post.mockResolvedValueOnce({ id: 1, language: 'Python', title: 'T', status: 'completed' })
    const store = useTaskStore()
    await store.createTask({ language: 'Python', title: 'T', description: '' })
    expect(post).toHaveBeenCalledWith('/tasks', expect.anything())
    await store.completeTask(1)
    expect(post).toHaveBeenCalledWith('/tasks/1/complete')
  })
})
```

**Step 2: 运行确认失败**

Run: `cd web; npx vitest run tests/taskStore.spec.ts`
Expected: FAIL（store 不存在）。

**Step 3: 实现类型与 store**

```ts
// web/src/types.ts
export type TaskStatus = 'todo' | 'in_progress' | 'completed'
export type SummaryStatus = 'pending' | 'success' | 'failed'

export interface Language { id: number; name: string }
export interface Task {
  id: number
  language: string
  title: string
  description: string
  status: TaskStatus
  summary_status: SummaryStatus
  summary_error?: string | null
  completed_at?: string | null
  created_at: string
  updated_at: string
}
export interface TaskCreatePayload { language: string; title: string; description: string }
```

```ts
// web/src/stores/task.ts
import { defineStore } from 'pinia'

import request from '@/utils/request'
import type { Language, Task, TaskCreatePayload, TaskStatus } from '@/types'

interface TaskFilter {
  language: string
  status: TaskStatus | ''
  keyword: string
}

export const useTaskStore = defineStore('task', {
  state: () => ({
    languages: [] as Language[],
    tasks: [] as Task[],
    filter: { language: '', status: '', keyword: '' } as TaskFilter
  }),
  actions: {
    async fetchLanguages() {
      this.languages = (await request.get('/languages')) as Language[]
    },
    async fetchTasks() {
      const params: Record<string, string> = {}
      if (this.filter.language) params.language = this.filter.language
      if (this.filter.status) params.status = this.filter.status
      if (this.filter.keyword) params.keyword = this.filter.keyword
      this.tasks = (await request.get('/tasks', { params })) as Task[]
    },
    async init() {
      await Promise.all([this.fetchLanguages(), this.fetchTasks()])
    },
    async createTask(payload: TaskCreatePayload) {
      const created = (await request.post('/tasks', payload)) as Task
      this.tasks.unshift(created)
      return created
    },
    async updateTask(id: number, data: Partial<Task>) {
      const updated = (await request.patch(`/tasks/${id}`, data)) as Task
      const index = this.tasks.findIndex((t) => t.id === id)
      if (index >= 0) this.tasks[index] = updated
      return updated
    },
    async startTask(id: number) {
      const updated = (await request.post(`/tasks/${id}/start`)) as Task
      const index = this.tasks.findIndex((t) => t.id === id)
      if (index >= 0) this.tasks[index] = updated
      return updated
    },
    async completeTask(id: number) {
      const updated = (await request.post(`/tasks/${id}/complete`)) as Task
      const index = this.tasks.findIndex((t) => t.id === id)
      if (index >= 0) this.tasks[index] = updated
      return updated
    }
  }
})
```

**Step 4: 实现看板视图与组件**

`TaskFilter.vue`：三个控件绑定 store.filter，`@change` 调 `fetchTasks`。
`TaskCard.vue`：props `task: Task`；展示语言徽标、状态 `el-tag`、描述；触发事件
`start`/`complete`（调用对应 store action），并提供【笔记】按钮路由 `/tasks/${id}/note`。
`TaskFormDialog.vue`：props `modelValue`；表单含语言（`el-select` 允许创建）+ 标题 + 描述；提交调 `store.createTask`。

`TaskBoard.vue` 主模板：

```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import TaskCard from '@/components/TaskCard.vue'
import TaskFilter from '@/components/TaskFilter.vue'
import TaskFormDialog from '@/components/TaskFormDialog.vue'
import { useTaskStore } from '@/stores/task'

const store = useTaskStore()
const showForm = ref(false)
onMounted(() => store.init())
</script>

<template>
  <div class="board-layout">
    <aside class="left-filter">
      <TaskFilter />
      <el-button class="profile-entry" text>用户画像/偏好</el-button>
    </aside>
    <main class="center">
      <header>
        <h2>学习任务</h2>
        <el-button type="primary" @click="showForm = true">新增任务</el-button>
      </header>
      <div class="task-grid">
        <TaskCard
          v-for="task in store.tasks"
          :key="task.id"
          :task="task"
          @start="store.startTask(task.id)"
          @complete="store.completeTask(task.id)"
        />
      </div>
    </main>
    <TaskFormDialog v-model="showForm" />
  </div>
</template>
```

样式要点：`.board-layout { display: grid; grid-template-columns: 240px 1fr; height: 100vh; }`；
`.task-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }`。
聊天窗第三列由 Task 18 加入；任务【详情】入口由 Task 16 加入。

**Step 5: 运行测试与构建**

Run: `cd web; npx vitest run; npm run build`
Expected: PASS + 构建成功。

**Step 6: 提交**

```bash
git add web/src web/tests
git commit -m "实现任务看板与任务状态流转"
```

---

### Task 16: 任务详情与学习记录

**Files:**
- Create: `Prince-PA/web/src/stores/record.ts`
- Create: `Prince-PA/web/src/components/TaskDetailDrawer.vue`
- Modify: `Prince-PA/web/src/components/TaskCard.vue`
- Modify: `Prince-PA/web/src/views/TaskBoard.vue`
- Create: `Prince-PA/web/tests/recordStore.spec.ts`

**Interfaces:**
- Consumes: `request`、任务 store。
- Produces:
  - `useRecordStore`：`records`、`fetchByTask(taskId)`、`addManual(taskId, startedAt, content)`。
  - `TaskDetailDrawer` 事件 `openNote(taskId)`、`complete(taskId)`。

**Step 1: 写失败测试**

```ts
// web/tests/recordStore.spec.ts
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/utils/request', () => ({ default: { get: vi.fn(), post: vi.fn() } }))

import request from '@/utils/request'
import { useRecordStore } from '@/stores/record'

const get = request.get as ReturnType<typeof vi.fn>
const post = request.post as ReturnType<typeof vi.fn>

describe('record store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetches records by task', async () => {
    get.mockResolvedValue([{ id: 1, task_id: 1, record_type: 'auto', content: '', started_at: '2026-09-06T10:00:00Z' }])
    const store = useRecordStore()
    await store.fetchByTask(1)
    expect(get).toHaveBeenCalledWith('/tasks/1/records')
    expect(store.records.length).toBe(1)
  })

  it('adds manual record', async () => {
    post.mockResolvedValue({ id: 2, task_id: 1, record_type: 'manual', content: '心得', started_at: '2026-09-06T10:00:00Z' })
    const store = useRecordStore()
    await store.addManual(1, '2026-09-06T10:00:00Z', '心得')
    expect(post).toHaveBeenCalledWith('/tasks/1/records', expect.anything())
  })
})
```

**Step 2: 运行确认失败**

Run: `cd web; npx vitest run tests/recordStore.spec.ts`
Expected: FAIL。

**Step 3: 实现 store 与抽屉**

```ts
// web/src/stores/record.ts
import { defineStore } from 'pinia'

import request from '@/utils/request'

export interface LearningRecord {
  id: number
  task_id: number
  record_type: 'auto' | 'manual'
  content: string
  started_at: string
  created_at: string
}

export const useRecordStore = defineStore('record', {
  state: () => ({ records: [] as LearningRecord[] }),
  actions: {
    async fetchByTask(taskId: number) {
      this.records = (await request.get(`/tasks/${taskId}/records`)) as LearningRecord[]
    },
    async addManual(taskId: number, startedAt: string, content: string) {
      const row = (await request.post(`/tasks/${taskId}/records`, { started_at: startedAt, content })) as LearningRecord
      this.records.unshift(row)
      return row
    }
  }
})
```

`TaskDetailDrawer.vue` 使用 Element Plus `el-drawer`（`size="45%"`）：

```vue
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import request from '@/utils/request'
import type { Task } from '@/types'
import { useRecordStore } from '@/stores/record'

const props = defineProps<{ task: Task | null }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'openNote', id: number): void }>()

const recordStore = useRecordStore()
const visible = computed(() => props.task !== null)
const manualTime = ref(new Date().toISOString().slice(0, 16))
const manualContent = ref('')
const summary = ref<{ status: string; content: string | null; error: string | null } | null>(null)

watch(visible, async (show) => {
  if (show && props.task) {
    await recordStore.fetchByTask(props.task.id)
    summary.value = (await request.get(`/tasks/${props.task.id}/summary`)) as typeof summary.value
  }
})

async function submitManual() {
  if (!props.task) return
  await recordStore.addManual(props.task.id, new Date(manualTime.value).toISOString(), manualContent.value)
  manualContent.value = ''
}

async function regenerateSummary() {
  if (!props.task) return
  await request.post(`/tasks/${props.task.id}/summary/regenerate`)
  summary.value = (await request.get(`/tasks/${props.task.id}/summary`)) as typeof summary.value
}
</script>

<template>
  <el-drawer :model-value="visible" title="任务详情" @close="emit('close')">
    <template v-if="task">
      <h2>{{ task.language }} / {{ task.title }}</h2>
      <p>{{ task.description }}</p>
      <el-button @click="emit('openNote', task.id)">打开笔记</el-button>
      <el-divider>学习记录</el-divider>
      <el-timeline>
        <el-timeline-item v-for="row in recordStore.records" :key="row.id" :timestamp="row.started_at">
          {{ row.record_type === 'auto' ? '自动' : '手动' }} · {{ row.content || '开始学习' }}
        </el-timeline-item>
      </el-timeline>
      <el-form label-width="90px">
        <el-form-item label="开始时间"><el-date-picker v-model="manualTime" type="datetime" /></el-form-item>
        <el-form-item label="内容"><el-input v-model="manualContent" type="textarea" /></el-form-item>
        <el-button type="primary" @click="submitManual">手动登记</el-button>
      </el-form>
      <el-divider>总结</el-divider>
      <el-alert v-if="summary?.status === 'failed'" :title="summary?.error" type="error" />
      <el-button v-if="summary?.status !== 'success'" @click="regenerateSummary">重新生成总结</el-button>
      <el-text v-else>总结已生成，可在笔记页查看</el-text>
    </template>
  </el-drawer>
</template>
```

在 `TaskCard.vue` 增加【详情】按钮，发射 `detail` 事件；`TaskBoard.vue` 的
`<script setup>` 增加：

```ts
import { useRouter } from 'vue-router'
import TaskDetailDrawer from '@/components/TaskDetailDrawer.vue'
import type { Task } from '@/types'

const router = useRouter()
const selectedTask = ref<Task | null>(null)
function openNote(id: number) {
  router.push(`/tasks/${id}/note`)
}
```

模板渲染 `<TaskDetailDrawer :task="selectedTask" @close="selectedTask = null" @open-note="openNote" />`。

**Step 4: 运行测试与构建**

Run: `cd web; npx vitest run; npm run build`
Expected: PASS + 构建成功。

**Step 5: 提交**

```bash
git add web/src/stores/record.ts web/src/components web/src/views web/tests
git commit -m "实现任务详情与学习记录登记"
```

---

### Task 17: Markdown 笔记编辑器（三栏 + 可拖拽）

**Files:**
- Create: `Prince-PA/web/src/stores/note.ts`
- Create: `Prince-PA/web/src/components/ResizableSplit.vue`
- Create: `Prince-PA/web/src/utils/resize.ts`
- Modify: `Prince-PA/web/src/views/NoteEditor.vue`
- Create: `Prince-PA/web/tests/noteStore.spec.ts`
- Create: `Prince-PA/web/tests/resize.spec.ts`

**Interfaces:**
- Consumes: `request`、`md-editor-v3`、任务/记录接口。
- Produces:
  - `useNoteStore`：`load(taskId)`、`save()`、`task`、`content`、`summary`
  - `applyRatio(ratio, total, minRatio)` 计算左右百分比

**Step 1: 写失败测试**

```ts
// web/tests/noteStore.spec.ts
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/utils/request', () => ({ default: { get: vi.fn(), put: vi.fn() } }))

import request from '@/utils/request'
import { useNoteStore } from '@/stores/note'

const get = request.get as ReturnType<typeof vi.fn>
const put = request.put as ReturnType<typeof vi.fn>

describe('note store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads task note and summary', async () => {
    get.mockResolvedValueOnce({ id: 1, language: 'Python', title: 'LangChain' })
    get.mockResolvedValueOnce({ content: '# 笔记' })
    get.mockResolvedValueOnce({ status: 'success', content: '# 总结', error: null })
    const store = useNoteStore()
    await store.load(1)
    expect(store.content).toBe('# 笔记')
    expect(store.summary?.content).toBe('# 总结')
  })

  it('saves note', async () => {
    put.mockResolvedValue({ content: 'new' })
    const store = useNoteStore()
    store.taskId = 1
    store.content = 'new'
    await store.save()
    expect(put).toHaveBeenCalledWith('/tasks/1/note', { content: 'new' })
  })
})
```

```ts
// web/tests/resize.spec.ts
import { describe, expect, it } from 'vitest'
import { applyRatio } from '@/utils/resize'

describe('applyRatio', () => {
  it('clamps and converts ratio to percent', () => {
    expect(applyRatio(-1, 100, 0.2)).toBe(20)
    expect(applyRatio(0.5, 100, 0.2)).toBe(50)
    expect(applyRatio(2, 100, 0.2)).toBe(80)
  })
})
```

**Step 2: 运行确认失败**

Run: `cd web; npx vitest run tests/noteStore.spec.ts tests/resize.spec.ts`
Expected: FAIL。

**Step 3: 实现 store 与比例工具**

```ts
// web/src/utils/resize.ts
export function applyRatio(ratio: number, total: number, minRatio: number): number {
  const min = total * minRatio
  const max = total * (1 - minRatio)
  return Math.min(max, Math.max(min, ratio)) / total * 100
}
```

```ts
// web/src/stores/note.ts
import { defineStore } from 'pinia'

import request from '@/utils/request'
import type { Task } from '@/types'

export const useNoteStore = defineStore('note', {
  state: () => ({
    taskId: 0,
    task: null as Task | null,
    content: '',
    dirty: false,
    summary: null as { status: string; content: string | null; error: string | null } | null
  }),
  actions: {
    async load(taskId: number) {
      this.taskId = taskId
      const [task, note, summary] = await Promise.all([
        request.get(`/tasks/${taskId}`),
        request.get(`/tasks/${taskId}/note`),
        request.get(`/tasks/${taskId}/summary`)
      ])
      this.task = task as Task
      this.content = (note as { content: string }).content
      this.summary = summary as typeof this.summary
      this.dirty = false
    },
    setContent(content: string) {
      this.content = content
      this.dirty = true
    },
    async save() {
      await request.put(`/tasks/${this.taskId}/note`, { content: this.content })
      this.dirty = false
    }
  }
})
```

**Step 4: 实现编辑器三栏**

`ResizableSplit.vue`：props `leftRatio: number`，emits `update:leftRatio`；渲染两个
`slot` 与拖拽分隔条；`@mousedown` 时记录起点，`pointermove` 按容器宽度换算比例并 emit。

```vue
<!-- web/src/components/ResizableSplit.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { applyRatio } from '@/utils/resize'

const props = defineProps<{ leftRatio: number }>()
const emit = defineEmits<{ (e: 'update:leftRatio', value: number): void }>()
const root = ref<HTMLDivElement | null>(null)

function onPointerDown(e: PointerEvent) {
  const startX = e.clientX
  const startRatio = props.leftRatio
  const onMove = (ev: PointerEvent) => {
    const rect = root.value?.getBoundingClientRect()
    if (!rect) return
    const nextRatio = startRatio + (ev.clientX - startX) / rect.width
    emit('update:leftRatio', applyRatio(nextRatio, 1, 0.2))
  }
  const onUp = () => {
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
  }
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
}
</script>

<template>
  <div ref="root" class="resizable-split">
    <div class="pane left-pane" :style="{ flexBasis: `${leftRatio}%` }">
      <slot name="left" />
    </div>
    <div class="divider" @pointerdown="onPointerDown" />
    <div class="pane right-pane" :style="{ flexBasis: `${100 - leftRatio}%` }">
      <slot name="right" />
    </div>
  </div>
</template>

<style scoped>
.resizable-split { display: flex; width: 100%; height: 100%; overflow: hidden; }
.pane { min-width: 0; overflow: hidden; }
.divider { width: 6px; cursor: col-resize; background: #d1d5db; flex: 0 0 6px; }
</style>
```

```vue
<!-- web/src/views/NoteEditor.vue -->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MdEditor, MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import { ElMessage } from 'element-plus'
import { useNoteStore } from '@/stores/note'
import ResizableSplit from '@/components/ResizableSplit.vue'

const route = useRoute()
const router = useRouter()
const noteStore = useNoteStore()
const taskId = Number(route.params.id)
const leftRatio = ref(50)
const saving = ref(false)
const contentModel = computed({
  get: () => noteStore.content,
  set: (value: string) => noteStore.setContent(value)
})

onMounted(async () => {
  await noteStore.load(taskId)
})

async function saveNote() {
  saving.value = true
  await noteStore.save()
  saving.value = false
  ElMessage.success('已保存')
}

function onKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault()
    void saveNote()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

const summaryText = computed(() => noteStore.summary?.content || '总结尚未生成')
</script>

<template>
  <div class="editor-page">
    <aside class="task-info">
      <el-button text @click="router.push('/')">← 返回看板</el-button>
      <h2>{{ noteStore.task?.language }} / {{ noteStore.task?.title }}</h2>
      <p>{{ noteStore.task?.description }}</p>
      <el-divider>总结（Agent 生成）</el-divider>
      <MdPreview :model-value="summaryText" preview-theme="default" />
      <el-button @click="saveNote" :loading="saving">保存笔记</el-button>
    </aside>
    <ResizableSplit v-model:left-ratio="leftRatio" class="split">
      <template #left>
        <MdEditor
          v-model="contentModel"
          :preview="false"
          :toolbars="['bold', 'italic', 'heading', 'code', 'quote', 'unorderedList', 'orderedList', 'link', 'image', 'preview']"
        />
      </template>
      <template #right>
        <div class="preview-pane">
          <MdPreview :model-value="noteStore.content" />
        </div>
      </template>
    </ResizableSplit>
  </div>
</template>

<style scoped>
.editor-page { display: flex; height: 100vh; }
.task-info { width: 20%; min-width: 220px; border-right: 1px solid #ddd; padding: 16px; overflow-y: auto; }
.split { flex: 1; display: flex; min-width: 0; }
</style>
```

说明：
- 左栏任务详情固定约 1/5；中右两栏通过 `ResizableSplit` 平分并可拖动调整。
- `MdEditor v-model` 与 `@on-change` 同时更新 store；`MdPreview` 实时预览同一内容。
- 本页不渲染 `ChatPanel`，满足“编辑笔记时隐藏聊天窗”。

**Step 5: 运行测试与构建**

Run: `cd web; npx vitest run; npm run build`
Expected: PASS + 构建成功。

**Step 6: 提交**

```bash
git add web/src web/tests
git commit -m "实现Markdown笔记编辑器与可拖拽分栏"
```

---

### Task 18: 聊天面板（流式对话）

**Files:**
- Create: `Prince-PA/web/src/utils/sse.ts`
- Create: `Prince-PA/web/src/stores/chat.ts`
- Replace: `Prince-PA/web/src/components/ChatPanel.vue`
- Modify: `Prince-PA/web/src/views/TaskBoard.vue`
- Create: `Prince-PA/web/tests/chatStore.spec.ts`
- Create: `Prince-PA/web/tests/sse.spec.ts`

**Interfaces:**
- Consumes: `/api/chat`（POST SSE）、`request`。
- Produces:
  - `parseSseBlock(raw: string): { type: string; content?: string; name?: string } | null`
  - `useChatStore`：`sessions`、`messages`、`streaming`、`init`、`newSession`、`send`

**Step 1: 写失败测试**

```ts
// web/tests/sse.spec.ts
import { describe, expect, it } from 'vitest'
import { parseSseBlock } from '@/utils/sse'

describe('parseSseBlock', () => {
  it('parses data json event', () => {
    const event = parseSseBlock('data: {"type":"token","content":"你好"}\n\n')
    expect(event?.type).toBe('token')
    expect(event?.content).toBe('你好')
  })
})
```

```ts
// web/tests/chatStore.spec.ts
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/utils/request', () => ({ default: { get: vi.fn(), post: vi.fn() } }))

import request from '@/utils/request'
import { useChatStore } from '@/stores/chat'

const get = request.get as ReturnType<typeof vi.fn>
const post = request.post as ReturnType<typeof vi.fn>

function streamResponse(...chunks: string[]) {
  return new Response(new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(new TextEncoder().encode(chunk)))
      controller.close()
    }
  }))
}

describe('chat store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.stubGlobal('fetch', vi.fn())
  })

  it('reads SSE and collects assistant text', async () => {
    get.mockResolvedValue([{ id: 1, title: '新会话' }])
    post.mockResolvedValue({ id: 1 })
    const fetchMock = fetch as ReturnType<typeof vi.fn>
    fetchMock.mockResolvedValue(streamResponse(
      'data: {"type":"token","content":"已创建"}\n\n',
      'data: {"type":"done"}\n\n'
    ))

    const store = useChatStore()
    await store.init()
    await store.newSession()
    await store.send('帮我加任务')

    expect(fetchMock).toHaveBeenCalled()
    expect(store.messages.at(-1)?.content).toContain('已创建')
  })
})
```

**Step 2: 运行确认失败**

Run: `cd web; npx vitest run tests/sse.spec.ts tests/chatStore.spec.ts`
Expected: FAIL。

**Step 3: 实现 SSE 解析与 chat store**

```ts
// web/src/utils/sse.ts
export function parseSseBlock(raw: string): { type: string; content?: string; name?: string } | null {
  const lines = raw.split('\n')
  const dataLine = lines.find((line) => line.startsWith('data:'))
  if (!dataLine) return null
  try {
    return JSON.parse(dataLine.slice(5).trim())
  } catch {
    return null
  }
}
```

```ts
// web/src/stores/chat.ts
import { defineStore } from 'pinia'

import request from '@/utils/request'
import { parseSseBlock } from '@/utils/sse'

export interface ChatMessage { role: 'user' | 'assistant'; content: string }
export interface ChatSession { id: number; title: string }

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessions: [] as ChatSession[],
    activeSessionId: 0,
    messages: [] as ChatMessage[],
    streaming: false
  }),
  actions: {
    async init() {
      this.sessions = (await request.get('/chat/sessions')) as ChatSession[]
      if (this.sessions.length === 0) await this.newSession()
      else await this.select(this.sessions[0].id)
    },
    async newSession() {
      const session = (await request.post('/chat/sessions')) as ChatSession
      this.sessions.unshift(session)
      await this.select(session.id)
    },
    async select(sessionId: number) {
      this.activeSessionId = sessionId
      const rows = (await request.get(`/chat/sessions/${sessionId}/messages`)) as Array<{ role: string; content: string }>
      this.messages = rows.map((row) => ({ role: row.role as ChatMessage['role'], content: row.content || '' }))
    },
    async send(content: string) {
      if (!this.activeSessionId || this.streaming) return
      this.streaming = true
      this.messages.push({ role: 'user', content })
      this.messages.push({ role: 'assistant', content: '' })
      const base = import.meta.env.VITE_API_BASE_URL || '/api'
      try {
        const response = await fetch(`${base}/chat/sessions/${this.activeSessionId}/messages`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content })
        })
        const reader = response.body?.getReader()
        if (!reader) return
        const decoder = new TextDecoder()
        let buffer = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const blocks = buffer.split('\n\n')
          buffer = blocks.pop() || ''
          for (const block of blocks) {
            const event = parseSseBlock(block)
            if (!event) continue
            if (event.type === 'token') {
              const last = this.messages.at(-1)
              if (last?.role === 'assistant') last.content += event.content || ''
            } else if (event.type === 'error') {
              const last = this.messages.at(-1)
              if (last?.role === 'assistant') last.content = `（错误）${event.content || ''}`
            }
          }
        }
      } catch (error) {
        const last = this.messages.at(-1)
        if (last?.role === 'assistant') last.content = `（请求失败）${String(error)}`
      } finally {
        this.streaming = false
      }
    }
  }
})
```

**Step 4: 实现 ChatPanel**

```vue
<!-- web/src/components/ChatPanel.vue -->
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useChatStore } from '@/stores/chat'

const store = useChatStore()
const input = ref('')

onMounted(() => store.init())

async function sendMessage() {
  const text = input.value.trim()
  if (!text) return
  input.value = ''
  await store.send(text)
}
</script>

<template>
  <section class="chat-panel">
    <header class="chat-header">
      <el-button text @click="store.newSession">＋ 新会话</el-button>
      <el-select :model-value="store.activeSessionId" @update:model-value="store.select" size="small">
        <el-option v-for="s in store.sessions" :key="s.id" :value="s.id" :label="s.title" />
      </el-select>
    </header>
    <div class="messages">
      <div v-for="(m, index) in store.messages" :key="index" class="message" :class="m.role">
        <pre>{{ m.content }}</pre>
      </div>
    </div>
    <footer class="chat-input">
      <el-input v-model="input" type="textarea" :rows="2" @keydown.enter.exact.prevent="sendMessage" placeholder="告诉学习助理你想做什么…" />
      <el-button type="primary" :loading="store.streaming" @click="sendMessage">发送</el-button>
    </footer>
  </section>
</template>

<style scoped>
.chat-panel { display: flex; flex-direction: column; height: 100vh; border-left: 1px solid #e5e7eb; }
.chat-header { padding: 12px; border-bottom: 1px solid #eee; display: flex; gap: 8px; }
.messages { flex: 1; overflow-y: auto; padding: 12px; }
.message { margin-bottom: 10px; }
.message.user { text-align: right; }
.message pre { white-space: pre-wrap; background: #f3f4f6; border-radius: 8px; padding: 8px; }
.message.user pre { background: #3b82f6; color: #fff; }
.chat-input { padding: 12px; border-top: 1px solid #eee; }
</style>
```

会话标题默认“新会话”：Task 20 之前保持“新会话”；聊天历史按会话持久化，
重新打开页面后能继续原会话。

将 `TaskBoard.vue` 改为三列布局：引入

```vue
import ChatPanel from '@/components/ChatPanel.vue'
```

并在 `<main>` 之后渲染 `<ChatPanel class="right-chat" />`，样式改为
`grid-template-columns: 240px 1fr 360px`。聊天窗此时常驻看板右侧。

**Step 5: 运行测试与构建**

Run: `cd web; npx vitest run; npm run build`
Expected: PASS + 构建成功。

**Step 6: 提交**

```bash
git add web/src/utils/sse.ts web/src/stores/chat.ts web/src/components/ChatPanel.vue web/tests
git commit -m "实现聊天面板与SSE流式对话"
```

---

### Task 19: 用户画像/偏好面板

**Files:**
- Create: `Prince-PA/web/src/stores/profile.ts`
- Create: `Prince-PA/web/src/components/ProfilePanel.vue`
- Modify: `Prince-PA/web/src/components/TaskFilter.vue`
- Modify: `Prince-PA/web/src/views/TaskBoard.vue`
- Create: `Prince-PA/web/tests/profileStore.spec.ts`

**Interfaces:**
- Produces:
  - `useProfileStore`：`profile`、`pending`、`fetch`、`extract`、`confirm`、`dismiss`
  - `ProfilePanel`（dialog）

**Step 1: 写失败测试**

```ts
// web/tests/profileStore.spec.ts
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/utils/request', () => ({ default: { get: vi.fn(), post: vi.fn() } }))

import request from '@/utils/request'
import { useProfileStore } from '@/stores/profile'

const get = request.get as ReturnType<typeof vi.fn>
const post = request.post as ReturnType<typeof vi.fn>

describe('profile store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetches and confirms preference', async () => {
    get.mockResolvedValue({ profile: {}, pending: [{ id: 1, dimension: 'summary_style', value: '详细' }] })
    post.mockResolvedValue({ id: 1, dimension: 'summary_style', value: '详细', status: 'confirmed' })
    const store = useProfileStore()
    await store.fetch()
    expect(store.pending.length).toBe(1)
    await store.confirm(1)
    expect(post).toHaveBeenCalledWith('/profile/preferences/1/confirm')
    expect(store.pending.length).toBe(0)
  })
})
```

**Step 2: 运行确认失败**

Run: `cd web; npx vitest run tests/profileStore.spec.ts`
Expected: FAIL。

**Step 3: 实现 store 与面板**

```ts
// web/src/stores/profile.ts
import { defineStore } from 'pinia'

import request from '@/utils/request'

export interface Preference {
  id: number
  dimension: string
  value: string
  source: 'auto' | 'manual'
  status: 'pending' | 'confirmed' | 'dismissed'
  confidence: number
  evidence?: string | null
}

export const useProfileStore = defineStore('profile', {
  state: () => ({
    profile: {} as Record<string, { value: string }>,
    pending: [] as Preference[],
    visible: false
  }),
  actions: {
    async fetch() {
      const data = (await request.get('/profile')) as { profile: Record<string, { value: string }>; pending: Preference[] }
      this.profile = data.profile
      this.pending = data.pending
    },
    async extract() {
      await request.post('/profile/extract')
      await this.fetch()
    },
    async confirm(id: number) {
      const updated = (await request.post(`/profile/preferences/${id}/confirm`)) as Preference
      this.pending = this.pending.filter((item) => item.id !== id)
      this.profile[updated.dimension] = { value: updated.value }
    },
    async dismiss(id: number) {
      await request.post(`/profile/preferences/${id}/dismiss`)
      this.pending = this.pending.filter((item) => item.id !== id)
    },
    async open() {
      this.visible = true
      await this.fetch()
    }
  }
})
```

`ProfilePanel.vue`：

```vue
<script setup lang="ts">
import { useProfileStore } from '@/stores/profile'

const store = useProfileStore()

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

async function runExtract() {
  await store.extract()
  for (let i = 0; i < 10 && store.pending.length === 0; i += 1) {
    await sleep(1000)
    await store.fetch()
  }
}
</script>

<template>
  <el-dialog v-model="store.visible" title="用户画像/偏好" width="60%">
    <el-button @click="runExtract">立即提炼</el-button>
    <el-divider>待确认偏好</el-divider>
    <el-empty v-if="store.pending.length === 0" description="暂无待确认项" />
    <el-card v-for="item in store.pending" :key="item.id" class="pending-item">
      <p>{{ item.dimension }}：{{ item.value }}</p>
      <el-text type="info">{{ item.evidence }}</el-text>
      <div>
        <el-button type="primary" @click="store.confirm(item.id)">确认</el-button>
        <el-button @click="store.dismiss(item.id)">忽略</el-button>
      </div>
    </el-card>
    <el-divider>当前画像</el-divider>
    <pre>{{ store.profile }}</pre>
  </el-dialog>
</template>
```

在 `TaskFilter.vue` 底部增加【用户画像/偏好】按钮，调用 `profileStore.open()`；
`TaskBoard.vue` 渲染 `<ProfilePanel />`。

**Step 4: 运行测试与构建**

Run: `cd web; npx vitest run; npm run build`
Expected: PASS + 构建成功。

**Step 5: 提交**

```bash
git add web/src/stores/profile.ts web/src/components/ProfilePanel.vue web/src/views web/src/components/TaskFilter.vue web/tests
git commit -m "实现用户画像偏好面板"
```

---

### Task 20: FastAPI 托管前端与收尾

**Files:**
- Modify: `Prince-PA/app/main.py`
- Modify: `Prince-PA/AGENTS.md`
- Create: `Prince-PA/README.md`
- Run: 后端与前端全量测试

**Interfaces:**
- 生产路径：`GET /` 返回 `web/dist/index.html`；`/assets/*` 由 StaticFiles 提供；`/api/*` 仍走 FastAPI 路由。

**Step 1: 修改 main.py 托管 dist**

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import chat, languages, notes, profile, records, summaries, tasks
from app.core.errors import install_exception_handlers

app = FastAPI(title="Prince-PA", version="0.1.0")
install_exception_handlers(app)
app.include_router(languages.router)
app.include_router(tasks.router)
app.include_router(notes.router)
app.include_router(summaries.router)
app.include_router(records.router)
app.include_router(chat.router)
app.include_router(profile.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


WEB_DIST = Path(__file__).resolve().parents[1] / "web" / "dist"
if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="接口不存在")
        candidate = WEB_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(WEB_DIST / "index.html")
```

**Step 2: 端到端验证**

后端：

```bash
python -m pytest -v
```

前端：

```bash
cd web
npm run test
npm run build
```

本地启动：

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

打开 `http://127.0.0.1:8002/`：应看到任务看板与聊天窗；创建任务后开始学习/完成；
进入任务笔记页出现三栏编辑器；刷新后聊天历史仍在。

**Step 3: 更新 AGENTS.md 与 README**

在 `AGENTS.md`“常用命令”表格中替换为实际命令：

```text
| 创建虚拟环境 | python -m venv .venv |
| 安装后端依赖 | pip install -r requirements.txt |
| 安装前端依赖 | cd web; npm install |
| 前端构建 | cd web; npm run build |
| 后端启动 | python -m uvicorn app.main:app --host 127.0.0.1 --port 8002 |
| 后端测试 | python -m pytest |
| 前端测试/构建 | cd web; npm run test; npm run build |
| 代码检查 | ruff check . |
```

`README.md` 摘要：项目用途、目录结构、本地启动步骤、数据目录与 `.env` 说明、
指向 PRD 与设计文档的链接。

**Step 4: 提交**

```bash
git add app/main.py AGENTS.md README.md web/dist
git commit -m "托管前端并收尾项目文档"
```

> `web/dist` 被 `.gitignore` 忽略，实际构建产物不会入库；提交仍只包含 main.py 与文档改动。

---

## 收尾检查清单

- [ ] 每个任务的测试均为先失败后通过。
- [ ] 后端 `pytest` 全绿。
- [ ] 前端 `vitest run` 与 `npm run build` 全绿。
- [ ] `http://127.0.0.1:8002` 手动验收主流程。
- [ ] `.env` 未入库；`DEEPSEEK_API_KEY` 由用户配置。
- [ ] 任务完成后总结自动生成；无 Key 时失败状态可重试。
- [ ] 画像自动提炼仅在总结成功后触发；偏好确认后才入库。
