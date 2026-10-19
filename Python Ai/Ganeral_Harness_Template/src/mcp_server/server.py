"""对接已有 Java 服务端 Api 的 MCP 示例服务。

启动方式：

    python src/mcp_server/server.py            # stdio（默认），供 Agent 以子进程方式接入
    python src/mcp_server/server.py --http     # streamable-http，监听 127.0.0.1:8002/mcp
    python src/mcp_server/server.py --mock     # 内置 Mock Java Api，不依赖真实 Java 服务

配置见 mcp_server/config.py（JAVA_API_BASE_URL / JAVA_API_TOKEN / JAVA_API_TIMEOUT / JAVA_API_MOCK）。

工具清单（6 个，覆盖知识库读写与业务问答）：

| 工具名              | 作用                             | 对应 Java 接口          |
| ------------------- | -------------------------------- | ----------------------- |
| java_api_health     | 探活，确认地址与鉴权配置是否正确 | GET  /rag/list          |
| rag_list_files      | 列出知识库已入库文件             | GET  /rag/list          |
| rag_upload_file     | 上传文件并预览切分结果（不入库） | PUT  /rag/upload        |
| rag_add_knowledge   | 把确认后的切分内容写入知识库     | POST /rag/add           |
| rag_delete_file     | 删除知识库文件                   | DELETE /rag/delete      |
| chat                | 业务问答（知识库问答/智能客服）  | POST /{feature_code}/chat |
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# 把 src/ 放到 sys.path 顶部，使 mcp_server 包可被绝对导入（与 main.py 一致）
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fastmcp import FastMCP

from mcp_server.client import JavaApiClient, JavaApiError
from mcp_server.config import (
    JAVA_API_BASE_URL,
    JAVA_API_MOCK,
    JAVA_API_MOCK_HOST,
    JAVA_API_MOCK_PORT,
    MCP_APPROVAL_DASHBOARD_HOST,
    MCP_APPROVAL_DASHBOARD_PORT,
    MCP_APPROVAL_ENABLED,
    MCP_APPROVAL_TIMEOUT,
    MCP_APPROVAL_TOOLS,
    UPLOAD_ROOT,
)
from mcp_server.middleware import HumanApprovalMiddleware
from mcp_server.middleware.approval_dashboard import start_dashboard

logger = logging.getLogger(__name__)

# streamable-http 传输的默认监听地址
HTTP_HOST = "127.0.0.1"
HTTP_PORT = 8002

mcp = FastMCP(
    "java-business-api",
    instructions=(
        "对接 Java 业务服务端 Api 的工具集，提供知识库（RAG）文件管理与业务问答能力。"
        "所有工具均直接访问远端 Java 服务，调用前可先用 java_api_health 确认连通性。"
    ),
)

# 人工审批中间件：模块级注册，保证 stdio 与 http 两种传输下写操作都被拦截。
# 审批台自身在 main() 里按开关启动，import server.py 不会起 HTTP 服务。
if MCP_APPROVAL_ENABLED:
    mcp.add_middleware(
        HumanApprovalMiddleware(
            tools=MCP_APPROVAL_TOOLS,
            timeout=MCP_APPROVAL_TIMEOUT,
            dashboard_url=f"http://{MCP_APPROVAL_DASHBOARD_HOST}:{MCP_APPROVAL_DASHBOARD_PORT}",
        )
    )

_client = JavaApiClient()


def _resolve_local_file(file_path: str) -> Path:
    """解析待上传的本地文件：绝对路径直接使用，相对路径按 uploads/ 目录解析。"""
    candidate = Path(file_path)
    if not candidate.is_absolute():
        candidate = UPLOAD_ROOT / candidate
    if not candidate.is_file():
        raise FileNotFoundError(f"文件不存在: {candidate}")
    return candidate


def _start_mock_api(host: str, port: int) -> str:
    """在后台线程启动 Mock Java Api，返回其基址。

    阻塞至端口就绪再返回，避免启动竞态导致首批工具调用失败。
    线程设为 daemon，随 MCP 服务进程一起退出。
    """
    import socket
    import threading
    import time

    import uvicorn

    from mcp_server.mock_java_api import app as mock_app

    uvicorn_config = uvicorn.Config(mock_app, host=host, port=port, log_level="warning")
    threading.Thread(target=uvicorn.Server(uvicorn_config).run,
                     name="mock-java-api", daemon=True).start()

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        with socket.socket() as probe:
            probe.settimeout(0.2)
            if probe.connect_ex((host, port)) == 0:
                return f"http://{host}:{port}/api"
        time.sleep(0.05)
    raise RuntimeError(f"Mock Java Api 启动失败：{host}:{port} 未就绪")


@mcp.tool()
async def java_api_health() -> Dict[str, Any]:
    """探测 Java 服务端是否可用，用于确认地址、网络与鉴权配置是否正确。

    Java Api 未提供独立健康检查接口，这里用 GET /rag/list 做轻量探活。
    """
    try:
        files = await _client.list_rag_files()
    except JavaApiError as exc:
        return {"ok": False, "base_url": _client.base_url, "error": str(exc)}
    return {
        "ok": True,
        "base_url": _client.base_url,
        "file_count": len(files) if isinstance(files, list) else None,
    }


@mcp.tool()
async def rag_list_files() -> Dict[str, Any]:
    """列出 Java 知识库中已入库的文件。

    返回 count 与 files（Java 端仅返回文件名，故元素为字符串）。
    """
    files = await _client.list_rag_files()
    if not isinstance(files, list):
        raise JavaApiError(f"/rag/list 返回结构异常，期望数组: {files!r}")
    names = [item.get("name") if isinstance(item, dict) else str(item) for item in files]
    return {"count": len(names), "files": names}


@mcp.tool()
async def rag_upload_file(file_path: str) -> Dict[str, Any]:
    """上传本地文件到 Java 知识库服务，返回切分结果供人工确认。

    只做上传与切分预览，不会入库；确认切分内容后需再调用 rag_add_knowledge。

    Args:
        file_path: 本地文件路径。绝对路径直接使用，相对路径按项目 uploads/ 目录解析。
    """
    path = _resolve_local_file(file_path)
    content = await asyncio.to_thread(path.read_bytes)
    result = await _client.upload_rag_file(path.name, content)

    if not isinstance(result, dict):
        raise JavaApiError(f"/rag/upload 返回结构异常，期望对象: {result!r}")
    raw_splits = result.get("splits") or []
    splits = [
        (item.get("content") or item.get("text") or "")
        if isinstance(item, dict)
        else str(item)
        for item in raw_splits
    ]
    return {"filename": path.name, "split_count": len(splits), "splits": splits}


@mcp.tool()
async def rag_add_knowledge(filename: str, splits: List[str]) -> Dict[str, Any]:
    """把切分后的文本内容正式写入 Java 知识库。

    Args:
        filename: 来源文件名，需与上传时一致。
        splits: 切分文本列表，通常直接使用 rag_upload_file 的返回值。
    """
    if not splits:
        raise ValueError("splits 不能为空，请先调用 rag_upload_file 获取切分结果")
    result = await _client.add_rag_knowledge(filename, splits)
    return {"ok": True, "filename": filename, "split_count": len(splits), "result": result}


@mcp.tool()
async def rag_delete_file(file_path: str) -> Dict[str, Any]:
    """从 Java 知识库中删除指定文件。

    Args:
        file_path: 要删除的文件名或路径，与 rag_list_files 返回的名称一致。
    """
    if not file_path.strip():
        raise ValueError("file_path 不能为空")
    await _client.delete_rag_file(file_path)
    return {"ok": True, "file_path": file_path}


@mcp.tool()
async def chat(feature_code: str, message: str) -> Dict[str, Any]:
    """向 Java 服务端的业务问答接口提问。

    Args:
        feature_code: 业务功能编码，已知取值 rag（知识库问答）、service（智能客服）。
        message: 用户问题。
    """
    if not message.strip():
        raise ValueError("message 不能为空")
    result = await _client.chat(feature_code, message)

    reply = ""
    if isinstance(result, dict):
        reply = result.get("message") or result.get("msg") or result.get("answer") or ""
    elif isinstance(result, str):
        reply = result
    elif result is not None:
        reply = str(result)

    payload: Dict[str, Any] = {"feature_code": feature_code, "reply": reply}
    if not reply:
        # 未识别出回复字段时回原始数据，便于核对 Java 端响应结构
        payload["raw"] = result
    return payload


def main() -> None:
    """命令行入口：默认 stdio 传输，--http 时使用 streamable-http，--mock 时内置 Mock Java Api。"""
    parser = argparse.ArgumentParser(description="对接 Java 服务端 Api 的 MCP 示例服务")
    parser.add_argument(
        "--http", action="store_true", help=f"以 streamable-http 启动，监听 {HTTP_HOST}:{HTTP_PORT}"
    )
    parser.add_argument("--host", default=HTTP_HOST, help="streamable-http 监听地址")
    parser.add_argument("--port", type=int, default=HTTP_PORT, help="streamable-http 监听端口")
    parser.add_argument(
        "--mock", action="store_true", help="内置 Mock Java Api，开发阶段不访问真实 Java 服务"
    )
    parser.add_argument("--mock-port", type=int, default=JAVA_API_MOCK_PORT, help="内置 Mock 监听端口")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    if args.mock or JAVA_API_MOCK:
        # 内置 Mock 时改写模块级客户端，工具后续调用均指向 Mock
        global _client
        _client = JavaApiClient(base_url=_start_mock_api(JAVA_API_MOCK_HOST, args.mock_port))
        logger.info("Mock Java Api 已启动，当前基址: %s", _client.base_url)
    else:
        logger.info("Java Api 基址: %s", JAVA_API_BASE_URL)

    if MCP_APPROVAL_ENABLED:
        # stdio 模式下 Agent 拉起的子进程也会执行 main()，审批台随之启动
        start_dashboard(MCP_APPROVAL_DASHBOARD_HOST, MCP_APPROVAL_DASHBOARD_PORT)

    if args.http:
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
