"""MCP 工具接入：把 src/mcp_server 暴露的 Java 业务工具挂到主 Agent。

为什么不用 langchain-mcp-adapters：它要求 mcp>=1.24,<2.0，而本项目锁定的
fastmcp 4.1.0 依赖 mcp>=2.0，二者无法共存（实测 import 即
ImportError: cannot import name 'RequestContext' from 'mcp.shared.context'）。
因此改用 fastmcp 自带的 Client 直连，再把远端工具包装成 langchain StructuredTool。

开发阶段想脱离真实 Java 服务：在项目根 .env 里打开 JAVA_API_MOCK=1 即可。
子进程会继承该环境变量，由 MCP 服务自行拉起内置 Mock Java Api。
"""
import json
import logging
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, List, Optional

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from langchain_core.tools import StructuredTool

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MCP_SERVER_SCRIPT = PROJECT_ROOT / "src" / "mcp_server" / "server.py"


def build_stdio_client() -> Client:
    """构造以 stdio 子进程方式连接 MCP 服务的客户端（尚未建立连接）。

    用 sys.executable 保证子进程与当前 Agent 进程同一解释器/同一虚拟环境，
    避免误用系统 Python 导致 fastmcp 缺失。
    """
    if not MCP_SERVER_SCRIPT.is_file():
        raise FileNotFoundError(f"MCP 服务脚本不存在: {MCP_SERVER_SCRIPT}")
    transport = StdioTransport(
        command=sys.executable,
        args=[str(MCP_SERVER_SCRIPT)],
        cwd=str(PROJECT_ROOT),
    )
    return Client(transport)


async def load_mcp_tools(client: Client) -> List[StructuredTool]:
    """列出远端 MCP 工具，逐个包装为 LangChain 工具。

    远端工具的 inputSchema 是 dict 形式的 JSON Schema，langchain 的
    StructuredTool 可直接接收，无需转成 pydantic 模型。
    """
    remote_tools = await client.list_tools()
    return [_wrap_remote_tool(client, remote) for remote in remote_tools]


async def setup_mcp_tools(stack: AsyncExitStack) -> List[StructuredTool]:
    """连接 MCP 服务并把工具挂到给定 stack 上，随 Agent 一起关闭。

    MCP 服务不可用时不阻断 Agent 启动：记录告警并返回空列表，
    Agent 的沙箱 / 技能等其余能力不受影响。
    """
    try:
        client = await stack.enter_async_context(build_stdio_client())
        tools = await load_mcp_tools(client)
    except Exception as exc:  # noqa: BLE001
        logger.warning("MCP 工具加载失败，已跳过（Agent 其余能力不受影响）：%s", exc)
        return []
    logger.info("MCP 工具已加载 %d 个：%s", len(tools), [tool.name for tool in tools])
    return tools


def _wrap_remote_tool(client: Client, remote) -> StructuredTool:
    """把单个远端 MCP 工具包装成 LangChain 工具。"""
    tool_name = remote.name
    schema = _input_schema(remote)

    async def _call(**kwargs: Any) -> str:
        # raise_on_error=False：远端工具报错时返回 is_error 结果而非抛异常，
        # 由 _render_result 渲染成可读文本交回 LLM，避免中断 Agent 运行。
        try:
            result = await client.call_tool(tool_name, kwargs, raise_on_error=False)
        except Exception as exc:  # noqa: BLE001
            # 会话层异常（如 MCP 子进程退出、超时）同样降级为文本，不阻断运行
            logger.warning("MCP 工具 %s 调用异常：%s", tool_name, exc)
            return f"调用 MCP 工具 {tool_name} 失败：{exc}"
        return _render_result(tool_name, result)

    return StructuredTool.from_function(
        coroutine=_call,
        name=tool_name,
        description=remote.description or f"调用 MCP 工具 {tool_name}。",
        args_schema=schema,
    )


def _input_schema(remote) -> dict:
    """取远端工具的入参 JSON Schema。

    mcp SDK v2 把字段从 inputSchema 改名为 input_schema，优先读新名，
    兼容旧名以免告警或漏读。
    """
    schema: Optional[dict] = getattr(remote, "input_schema", None)
    if schema is None:
        schema = getattr(remote, "inputSchema", None)
    return schema or {"type": "object", "properties": {}}


def _render_result(tool_name: str, result) -> str:
    """把 MCP 调用结果渲染成给 LLM 看的字符串。

    优先返回结构化数据（远端工具的返回值），无结构化数据时回退文本内容；
    失败时返回可读的错误说明，交由主 Agent 决定后续动作。
    """
    texts = [
        content.text
        for content in (getattr(result, "content", None) or [])
        if getattr(content, "text", None) is not None
    ]
    data = getattr(result, "data", None)

    if getattr(result, "is_error", False):
        detail = "\n".join(texts) or (
            json.dumps(data, ensure_ascii=False) if data is not None else "未知错误"
        )
        return f"调用 MCP 工具 {tool_name} 失败：{detail}"

    if data is not None:
        return json.dumps(data, ensure_ascii=False)
    return "\n".join(texts)
