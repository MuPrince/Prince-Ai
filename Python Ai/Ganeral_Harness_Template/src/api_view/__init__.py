from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from starlette.middleware.cors import CORSMiddleware

from agent.main_agnet import build_agent, close_agent

from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：构建主 agent（内部建立 Postgres 连接、加载 skills 等）
    app.state.agent = await build_agent()
    yield
    # 关闭：释放 Postgres / checkpointer / store
    await close_agent()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    """首页：优先返回前端静态页面；文件不存在时返回健康状态。"""
    frontend_path = Path(__file__).parent.parent / "static" / "index.html"
    if frontend_path.exists():
        return FileResponse(str(frontend_path))
    return {"status": "ok", "message": "AI Chat API is running"}


@app.get("/@vite/client")
async def vite_client():
    """兼容前端 dev 工具对 /@vite/client 的探测请求：返回空脚本，避免 404 噪音。"""
    return Response(content="", media_type="text/javascript")
