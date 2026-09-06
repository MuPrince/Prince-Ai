from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import build_chat_model
from app.models.entities import Task


def generate_summary(
    task: Task,
    note_content: str,
    model: BaseChatModel | None = None,
) -> str:
    chat = model or build_chat_model()
    system = (
        "你是Prince-PA学习助理的总结引擎。根据任务信息和笔记内容生成结构化"
        "中文Markdown总结，使用如下结构：# <主题>总结；## 学习要点；## 实践记录；"
        "## 问题与反思。笔记为空时，基于任务描述输出要点并注明'笔记尚未填写'。"
        "不要虚构未出现在素材中的事实。"
    )
    material = note_content or task.description or "（该任务暂无可参考笔记）"
    user_text = f"任务语言：{task.language.name}\n任务主题：{task.title}\n参考素材：\n{material}"
    response = chat.invoke([SystemMessage(content=system), HumanMessage(content=user_text)])
    return str(response.content)
