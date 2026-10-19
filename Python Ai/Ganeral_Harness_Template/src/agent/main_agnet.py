"""
主 Agent 构建与生命周期管理。

不在 import 时创建：由 FastAPI lifespan 调用 build_agent()，
shutdown 时调用 close_agent()，确保 Postgres 连接 / checkpointer 正确关闭。
"""
import logging
import os
from contextlib import AsyncExitStack
from typing import Optional

from deepagents import create_deep_agent
from deepagents.backends import (
    CompositeBackend,
    FilesystemBackend,
    StateBackend,
    StoreBackend,
)
from dotenv import load_dotenv
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore

# 必须在导入子 Agent / 工具等依赖环境变量的模块之前加载 .env：
# 子 Agent spec 在 import 时调用 get_subagent_model()，需要 DEEPSEEK_API_KEY 已就绪
load_dotenv()

from agent.config.config import MODEL
from agent.config.constants import LOCAL_SKILLS_DIR
from agent.config.context_type import ContextType
from agent.backends.sandbox import get_sandbox_pool, close_sandbox_pool
from agent.backends.sandbox_pool_backend import SandboxPoolBackend
from agent.subagent import SUBAGENTS
from agent.tools.sandbox_tools import SANDBOX_TOOLS
from agent.tools.skill_tools import SKILL_TOOLS
from agent.tools.mcp_tools import setup_mcp_tools

logger = logging.getLogger(__name__)

PG_CONN_STRING = os.getenv(
    "PG_CONN_STRING",
    "postgresql://postgre:root@127.0.0.1:5432/harness_template",
)

# 模块级单例：build_agent() 之后被填充，close_agent() 时清空
_stack: Optional[AsyncExitStack] = None
_agent = None
_checkpointer: Optional[AsyncPostgresSaver] = None
_store: Optional[AsyncPostgresStore] = None


def _org_namespace(rt) -> tuple:
    """org 级命名空间：同组织共享（用于 AGENTS.md 等团队指引）。

    rt 是 LangGraph 的 Runtime，从其 context（即 ContextType）读取 org_id。
    若在 graph 外被调用（无 runtime/context），回退到默认值避免崩溃。
    """
    ctx = getattr(rt, "context", None)
    org = getattr(ctx, "org_id", None) or "default_org"
    return (org,)


def _user_namespace(rt) -> tuple:
    """user 级命名空间：同用户隔离（用于 /memories/ 等个人记忆）。"""
    ctx = getattr(rt, "context", None)
    org = getattr(ctx, "org_id", None) or "default_org"
    user = getattr(ctx, "user_id", None) or "local_user"
    return org, user


async def build_agent():
    """构建主 Agent（deep agent）。

    - checkpointer：AsyncPostgresSaver，负责 thread 级对话历史
    - store：AsyncPostgresStore，负责跨 thread 的 memory / 知识
    - subagents：SUBAGENTS（file_agent / statistic_agent / coder_agent / reviewer_agent
      四个专职子 Agent，经内置 task 工具按 description 委派；
      deepagents 会额外自动追加一个内置 general-purpose 子 Agent）
    - backend：CompositeBackend
        * 默认            → StateBackend（thread 内临时文件）
        * /memory/AGENTS.md → StoreBackend（全局 AGENTS 记忆）
        * /memories/       → StoreBackend（全局 memories）
        * /skills/         → FilesystemBackend（LOCAL_SKILLS_DIR）
        * /sandbox/        → SandboxPool（按 org_id 隔离，支持并发与等待队列）
    - mcp：以 stdio 子进程接入 src/mcp_server，把 Java 业务 Api 工具并入工具集；
      服务不可用时自动降级（不阻断启动），会话挂在 stack 上随 Agent 一起关闭
    """
    global _stack, _agent, _checkpointer, _store
    if _agent is not None:
        return _agent

    stack = AsyncExitStack()
    checkpointer = await stack.enter_async_context(
        AsyncPostgresSaver.from_conn_string(PG_CONN_STRING)
    )
    store = await stack.enter_async_context(
        AsyncPostgresStore.from_conn_string(PG_CONN_STRING)
    )
    await checkpointer.setup()
    await store.setup()

    # 启动沙箱池（按 org_id 隔离，支持并发 64 任务与等待队列）
    get_sandbox_pool()

    # 接入 MCP 服务（src/mcp_server → Java 业务 Api）；失败时降级为空列表
    mcp_tools = await setup_mcp_tools(stack)

    agent = create_deep_agent(
        model=MODEL,
        context_schema=ContextType,
        memory=["/memories/"],
        skills=["/skills/main/"],
        tools=[*SANDBOX_TOOLS, *SKILL_TOOLS, *mcp_tools],
        subagents=SUBAGENTS,
        checkpointer=checkpointer,
        store=store,
        backend=CompositeBackend(
            default=StateBackend(),
            routes={
                "/memory/AGENTS.md": StoreBackend(
                    namespace=_org_namespace,
                    store=store,
                ),
                "/memories/": StoreBackend(
                    namespace=_user_namespace,
                    store=store,
                ),
                "/skills/": FilesystemBackend(
                    root_dir=str(LOCAL_SKILLS_DIR),
                    virtual_mode=True,
                ),
                "/sandbox/": SandboxPoolBackend(),
            },
        ),
    )

    _stack = stack
    _checkpointer = checkpointer
    _store = store
    _agent = agent
    logger.info("主 agent 构建完成。")
    return agent


def get_agent():
    """取出已构建的 agent 单例；未构建时抛错（应由 lifespan 先调用 build_agent）。"""
    if _agent is None:
        raise RuntimeError("agent 尚未构建，请先在 FastAPI lifespan 中调用 build_agent()。")
    return _agent


async def close_agent() -> None:
    """关闭 agent 依赖的资源（Postgres 连接等）。"""
    global _stack, _agent, _checkpointer, _store
    if _stack is not None:
        try:
            await _stack.aclose()
            logger.info("主 agent 资源已关闭。")
        finally:
            _stack = None
            _agent = None
            _checkpointer = None
            _store = None

    # 关闭沙箱池
    close_sandbox_pool()
