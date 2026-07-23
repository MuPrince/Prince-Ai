import time

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_session
from database.user_model import User
from net.page_request import common_page, PageParams
from net.page_response import PageResponse

from net.result import Result, success

router = APIRouter(prefix="/users", tags=["user"])

from pydantic import BaseModel

class UserResponse(BaseModel):
    id: int
    nickname: str
    profile: str | None = None   # 如果允许为空
    bio: str | None = None

    class Config:
        from_attributes = True   # SQLAlchemy 2.0 风格，将 ORM 对象转换为字典


@router.get("/page", response_model=Result[PageResponse[UserResponse]])
async def get_users(page: PageParams = Depends(common_page), session: AsyncSession = Depends(get_session)):
    print("查询用户")
    """分页获取用户列表"""
    # 查询用户（按 id 排序保证分页稳定性）
    sql = select(User).order_by(User.id).offset(page.page * page.pageSize).limit(page.pageSize)
    result = await session.execute(sql)
    users = result.scalars().all()  # 获取所有 User 对象

    # 如果 users 为空列表，FastAPI 会正常返回 []
    # return Result(data=PageResponse(total = len(users), items = list(users), page = page.page, pageSize = page.pageSize), code=200, message="查询成功", timestamp=int(time.time_ns() / 1000000))
    return success(PageResponse(total = len(users), items = list(users), page = page.page, pageSize = page.pageSize))
