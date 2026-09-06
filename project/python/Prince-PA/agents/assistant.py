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
    tools = build_all_tools(session_factory)
    agent = create_tool_calling_agent(build_chat_model(), tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
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
    async for event in executor.astream_events(
        {"chat_history": history, "input": user_text}, version="v1"
    ):
        event_type = event["event"]
        if event_type == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            content = getattr(chunk, "content", None) if chunk is not None else None
            if isinstance(content, str) and content:
                yield {"type": "token", "content": content}
        elif event_type == "on_tool_start":
            yield {
                "type": "tool_start",
                "name": event.get("name", ""),
                "input": event.get("data", {}).get("input"),
            }
        elif event_type == "on_tool_end":
            yield {"type": "tool_end", "name": event.get("name", "")}
    yield {"type": "done"}
