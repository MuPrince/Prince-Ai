"""Agent 运行时上下文：贯穿每次调用的用户/组织标识。

仅使用 pydantic.BaseModel，不再与 dataclass 混用。
"""
from pydantic import BaseModel


class ContextType(BaseModel):
    user_id: str = "local_user"
    org_id: str = "default_org"
