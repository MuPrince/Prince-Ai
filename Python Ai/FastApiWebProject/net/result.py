from datetime import datetime
from typing import Generic, TypeVar, List, Any

from pydantic import BaseModel

# 定义类型变量 T，代表 items 中元素的类型
T = TypeVar('T')

class Result(BaseModel, Generic[T]):
    code: int
    message: str
    data: T
    timestamp: str

    # def model_dump(self) -> dict:
    #     return {
    #         "code": self.code,
    #         "message": self.message,
    #         "data": self.data,
    #         "timestamp": self.timestamp
    #     }


class PageResponse(BaseModel, Generic[T]):
    total: int
    page: int
    pageSize: int
    items: List[T]


def success(data: T):
    return Result(
        data = data,
        code = 200,
        message="success",
        timestamp = datetime.now().isoformat()
    )


def fail(message:str, code: int = 500, data: T = None):
    return Result(data = data, message = message, code = code, timestamp = datetime.now().isoformat())


def success_response(data: Any = None, message: str = "操作成功") -> dict:
    return {
        "message": message,
        "data": data,
        "code": 200,
        "timestamp": datetime.now().isoformat()
    }


def error_response(message: str = "操作失败", code: int = 500, error: str = None) -> dict:
    return {
        "message": message,
        "code": code,
        "timestamp": datetime.now().isoformat(),
        "error": error
    }

