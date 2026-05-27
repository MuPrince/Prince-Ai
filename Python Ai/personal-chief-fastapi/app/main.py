import app.api.chat as chat
import app.api.oss as oss
import app.api.test as test
import app.api.rag as rag

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

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

app.include_router(chat.router, prefix="/api")
app.include_router(oss.router, prefix="/api")
app.include_router(test.router, prefix="/api")
app.include_router(rag.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "你的独家私厨上线了~", "status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)
