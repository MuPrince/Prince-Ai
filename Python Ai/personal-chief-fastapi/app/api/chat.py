from fastapi import APIRouter

from app.models.schemas import ChatRequest

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/message", summary="发送聊天消息")
async def send_chat_message(message: str):
    """
    发送聊天消息
    """
    pass

@router.get("/stream", summary="获取聊天流")
async def get_chat_stream(request: ChatRequest):
    """
    获取聊天流
    """
    pass

@router.delete("/message", summary="删除聊天消息")
async def delete_chat_message(message_id: str):
    """
    删除聊天消息
    """
    pass