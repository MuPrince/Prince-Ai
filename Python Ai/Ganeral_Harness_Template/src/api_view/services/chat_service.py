"""聊天相关业务：调用主 Agent 的 astream_events，把 LangChain 事件流转成 SSE 帧。

前端约定的事件类型（与 index.html 对应）：
  token / reasoning_token / tool_call / tool_result / done / error
"""
import json
import logging
from typing import AsyncIterator, Optional

from agent.config.context_type import ContextType
from agent.main_agnet import get_agent
from agent.backends.sandbox_pool_backend import set_sandbox_context, clear_sandbox_context
from agent.tools.sandbox_tools import begin_context_tracking, cleanup_context_tasks

logger = logging.getLogger(__name__)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _run_agent_stream(
    message: str,
    thread_id: str,
    user_id: str,
    org_id: str,
    extra_messages: Optional[list] = None,
) -> AsyncIterator[str]:
    """核心流式循环：驱动 agent.astream_events，把事件翻译成 SSE。"""
    agent = get_agent()

    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 100,
    }
    context = ContextType(user_id=user_id, org_id=org_id)

    messages = list(extra_messages or [])
    messages.append({"role": "user", "content": message})
    input_state = {"messages": messages}

    full_reply = ""
    full_reasoning = ""

    # 沙箱上下文：设置 org_id 供 SandboxPoolBackend 路由；
    # 开始跟踪本次流创建的沙箱任务，finally 中兜底释放未 finish 的任务
    set_sandbox_context(org_id)
    begin_context_tracking()

    try:
        async for event in agent.astream_events(
            input_state,
            config=config,
            context=context,
            version="v2",
        ):
            kind = event.get("event")

            if kind == "on_chat_model_stream":
                chunk = (event.get("data") or {}).get("chunk")
                if chunk is None:
                    continue
                content = getattr(chunk, "content", "") or ""
                if content:
                    full_reply += content
                    yield _sse({"type": "token", "content": content})
                reasoning = (getattr(chunk, "additional_kwargs", None) or {}).get(
                    "reasoning_content"
                ) or ""
                if reasoning:
                    full_reasoning += reasoning
                    yield _sse({"type": "reasoning_token", "content": reasoning})

            elif kind == "on_tool_start":
                name = event.get("name") or "tool"
                yield _sse({"type": "tool_call", "name": name})

            elif kind == "on_tool_end":
                yield _sse({"type": "tool_result"})

        yield _sse({
            "type": "done",
            "reply": full_reply,
            "reasoning": full_reasoning or None,
        })

    except Exception as e:
        logger.exception("stream_chat error thread_id=%s", thread_id)
        yield _sse({"type": "error", "message": str(e)})

    finally:
        # 兜底：释放本次聊天流中未显式 finish 的沙箱任务，防止沙箱泄漏
        try:
            cleanup_context_tasks()
        except Exception:
            logger.exception("cleanup_context_tasks error thread_id=%s", thread_id)
        clear_sandbox_context()


async def stream_chat(
    message: str,
    thread_id: str,
    user_id: str,
    org_id: str,
) -> AsyncIterator[str]:
    """普通聊天。"""
    async for frame in _run_agent_stream(
        message=message, thread_id=thread_id, user_id=user_id, org_id=org_id
    ):
        yield frame


async def stream_chat_with_file(
    message: str,
    thread_id: str,
    user_id: str,
    org_id: str,
    file_id: str,
) -> AsyncIterator[str]:
    """带文件聊天：在 user message 前先注入一条 system 提示，告知 agent 文件信息。

    真正的文件内容注入 / 沙箱分析由 file_service 后续实现，这里仅做提示。
    """
    hint = (
        f"用户上传了文件 file_id={file_id}，"
        "请结合该文件回答接下来的问题。"
    )
    async for frame in _run_agent_stream(
        message=message,
        thread_id=thread_id,
        user_id=user_id,
        org_id=org_id,
        extra_messages=[{"role": "system", "content": hint}],
    ):
        yield frame
