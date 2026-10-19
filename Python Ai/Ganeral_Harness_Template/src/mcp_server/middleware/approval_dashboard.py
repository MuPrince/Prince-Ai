"""网页审批台：列出待审票据，供人类一键批准 / 拒绝。

极简 FastAPI 应用，仅监听回环地址。接口：

| 方法 | 路径                     | 作用               |
| ---- | ------------------------ | ------------------ |
| GET  | `/`                      | 极简 HTML 页面     |
| GET  | `/api/pending`           | 待审票据列表（JSON）|
| POST | `/api/approve/{id}`      | 批准某张票据       |
| POST | `/api/deny/{id}`         | 拒绝某张票据       |

``start_dashboard`` 复用 ``server.py`` 中 ``_start_mock_api`` 的写法：
uvicorn 在 daemon 后台线程启动，并轮询端口直到就绪才返回，避免启动竞态。
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from mcp_server.middleware.approval_store import ApprovalStore, default_store

logger = logging.getLogger(__name__)


def create_app(store: Optional[ApprovalStore] = None) -> FastAPI:
    """构造审批台 FastAPI 应用，票据读写指向给定存储。"""
    app = FastAPI(title="MCP 人工审批台", description="审批 Agent 的写操作请求")
    tickets = store if store is not None else default_store

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        """审批台主页：待审票据列表 + 批准 / 拒绝按钮。"""
        return _render_index()

    @app.get("/api/pending")
    async def pending() -> dict:
        """返回当前所有待审票据。"""
        return {"tickets": [t.to_dict() for t in tickets.list_pending()]}

    @app.post("/api/approve/{ticket_id}")
    async def approve(ticket_id: int) -> dict:
        """批准指定票据，唤醒等待中的工具调用。"""
        return _decide(tickets, ticket_id, approved=True)

    @app.post("/api/deny/{ticket_id}")
    async def deny(ticket_id: int) -> dict:
        """拒绝指定票据，工具调用将返回可读的拒绝说明。"""
        return _decide(tickets, ticket_id, approved=False)

    return app


def _decide(store: ApprovalStore, ticket_id: int, approved: bool) -> dict:
    """执行审批决定并返回结果；票据不存在则 404，重复决定幂等。"""
    ticket = store.decide(ticket_id, approved=approved, decided_by="dashboard")
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"票据 #{ticket_id} 不存在")
    return {"ok": True, "ticket": ticket.to_dict()}


def _render_index() -> str:
    """渲染审批台主页（内联样式与脚本，无外部依赖）。"""
    return """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>MCP 人工审批台</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 2rem; color: #222; }
  h1 { font-size: 1.3rem; }
  table { border-collapse: collapse; width: 100%; margin-top: 1rem; }
  th, td { border: 1px solid #ddd; padding: 0.5rem 0.75rem; text-align: left; font-size: 0.9rem; }
  th { background: #f5f5f5; }
  button { margin-right: 0.5rem; padding: 0.25rem 0.75rem; cursor: pointer; }
  .empty { color: #888; margin-top: 1rem; }
</style>
</head>
<body>
  <h1>MCP 人工审批台</h1>
  <div id="content" class="empty">加载中…</div>
<script>
async function load() {
  const res = await fetch('/api/pending');
  const data = await res.json();
  const box = document.getElementById('content');
  if (!data.tickets.length) {
    box.className = 'empty';
    box.textContent = '当前没有待审请求。';
    return;
  }
  let rows = data.tickets.map(t => (
    '<tr><td>#' + t.id + '</td><td>' + t.tool_name + '</td>' +
    '<td><code>' + JSON.stringify(t.arguments) + '</code></td>' +
    '<td>' + t.created_at_text + '</td>' +
    '<td><button onclick="decide(' + t.id + ', true)">批准</button>' +
    '<button onclick="decide(' + t.id + ', false)">拒绝</button></td></tr>'
  )).join('');
  box.className = '';
  box.innerHTML = '<table><thead><tr><th>票据</th><th>工具</th><th>参数</th>' +
    '<th>提交时间</th><th>操作</th></tr></thead><tbody>' + rows + '</tbody></table>';
}
async function decide(id, approved) {
  const url = approved ? '/api/approve/' + id : '/api/deny/' + id;
  await fetch(url, {method: 'POST'});
  load();
}
load();
setInterval(load, 3000);
</script>
</body>
</html>"""


def start_dashboard(host: str, port: int, store: Optional[ApprovalStore] = None) -> str:
    """在后台线程启动审批台，返回其访问地址。

    阻塞至端口就绪再返回，避免启动竞态。线程设为 daemon，随 MCP 服务进程一起退出。
    """
    import socket
    import threading
    import time

    import uvicorn

    uvicorn_config = uvicorn.Config(
        create_app(store), host=host, port=port, log_level="warning"
    )
    threading.Thread(
        target=uvicorn.Server(uvicorn_config).run, name="approval-dashboard", daemon=True
    ).start()

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        with socket.socket() as probe:
            probe.settimeout(0.2)
            if probe.connect_ex((host, port)) == 0:
                url = f"http://{host}:{port}"
                logger.info("人工审批台已启动：%s", url)
                return url
        time.sleep(0.05)
    raise RuntimeError(f"人工审批台启动失败：{host}:{port} 未就绪")
