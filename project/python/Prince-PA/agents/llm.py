from langchain_deepseek import ChatDeepSeek

from app.core.config import settings


def build_chat_model() -> ChatDeepSeek:
    return ChatDeepSeek(
        model="deepseek-chat",
        api_key=settings.deepseek_api_key,
        temperature=0.3,
        max_tokens=4000,
    )
