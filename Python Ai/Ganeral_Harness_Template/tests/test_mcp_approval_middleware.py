"""mcp_server 人工审批中间件测试。

覆盖：非守护工具直通、守护工具批准/拒绝、超时、elicit 各分支自动回退，
以及审批台接口的票据状态流转与幂等。
"""
import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from fastmcp.exceptions import ToolError
from fastmcp.server.elicitation import AcceptedElicitation, DeclinedElicitation
from fastmcp.server.middleware import MiddlewareContext
from fastmcp.tools.base import ToolResult

import mcp_types as mt

from mcp_server.middleware import HumanApprovalMiddleware
from mcp_server.middleware.approval_dashboard import create_app
from mcp_server.middleware.approval_store import (
    APPROVED,
    DENIED,
    TIMEOUT,
    ApprovalStore,
)

DASHBOARD_URL = "http://127.0.0.1:9001"


# ---------- 测试替身 ----------

class _FakeMessage:
    """模拟 mt.CallToolRequestParams：仅需 name / arguments。"""

    def __init__(self, name, arguments=None):
        self.name = name
        self.arguments = arguments


def _make_context(name, arguments=None, fastmcp_context=None):
    return MiddlewareContext(
        message=_FakeMessage(name, arguments), fastmcp_context=fastmcp_context
    )


def _make_call_next(text="ok"):
    """构造假 call_next，记录被调用次数并返回正常结果。"""
    calls = []

    async def call_next(context):
        calls.append(context)
        return ToolResult(content=[mt.TextContent(type="text", text=text)])

    return call_next, calls


class _FakeCapabilities:
    def __init__(self, elicitation):
        self.elicitation = elicitation


class _FakeSession:
    def __init__(self, elicitation=True, can_send=True):
        self.client_capabilities = _FakeCapabilities(object() if elicitation else None)
        self.can_send_request = can_send


class _FakeFastMCPContext:
    """模拟 fastmcp Context：提供 session 与 elicit 的最小行为。"""

    def __init__(self, elicit_result=None, elicit_error=None, session=None):
        self._session = session if session is not None else _FakeSession()
        self._result = elicit_result
        self._error = elicit_error
        self.elicit_calls = 0

    @property
    def session(self):
        return self._session

    async def elicit(self, message, response_type):
        self.elicit_calls += 1
        if self._error is not None:
            raise self._error
        return self._result


class _RaisingSession:
    """session 访问即抛错，用于验证能力探测的兜底。"""

    @property
    def session(self):
        raise RuntimeError("session 尚未建立")


class _SessionRaisingFastMCPContext:
    session = _RaisingSession()


