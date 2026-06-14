from contextlib import asynccontextmanager
from datetime import date, datetime

import uvicorn
from fastapi import FastAPI, Query
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

import api.user as user
from database.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("启动：初始化数据库连接")
    app.state.db_pool = await init_db()

    yield


    print("关闭：释放资源")
    await app.state.db_pool.close()

app = FastAPI(lifespan=lifespan)

app.include_router(user.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def middleware(request:Request, call_next):
    print(f"""收到请求：{request.url} ,{datetime.now()}""")
    response = await call_next(request)
    print("响应请求：", request.url)
    return response


@app.get("/")
async def root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)