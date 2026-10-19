import asyncio
import selectors
import sys
from pathlib import Path

# 把 src/ 放到 sys.path 顶部，使 api_view / agent 等包可被绝对导入
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from uvicorn import Config, Server

from api_view import app


async def serve():
    """uvicorn 启动协程：创建 Server 并运行。"""
    config = Config(app=app, host="127.0.0.1", port=8000)
    server = Server(config)
    await server.serve()


if __name__ == '__main__':
    if sys.platform == "win32":
        # Windows + Python 3.14：psycopg 异步模式需要 SelectorEventLoop
        # asyncio.set_event_loop_policy() 已弃用且对 uvicorn.run() 无效，
        # 必须通过 asyncio.run() 的 loop_factory 显式创建 SelectorEventLoop
        asyncio.run(
            serve(),
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        )
    else:
        asyncio.run(serve())
