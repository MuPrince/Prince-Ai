from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List


from app.models.schemas import success_response, error_response
from app.common.embedding import compute_embeddings
from app.common.milvus import insert_chunks, create_collection, get_collection

router = APIRouter(prefix="/rag", tags=["RAG"])

ALLOWED_EXTENSIONS = {"doc", "docx", "md", "txt", "pdf"}


def get_file_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def split_text_by_length(content: str, chunk_size: int = 500, overlap: int = 50) -> list:
    if not content:
        return []

    chunks = []
    start = 0
    content_length = len(content)

    while start < content_length:
        end = start + chunk_size
        chunk = content[start:end]
        chunks.append(chunk)
        start = end - overlap

    return chunks


class Knowledge(BaseModel):
    filename: str
    splits: List[str]


@router.post("/add", summary="添加知识库文档")
async def add_knowledge_file(knowledge: Knowledge):
    try:
        if not knowledge.filename or not knowledge.splits:
            return JSONResponse(content=error_response(
                message="文件名和文档内容不能为空",
                code=400
            ))

        if create_collection() is None:
            return JSONResponse(content=error_response(
                message="向量数据库连接失败，请检查 Milvus 配置",
                code=500
            ))

        chunks = knowledge.splits

        embeddings = compute_embeddings(chunks)

        success = insert_chunks(
            file_name=knowledge.filename,
            chunks=chunks,
            embeddings=embeddings
        )

        if not success:
            return JSONResponse(content=error_response(
                message="文档向量存入数据库失败",
                code=500
            ))

        return JSONResponse(content=success_response(
            data={
                "filename": knowledge.filename,
                "chunk_count": len(chunks),
                "embedding_dimension": len(embeddings[0]) if embeddings else 0
            },
            message="文档添加成功"
        ))

    except Exception as e:
        return JSONResponse(content=error_response(
            message=f"添加文档失败: {str(e)}",
            code=500
        ))


@router.post("/query", summary="查询知识库文件")
async def query_knowledge_file(
    query: str = Query(..., description="查询关键词")
):
    return JSONResponse(content=success_response(message="查询成功"))


@router.put("/upload", summary="上传知识库文件")
async def upload_knowledge_files(file: UploadFile = File(..., description="要上传的知识库文件")):
    ext = get_file_extension(file.filename)

    if ext not in ALLOWED_EXTENSIONS:
        return JSONResponse(content=error_response(
            message=f"不支持的文件格式，仅支持: {', '.join(ALLOWED_EXTENSIONS)}",
            code=400
        ))

    content = await file.read()
    content = content.decode("utf-8", errors="ignore")

    chunks = split_text_by_length(content, chunk_size=500, overlap=50)

    return JSONResponse(content=success_response(
        data={
            "filename": file.filename,
            "total_chunks": len(chunks),
            "splits": [{"content": chunk, "index": i} for i, chunk in enumerate(chunks)]
        },
        message="上传成功"
    ))


@router.get("/list", summary="获取知识库文件列表")
async def list_knowledge_files():
    return JSONResponse(content=success_response(
        data=[{"name": "假文件1", "size": 10}, {"name": "假文件2", "size": 15}, {"name": "假文件3", "size": 20}],
        message="获取成功"
    ))

from app.agents.rag_agent import stream_response
from fastapi.responses import StreamingResponse

@router.get("/chat", summary="调用 RAG 模型")
def agent(query: str):

    return StreamingResponse(
        stream_response(query),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用代理缓冲
            "Access-Control-Allow-Origin": "*",
        }
    )
