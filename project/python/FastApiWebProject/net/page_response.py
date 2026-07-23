from typing import Generic, TypeVar, List

from pydantic import BaseModel

# 定义类型变量 T，代表 items 中元素的类型
T = TypeVar('T')

class PageResponse(BaseModel, Generic[T]):
    total: int
    page: int
    pageSize: int
    items: List[T]