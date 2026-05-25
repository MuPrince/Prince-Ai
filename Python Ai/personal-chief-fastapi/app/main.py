import app.api.chat as chat
import app.api.oss as oss
import os

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

from app.common.logger import setup_logging

setup_logging()

app = FastAPI(
    title="Personal Chief API",
    version="1.0",
    description="API for personal chef services",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "static")

app.include_router(chat.router, prefix="/api")
app.include_router(oss.router, prefix="/api")


@app.get("/{path:path}", include_in_schema=False)
async def serve_frontend(path: str):
    #排除API路径

    if path.startswith("api/"):
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Not Found"}, status_code=404)
    # 如果请求的是静态文件，直接返回
    file_path = os.path.join(static_dir, path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    # 否则返回 index.html (SPA fallback)
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message":"你的独家私厨上线了~", "status":"ok"}

if __name__ == "__main__":
    import uvicorn
    # 启动命令：python -m app.main
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)