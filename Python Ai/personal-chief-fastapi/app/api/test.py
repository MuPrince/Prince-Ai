from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models.schemas import success_response

router = APIRouter(prefix="/test", tags=["Test"])


@router.get("/test")
async def test():
    return JSONResponse(content=success_response(
        data={"message": "这是个测试接口，你的请求联通了"},
        message="操作成功"
    ))
