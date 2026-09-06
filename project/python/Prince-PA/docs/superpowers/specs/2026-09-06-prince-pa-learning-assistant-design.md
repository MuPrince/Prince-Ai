# Prince-PA 个人 Agent 开发学习助理 — 设计文档

- 日期：2026-09-06
- 状态：待审阅
- 项目位置：`project/python/Prince-PA`

## 1. 背景与目标

Prince-PA 是一个本地运行的个人学习助理，帮助用户学习 AI Agent 开发。学习内容涵盖
Python、Java、TypeScript 等多种编程语言；学习任务以**编程语言作为一级分类**。

目标：

- 通过常驻聊天窗口，用自然语言让 Agent 添加、更新、查询任务并汇报进度。
- 通过任务看板手动管理任务，以卡片形式呈现。
- 以真实 `.md` 文件保存学习笔记，总结由 Agent 在任务完成时自动生成，并与任务、笔记关联。
- 自动或手动记录学习开始时间，形成可回顾的学习记录。

## 2. 范围

### MVP 内

- 语言分类与任务管理（增、查、改、状态流转）。
- LangChain + DeepSeek 对话 Agent，提供任务与笔记相关工具。
- 任务完成时自动生成/更新总结文件。
- 学习记录：看板“开始学习”自动生成；详情页手动登记。
- Markdown 笔记编辑（编辑区 + 预览区），支持拖动调整。
- 聊天历史持久化与 SSE 流式回复。

### MVP 外（暂不实现）

- 登录鉴权、多用户。
- 学习时长统计、计时器。
- Agent 代写学习记录或直接改写用户笔记文件。
- `skills/` 插件化能力（目录预留，暂不使用）。
- 移动端适配。

## 3. 总体架构与项目结构

FastAPI 提供 REST API 并托管 Vue 3 构建产物；Agent 使用 LangChain 接入 DeepSeek；
内容文件使用真实 Markdown，结构化数据使用 SQLite。

```text
Prince-PA/
├── AGENTS.md
├── requirements.txt
├── .env                        # DEEPSEEK_API_KEY 等，由用户自管
├── data/                       # 运行时数据，不提交 git
│   ├── notes/<语言>/<主题>.md
│   ├── notes/<语言>/<主题>-总结.md
│   └── app.db
├── app/                        # FastAPI
│   ├── main.py
│   ├── api/
│   │   ├── tasks.py
│   │   ├── notes.py
│   │   ├── records.py
│   │   ├── summaries.py
│   │   └── chat.py
│   ├── core/
│   │   ├── config.py           # .env / pydantic-settings
│   │   ├── database.py         # SQLAlchemy session
│   │   └── errors.py           # 统一异常与响应
│   ├── models/                 # ORM
│   ├── schemas/                # Pydantic
│   └── services/
│       ├── task_service.py
│       ├── note_service.py     # .md 读写与路径管理
│       ├── record_service.py
│       ├── summary_service.py  # 元数据与状态
│       └── completion_service.py
├── agents/
│   ├── llm.py                  # LangChain + DeepSeek
│   ├── assistant.py            # 对话 Agent 编排、SSE 事件
│   ├── summarizer.py           # 总结生成（非对话流程）
│   └── tools/
│       ├── __init__.py         # 工具注册与汇总
│       ├── task_tools.py
│       ├── note_tools.py
│       └── language_tools.py
├── web/                        # Vue 3 + TS + Element Plus
│   ├── src/
│   └── dist/                   # 构建产物，FastAPI 静态托管
└── skills/                     # 预留，暂不使用
```

本地运行约定：

- 后端默认 `http://127.0.0.1:8002`。
- 开发期前端 `npm run dev`，通过 Vite 代理访问后端。
- 正式本地使用执行 `npm run build`，由 FastAPI 托管 `web/dist`。

## 4. 数据模型与存储

SQLite（`data/app.db`）+ SQLAlchemy 2.0 ORM；`.md` 文件是笔记与总结的内容源头，
数据库仅保存结构化数据和文件元数据。

### 表设计

| 表 | 说明 | 关键字段 |
| --- | --- | --- |
| `languages` | 一级分类 | id、name（唯一）、sort_order、created_at |
| `tasks` | 学习任务 | id、language_id、title、description、status、summary_status、completed_at、created_at、updated_at |
| `note_files` | 笔记/总结文件元数据 | id、task_id、kind（note/summary）、rel_path（唯一）、updated_at |
| `learning_records` | 学习记录 | id、task_id、record_type（auto/manual）、content、started_at、created_at |
| `chat_sessions` | 聊天会话 | id、title、created_at、updated_at |
| `chat_messages` | 聊天消息 | id、session_id、role、content、tool_name、tool_input_json、created_at |

约束：

- `tasks`：`(language_id, title)` 唯一；`status` 枚举为 `todo / in_progress / completed`；
  `summary_status` 枚举为 `pending / success / failed`。
- `note_files`：每个任务每种 `kind` 至多一个文件；`rel_path` 全局唯一。
- `learning_records`：`task_id` 必填；`record_type` 枚举为 `auto / manual`。
- 文件是笔记/总结的内容源头，ORM 表只存元数据；聊天消息完整保存在 SQLite。

### 文件规则

- 笔记：`data/notes/<语言>/<主题>.md`
- 总结：`data/notes/<语言>/<主题>-总结.md`
- 同一任务的笔记与总结位于同一目录；同一语言下主题唯一。
- 语言与主题作为路径组成部分，禁止包含路径分隔符与 Windows 保留字符，保存前校验。
- 文件统一 UTF-8 编码；任务若修改语言/主题且已存在文件，服务层负责原子迁移
  对应 `.md` 文件并更新元数据，目标路径冲突时拒绝修改。
