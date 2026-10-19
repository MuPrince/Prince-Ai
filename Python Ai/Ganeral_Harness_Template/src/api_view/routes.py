"""
API 路由定义层。

本模块只做 HTTP 参数解析与响应封装，业务实现位于 api_view/services/。
当前所有 service 实现均为打印接口路径 + 返回 mock 数据，便于前端联调。
"""

import logging
import urllib.parse
from typing import List, Literal, Optional

from fastapi import APIRouter, File, Form, Path, Query, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from .services import (
    chat_service,
    file_service,
    sandbox_service,
    thread_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# 通用模型
# ============================================================

class ThreadInfo(BaseModel):
    """会话列表条目。"""
    thread_id: str
    last_message: Optional[str] = None
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    updated_at: Optional[float] = None


class ChatMessage(BaseModel):
    """历史消息条目。"""
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    reasoning: Optional[str] = None


class ThreadHistoryResponse(BaseModel):
    thread_id: str
    messages: List[ChatMessage]


class ChatStreamRequest(BaseModel):
    """普通聊天流式请求体。"""
    message: str
    thread_id: str
    user_id: str = "local-user"
    org_id: str = "default-org"


class ChatWithFileStreamRequest(ChatStreamRequest):
    """带文件的聊天流式请求体。"""
    file_id: str


class FileUploadResponse(BaseModel):
    """文件上传结果。"""
    file_id: str
    filename: str
    file_type: str
    row_count: int = 0
    columns: List[str] = Field(default_factory=list)
    # direct: 直接把内容塞进 prompt; code_execution: 交给 Agent 在沙箱写代码分析
    analysis_type: Literal["direct", "code_execution"] = "direct"
    code: Optional[str] = None


# ============================================================
# 会话（Threads）
# ============================================================

@router.get("/threads", response_model=List[ThreadInfo], summary="列出会话")
async def list_threads(
    org_id: str = Query(..., description="组织 ID，用于隔离不同组织的会话"),
    only_mine: bool = Query(False, description="是否只返回当前用户的会话"),
    user_id: Optional[str] = Query(None, description="当 only_mine=true 时必传"),
) -> List[ThreadInfo]:
    """按 org_id（可选 user_id）筛选历史会话列表，按更新时间倒序。"""
    return thread_service.list_threads(org_id=org_id, only_mine=only_mine, user_id=user_id)


@router.get("/history/{thread_id}", response_model=ThreadHistoryResponse, summary="获取会话历史")
async def get_thread_history(
    thread_id: str = Path(..., description="会话 ID"),
) -> ThreadHistoryResponse:
    """返回某个 thread_id 下的全部历史消息（含 reasoning 字段）。"""
    return thread_service.get_history(thread_id)


@router.delete("/threads/{thread_id}", status_code=204, summary="删除会话")
async def delete_thread(
    thread_id: str = Path(..., description="会话 ID"),
) -> Response:
    """删除会话及其所有 checkpoint / store 记录。"""
    thread_service.delete_thread(thread_id)
    return Response(status_code=204)


# ============================================================
# 聊天（Chat，SSE 流式）
# ============================================================

@router.post("/chat/stream", summary="流式聊天（SSE）")
async def chat_stream(body: ChatStreamRequest) -> StreamingResponse:
    """
    与 Agent 对话，SSE 推送增量。

    事件类型（data: {...}\\n\\n）：
      - token:            {type, content}                正文增量
      - reasoning_token:  {type, content}                思考增量
      - tool_call:        {type, name}                   工具开始调用
      - tool_result:      {type}                         工具调用结束
      - done:             {type, reply, reasoning}       流结束，汇总值
      - error:            {type, message}                流内错误
    """
    return StreamingResponse(
        chat_service.stream_chat(
            message=body.message,
            thread_id=body.thread_id,
            user_id=body.user_id,
            org_id=body.org_id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat-with-file/stream", summary="带文件的流式聊天（SSE）")
async def chat_with_file_stream(body: ChatWithFileStreamRequest) -> StreamingResponse:
    """
    与 /chat/stream 类似，但额外携带 file_id。
    Agent 根据文件的 analysis_type 决定直接注入上下文还是在沙箱内执行代码分析。
    """
    return StreamingResponse(
        chat_service.stream_chat_with_file(
            message=body.message,
            thread_id=body.thread_id,
            user_id=body.user_id,
            org_id=body.org_id,
            file_id=body.file_id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ============================================================
# 文件（Files）
# ============================================================

@router.post("/files/upload", response_model=FileUploadResponse, summary="上传文件")
async def upload_file(
    file: UploadFile = File(...),
    org_id: str = Form("default-org"),
) -> FileUploadResponse:
    """
    上传 CSV / Excel / TXT 等文件，返回 file_id 与分析方式（direct / code_execution）。
    小文件 → direct（直接读取摘要）；大文件 → code_execution（沙箱分析）。
    """
    content = await file.read()
    return await file_service.upload(file_bytes=content, filename=file.filename or "unnamed", org_id=org_id)


@router.delete("/files/{file_id}", status_code=204, summary="删除已上传文件")
async def delete_file(
    file_id: str = Path(..., description="文件 ID"),
) -> Response:
    """删除之前上传的文件（含磁盘与索引记录）。"""
    file_service.delete(file_id)
    return Response(status_code=204)


# ============================================================
# 沙箱（Sandbox）：仅为用户下载 Agent 产物保留 download
# ============================================================

@router.get("/sandbox/download", summary="下载 Agent 在沙箱中生成的文件")
async def sandbox_download(
    path: str = Query(..., description="沙箱内绝对路径，如 /workspace/output/report.pptx"),
    org_id: str = Query("default-org"),
) -> Response:
    """
    Agent 在沙箱中生成产物（PPT / 报表 / 压缩包等）后，会在回答中输出
    `/api/sandbox/download?path=...` 链接，用户点击即可下载到本地。
    """
    content, filename = sandbox_service.download(path=path, org_id=org_id)
    # Content-Disposition 只能放 latin-1 字符：中文等非 ASCII 文件名必须
    # 走 RFC 5987 的 filename*=UTF-8''<percent-encoded>，并附 ASCII 兜底名
    ascii_fallback = filename.encode("ascii", errors="replace").decode("ascii")
    quoted = urllib.parse.quote(filename)
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{ascii_fallback}\"; "
                f"filename*=UTF-8''{quoted}"
            )
        },
    )
