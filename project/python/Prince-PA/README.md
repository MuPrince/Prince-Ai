# Prince-PA

Prince-PA 是一个本地运行的个人 Agent 开发学习助理，支持按编程语言分类管理学习
任务、Markdown 笔记编辑、任务完成自动总结、学习记录，以及右侧常驻的 LangChain +
DeepSeek 聊天 Agent。

## 文档

- [PRD](PRD.md)
- [设计文档](docs/superpowers/specs/2026-09-06-prince-pa-learning-assistant-design.md)
- [实现计划](docs/superpowers/plans/2026-09-06-prince-pa-learning-assistant.md)

## 目录

```text
app/       FastAPI 后端
agents/    LangChain Agent、工具、记忆/画像
web/       Vue 3 + TypeScript 前端
data/      运行时笔记 .md 与 SQLite（不提交）
```

## 本地启动

1. 配置 `.env`（参考 `.env.example`）：

   ```text
   DEEPSEEK_API_KEY=你的Key
   ```

2. 安装并启动后端：

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002
   ```

3. 安装并构建前端（也可开发期用 Vite 代理）：

   ```powershell
   cd web
   npm install
   npm run build
   ```

4. 打开 `http://127.0.0.1:8002/`。

## 数据

- 笔记：`data/notes/<语言>/<主题>.md`
- 总结：`data/notes/<语言>/<主题>-总结.md`
- SQLite：`data/app.db`

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest
cd web; npm run test; npm run build
```