async def _wait_for_ticket(store, timeout=2.0):
    """轮询等待中间件登记出票据。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        pending = store.list_pending()
        if pending:
            return pending[0]
        await asyncio.sleep(0.01)
    raise AssertionError("未等到审批票据")


async def _run_and_decide(middleware, context, store, approved):
    """启动中间件调用，等票据出现后作出决定，返回 (结果, 调用记录, 票据)。"""
    call_next, calls = _make_call_next()
    task = asyncio.create_task(middleware.on_call_tool(context, call_next))
    ticket = await _wait_for_ticket(store)
    store.decide(ticket.id, approved)
    result = await asyncio.wait_for(task, timeout=5)
    return result, calls, ticket


# ---------- 中间件行为 ----------

class TestHumanApprovalMiddleware:
    @pytest.mark.asyncio
    async def test_non_guarded_tool_passes_through(self):
        """非守护工具直通：call_next 被调用一次，原结果原样返回，不产生票据。"""
        store = ApprovalStore()
        middleware = HumanApprovalMiddleware(
            tools=["rag_delete_file"], timeout=5, store=store, dashboard_url=DASHBOARD_URL
        )
        call_next, calls = _make_call_next(text="列表结果")
        context = _make_context("rag_list_files", {})

        result = await middleware.on_call_tool(context, call_next)

        assert result.is_error is False
        assert result.content[0].text == "列表结果"
        assert len(calls) == 1
        assert store.list_pending() == []

    @pytest.mark.asyncio
    async def test_guarded_tool_approved(self):
        """守护工具 + 批准 → 放行，call_next 被调用。"""
        store = ApprovalStore()
        middleware = HumanApprovalMiddleware(
            tools=["rag_delete_file"], timeout=5, store=store, dashboard_url=DASHBOARD_URL
        )
        context = _make_context("rag_delete_file", {"file_path": "a.pdf"})

        result, calls, ticket = await _run_and_decide(middleware, context, store, approved=True)

        assert result.is_error is False
        assert len(calls) == 1
        assert store.get(ticket.id).status == APPROVED

    @pytest.mark.asyncio
    async def test_guarded_tool_denied(self):
        """守护工具 + 拒绝 → 返回 is_error 结果，不进入工具体。"""
        store = ApprovalStore()
        middleware = HumanApprovalMiddleware(
            tools=["rag_delete_file"], timeout=5, store=store, dashboard_url=DASHBOARD_URL
        )
        context = _make_context("rag_delete_file", {"file_path": "a.pdf"})

        result, calls, ticket = await _run_and_decide(middleware, context, store, approved=False)

        assert result.is_error is True
        assert len(calls) == 0
        assert "拒绝" in result.content[0].text
        assert f"#{ticket.id}" in result.content[0].text
        assert store.get(ticket.id).status == DENIED

    @pytest.mark.asyncio
    async def test_guarded_tool_timeout_denied(self):
        """超时 → 按拒绝处理，返回 is_error 结果。"""
        store = ApprovalStore()
        middleware = HumanApprovalMiddleware(
            tools=["rag_delete_file"], timeout=0.2, store=store, dashboard_url=DASHBOARD_URL
        )
        call_next, calls = _make_call_next()
        context = _make_context("rag_delete_file", {"file_path": "a.pdf"})

        result = await middleware.on_call_tool(context, call_next)

        assert result.is_error is True
        assert len(calls) == 0
        assert "未获批准" in result.content[0].text
        ticket = store.get(1)
        assert ticket.status == TIMEOUT

    @pytest.mark.asyncio
    async def test_elicit_accepted_approves_without_ticket(self):
        """elicit 返回接受 → 直接批准，不登记网页票据。"""
        store = ApprovalStore()
        middleware = HumanApprovalMiddleware(
            tools=["rag_delete_file"], timeout=5, store=store, dashboard_url=DASHBOARD_URL
        )
        fake_ctx = _FakeFastMCPContext(elicit_result=AcceptedElicitation(data=True))
        call_next, calls = _make_call_next()
        context = _make_context("rag_delete_file", {"file_path": "a.pdf"}, fake_ctx)

        result = await middleware.on_call_tool(context, call_next)

        assert result.is_error is False
        assert len(calls) == 1
        assert fake_ctx.elicit_calls == 1
        assert store.list_pending() == []

    @pytest.mark.asyncio
    async def test_elicit_declined_falls_back_to_dashboard(self):
        """elicit 被拒绝 → 回退网页台，等待人工决定。"""
        store = ApprovalStore()
        middleware = HumanApprovalMiddleware(
            tools=["rag_delete_file"], timeout=5, store=store, dashboard_url=DASHBOARD_URL
        )
        fake_ctx = _FakeFastMCPContext(elicit_result=DeclinedElicitation())
        context = _make_context("rag_delete_file", {"file_path": "a.pdf"}, fake_ctx)

        result, calls, _ = await _run_and_decide(middleware, context, store, approved=True)

        assert fake_ctx.elicit_calls == 1
        assert result.is_error is False
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_elicit_error_falls_back_to_dashboard(self):
        """elicit 抛 ToolError（modern 协议）→ 异常被吞掉并回退网页台。"""
        store = ApprovalStore()
        middleware = HumanApprovalMiddleware(
            tools=["rag_delete_file"], timeout=5, store=store, dashboard_url=DASHBOARD_URL
        )
        fake_ctx = _FakeFastMCPContext(
            elicit_error=ToolError("elicitation via server-initiated requests is unavailable")
        )
        context = _make_context("rag_delete_file", {"file_path": "a.pdf"}, fake_ctx)

        result, calls, _ = await _run_and_decide(middleware, context, store, approved=True)

        assert fake_ctx.elicit_calls == 1
        assert result.is_error is False
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_capability_probe_swallows_session_error(self):
        """session 访问抛错时能力探测兜底为不支持，静默回退网页台。"""
        store = ApprovalStore()
        middleware = HumanApprovalMiddleware(
            tools=["rag_delete_file"], timeout=5, store=store, dashboard_url=DASHBOARD_URL
        )
        context = _make_context(
            "rag_delete_file", {"file_path": "a.pdf"}, _SessionRaisingFastMCPContext()
        )

        result, calls, _ = await _run_and_decide(middleware, context, store, approved=True)

        assert result.is_error is False
        assert len(calls) == 1


# ---------- 审批台接口 ----------

class TestApprovalDashboard:
    def _client_with_store(self):
        store = ApprovalStore()
        return TestClient(create_app(store)), store

    def test_pending_list_and_approve(self):
        client, store = self._client_with_store()
        ticket = store.create("rag_delete_file", {"file_path": "a.pdf"})

        pending = client.get("/api/pending").json()["tickets"]
        assert [t["id"] for t in pending] == [ticket.id]

        resp = client.post(f"/api/approve/{ticket.id}")
        assert resp.status_code == 200
        assert resp.json()["ticket"]["status"] == APPROVED
        assert client.get("/api/pending").json()["tickets"] == []

    def test_deny_and_idempotent_repeat(self):
        client, store = self._client_with_store()
        ticket = store.create("rag_add_knowledge", {"filename": "a.md"})

        assert client.post(f"/api/deny/{ticket.id}").json()["ticket"]["status"] == DENIED
        # 重复决定幂等：不会覆盖已有结论
        again = client.post(f"/api/approve/{ticket.id}").json()["ticket"]
        assert again["status"] == DENIED

    def test_unknown_ticket_returns_404(self):
        client, _ = self._client_with_store()
        assert client.post("/api/approve/999").status_code == 404
        assert client.post("/api/deny/999").status_code == 404
