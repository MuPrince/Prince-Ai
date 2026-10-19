"""人工审批中间件：拦截不可逆写操作，等人类批准后才放行。

命中守护名单的工具调用会被挂起，先尝试协议原生的人工确认通道
``ctx.elicit(...)``（**尽力路径**：modern 协议下它会直接抛 ``ToolError``，
故必须捕获异常并回退），失败或客户端不支持时回退到网页审批台：
登记票据后用 ``asyncio.to_thread(event.wait, timeout)`` 阻塞等待人类批准。

批准 → 正常放行（``return await call_next(context)``）；
拒绝 / 超时 → 返回 ``ToolResult(is_error=True, ...)`` 短路，不再进入工具体。

实现风格参照官方 ``fastmcp/server/middleware/authorization.py`` 的
``AuthMiddleware.on_call_tool``。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Iterable, Optional, Set

import mcp_types as mt

from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools.base import ToolResult

from mcp_server.middleware.approval_store import APPROVED, DENIED, ApprovalStore, default_store

logger = logging.getLogger(__name__)


class HumanApprovalMiddleware(Middleware):
    """对指定工具做人工审批的中间件。

    Args:
        tools: 需要人工审批的工具名集合（仅拦截这些工具）。
        timeout: 等待人类决定的秒数，超时按拒绝处理。
        store: 票据存储，默认使用进程内共享的 ``default_store``。
        dashboard_url: 审批台地址，写入拒绝说明便于排查。
    """

    def __init__(
        self,
        tools: Iterable[str],
        timeout: float,
        store: Optional[ApprovalStore] = None,
        dashboard_url: str = "",
    ) -> None:
        self._tools: Set[str] = set(tools)
        self._timeout = float(timeout)
        self._store = store if store is not None else default_store
        self._dashboard_url = dashboard_url.rstrip("/")

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        """写操作工具执行前先请人审批。"""
        tool_name = context.message.name

        # 不在守护名单的工具（读操作）直接放行，不做任何额外动作
        if tool_name not in self._tools:
            return await call_next(context)

        arguments = dict(context.message.arguments or {})
        logger.info("工具 %s 命中人工审批名单，请求审批：%s", tool_name, arguments)

        rejection = await self._request_approval(tool_name, arguments, context)
        if rejection is None:
            logger.info("工具 %s 已获人工批准，放行执行", tool_name)
            return await call_next(context)

        logger.warning("工具 %s 未经批准，已拒绝执行：%s", tool_name, rejection)
        return ToolResult(
            content=[mt.TextContent(type="text", text=rejection)],
            is_error=True,
        )

    async def _request_approval(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: MiddlewareContext[mt.CallToolRequestParams],
    ) -> Optional[str]:
        """请求人工审批。

        返回 None 表示已批准；返回字符串表示拒绝（内容给 LLM 阅读）。
        """
        message = f"Agent 请求执行写操作「{tool_name}」，参数：{arguments}。是否批准？"

        # 1) 尽力尝试协议原生 elicit（modern 协议下会抛 ToolError，必须捕获）
        if await self._try_elicit(context, message):
            logger.info("工具 %s 经 elicit 获得批准", tool_name)
            return None

        # 2) 回退网页审批台：登记票据并阻塞等待
        ticket = self._store.create(tool_name, arguments)
        if self._dashboard_url:
            logger.info(
                "已登记审批票据 #%d（%s），请访问 %s 处理，等待最多 %.0f 秒",
                ticket.id, tool_name, self._dashboard_url, self._timeout,
            )
        else:
            logger.info("已登记审批票据 #%d（%s），等待最多 %.0f 秒", ticket.id, tool_name, self._timeout)

        decided = await asyncio.to_thread(self._store.wait, ticket.id, self._timeout)
        status = decided.status if decided is not None else ""

        if status == APPROVED:
            return None

        where = f"，可访问 {self._dashboard_url} 查看" if self._dashboard_url else ""
        if status == DENIED:
            return f"人工审核未通过：工具 {tool_name} 的请求被拒绝（票据 #{ticket.id}{where}）"
        return (
            f"人工审核未通过：工具 {tool_name} 的请求在 {self._timeout:.0f} 秒内未获批准，"
            f"已按拒绝处理（票据 #{ticket.id}{where}）"
        )

    async def _try_elicit(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        message: str,
    ) -> bool:
        """探测客户端能力并尝试 elicit；批准返回 True，其余一律 False。

        任何异常（含 modern 协议下的 ``ToolError``）都被吞掉，绝不冒泡导致
        工具调用失败——能力不足就静默降级到网页审批台。
        """
        fastmcp_context = context.fastmcp_context
        if fastmcp_context is None or not self._client_supports_elicitation(fastmcp_context):
            return False

        try:
            result = await fastmcp_context.elicit(message, response_type=bool)
        except Exception as exc:  # noqa: BLE001 - elicit 失败必须回退，不能中断调用
            logger.info("elicit 请求失败，回退网页审批台：%s", exc)
            return False

        # AcceptedElicitation / DeclinedElicitation / CancelledElicitation 均带 action 字段
        if getattr(result, "action", None) == "accept" and getattr(result, "data", None) is True:
            return True
        logger.info("elicit 未获批准（action=%s），回退网页审批台", getattr(result, "action", None))
        return False

    @staticmethod
    def _client_supports_elicitation(fastmcp_context: Any) -> bool:
        """探测客户端是否声明了 elicitation 能力且当前会话可发起请求。

        ``Context.session`` 在无请求上下文时可能抛错，故整体 try/except 兜底。
        """
        try:
            session = fastmcp_context.session
            capabilities = session.client_capabilities
            if capabilities is None or getattr(capabilities, "elicitation", None) is None:
                return False
            return bool(session.can_send_request)
        except Exception:  # noqa: BLE001 - 探测失败按「不支持」处理
            return False
