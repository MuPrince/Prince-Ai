from pydantic import BaseModel, Field
from typing import Optional, Any, Generic, TypeVar
from datetime import datetime

T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    success: bool = True
    message: str = "操作成功"
    data: Optional[Any] = None
    code: int = 200
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ErrorResponse(BaseModel):
    success: bool = False
    message: str = "操作失败"
    code: int = 500
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None


class ChatRequest(BaseModel):
    messages: str
    message_id: str
    image_url: Optional[str] = None


class SuccessResponse(BaseModel):
    success: bool = True
    message: str = "操作成功"
    code: int = 200


def success_response(data: Any = None, message: str = "操作成功") -> dict:
    return {
        "success": True,
        "message": message,
        "data": data,
        "code": 200,
        "timestamp": datetime.now().isoformat()
    }


def error_response(message: str = "操作失败", code: int = 500, error: str = None) -> dict:
    return {
        "success": False,
        "message": message,
        "code": code,
        "timestamp": datetime.now().isoformat(),
        "error": error
    }