- 总结文件由 Agent 生成，默认只读；生成失败时任务保留 `summary_status=failed`
  与错误信息，允许重试。

## 5. Agent 设计

### 模型接入

- LangChain DeepSeek 集成，模型 `deepseek-chat`。
- API Key 仅从 `.env` 读取，不写入代码、数据库或前端。

### 工具目录

```text
agents/tools/
├── __init__.py          # 汇总 tools 供 assistant 注册
├── task_tools.py
├── note_tools.py
└── language_tools.py
```

### 工具清单

| 工具 | 作用 | 写入边界 |
| --- | --- | --- |
| `create_task` | 新增任务（语言不存在时创建分类） | 任务/语言表 |
| `update_task` | 更新任务字段/状态 | 任务表，必要时迁移文件 |
| `complete_task` | 标记完成 | 任务表 + 触发总结流程 |
| `list_tasks` | 按语言/状态/关键词查询 | 只读 |
| `get_task_detail` | 查询任务详情与文件 | 只读 |
| `read_note` | 读取任务笔记正文 | 只读 |
| `draft_note` | 按用户要求起草笔记内容 | 只在聊天中返回 |
| `summarize_task` | 用户要求时生成/更新总结 | 写总结文件 |
| `list_languages` | 查询语言分类 | 只读 |

### 行为边界

- Agent 可增改任务、查询汇报、标记完成、读取笔记、起草内容、生成总结。
- Agent **不直接修改用户笔记文件**；起草内容仅返回聊天，由用户保存。
- Agent **不创建、不代写学习记录**。
- 自动学习记录只由用户在看板点击“开始学习”时由系统生成。
- 任务完成无论来自聊天还是看板，均进入同一 `completion_service`。

### 总结生成流程

1. 任务置为 `completed`，写入 `completed_at`，`summary_status=pending`，提交事务。
2. 后台任务读取该任务笔记文件内容。
3. `summarizer` 使用 DeepSeek 生成 Markdown 总结。
4. 写入 `data/notes/<语言>/<主题>-总结.md`，登记/更新 `note_files`。
5. 成功置 `summary_status=success`；失败置 `failed` 并记录原因，支持重试。

若任务重新打开后再次完成，总结文件执行**更新**而非重复创建。

## 6. API 设计

统一响应 `{code, message, detail}`；错误映射见第 8 节。

| 分组 | 端点 |
| --- | --- |
| 语言 | `GET/POST /api/languages` |
| 任务 | `GET /api/tasks`、`POST /api/tasks`、`GET/PATCH /api/tasks/{id}` |
| 状态流转 | `POST /api/tasks/{id}/start`、`POST /api/tasks/{id}/complete` |
| 笔记 | `GET/PUT /api/tasks/{id}/note` |
| 总结 | `GET /api/tasks/{id}/summary`、`POST /api/tasks/{id}/summary/regenerate` |
| 记录 | `GET /api/tasks/{id}/records`、`POST /api/tasks/{id}/records` |
| 聊天 | `POST /api/chat/sessions`、`GET /api/chat/sessions`、`GET /api/chat/sessions/{id}/messages`、`POST /api/chat/sessions/{id}/messages`（SSE） |

要点：

- `start`：任务置为学习中并写入一条 `auto` 记录，`started_at=now`。
- `complete`：状态置为已完成，触发总结生成后台任务。
- 笔记 `PUT` 由编辑器保存时调用；首次保存创建文件。
- 聊天 POST 返回 SSE 流，事件类型：`token`、`tool_start`、`tool_end`、`done`、`error`。

## 7. 页面与交互

整体布局参照大模型提供商的模型选择页：**左侧筛选、中间卡片区、最右侧固定聊天窗**。

### 任务看板（主页）

- 左侧筛选：语言、状态、关键词。
- 中间：任务卡片网格，每张卡片含标题、语言徽标、状态、简介、最近学习概览；
  操作：详情、开始学习/继续、完成、笔记。
- 右侧：聊天窗常驻；仅在编辑 Markdown 时隐藏。

### 任务详情

展示任务完整信息、学习记录时间线（自动/手动）、总结入口；支持手动新增学习记录。

### 笔记编辑

从任务卡片或详情进入；此时隐藏聊天窗，分三栏：

- 左栏：约 1/5，固定宽度，展示任务详情与关联总结入口。
- 中栏：Markdown 编辑区（默认约 2/5）。
- 右栏：实时预览区（默认约 2/5）。
- 中/右栏间分隔条可拖动，手动调整占比；左栏宽度固定。

总结文件在此查看，默认只读；若任务总结失败，此处提供重试。

## 8. 错误处理

- 统一错误码：任务不存在、语言/主题冲突、文件写入失败、路径非法、模型调用失败、总结生成失败。
- 总结生成在后台执行，不阻塞看板操作。
- Agent 工具异常不中断聊天流，向用户返回可读说明。
- 笔记文件通过任务 ID 访问，由服务层映射路径并校验，避免目录穿越。

## 9. 测试与质量

- 后端 pytest：
  - 服务层：任务 CRUD、文件读写与迁移、记录生成、总结流程（mock 模型）。
  - API：TestClient + 临时 SQLite/data 目录。
- 前端：`vue-tsc`、`npm run build`，必要时补组件测试。
- 测试数据使用 `data/` 临时副本，不触碰真实笔记。

## 10. 后续扩展

- `skills/` 目录预留；未来可按需引入可插拔技能/工具包。
- 若需要多语言知识库检索，可在总结/笔记基础上接入向量化能力。
- 若引入时长管理，可在 `learning_records` 上平滑扩展。
