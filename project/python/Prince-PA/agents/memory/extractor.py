import json

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import build_chat_model
from app.models.entities import Task


def extract_preferences(
    task: Task,
    note_content: str,
    summary_content: str,
    chat_snippets: list[str],
    model: BaseChatModel | None = None,
) -> list[dict]:
    chat = model or build_chat_model()
    system = (
        "你是Prince-PA的用户画像提炼器。根据任务信息、笔记、总结与对话片段，"
        "提炼用户偏好。只输出JSON数组："
        '[{"dimension":"learning_focus|learning_style|summary_style|response_style",'
        '"value":"中文摘要","confidence":0到1,"evidence":"来源摘录"}]。'
        "没有依据的维度不要输出。"
    )
    user = (
        f"任务：{task.language.name} / {task.title}\n"
        f"笔记：{note_content}\n总结：{summary_content}\n对话：{chr(10).join(chat_snippets[-20:])}"
    )
    response = chat.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    raw = response.content
    if isinstance(raw, list):
        raw = "".join(str(part.get("text", "")) for part in raw if isinstance(part, dict))
    text = str(raw).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    parsed = json.loads(text)
    if isinstance(parsed, dict):
        parsed = parsed.get("preferences", [])
    return [item for item in parsed if isinstance(item, dict)]
