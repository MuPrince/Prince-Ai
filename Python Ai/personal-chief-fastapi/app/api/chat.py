from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models.schemas import success_response

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/message", summary="发送聊天消息")
async def send_chat_message(message: str):
    return JSONResponse(content=success_response(
        data={"message": "消息发送成功"},
        message="操作成功"
    ))


@router.get("/stream", summary="获取聊天流")
async def get_chat_stream():
    return JSONResponse(content=success_response(
        data={"stream": "聊天流数据"},
        message="获取成功"
    ))


@router.delete("/message", summary="删除聊天消息")
async def delete_chat_message(message_id: str):
    return JSONResponse(content=success_response(
        data={"message_id": message_id},
        message="删除成功"
    ))
