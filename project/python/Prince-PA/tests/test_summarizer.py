from typing import ClassVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from agents.summarizer import generate_summary
from app.models.entities import Language, Task


class FakeChatModel(BaseChatModel):
    """记录收到的消息并返回固定总结。"""

    received_messages: ClassVar[list] = []

    @property
    def _llm_type(self) -> str:
        return "fake-chat"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        type(self).received_messages = list(messages)
        content = "# 总结\n\n来自 fake 模型的输出"
        message = AIMessage(content=content)
        return ChatResult(generations=[ChatGeneration(message=message)])


def _task():
    return Task(id=1, language=Language(name="Python"), title="LangChain", description="d")


def test_generate_summary_uses_model(db_session):
    model = FakeChatModel()
    result = generate_summary(_task(), "# 笔记正文", model=model)
    assert result == "# 总结\n\n来自 fake 模型的输出"
    joined = "\n".join(m.content for m in FakeChatModel.received_messages)
    assert "LangChain" in joined
    assert "# 笔记正文" in joined
