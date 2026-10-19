"""Mock Java 服务端 Api：开发阶段替代真实 Java 服务。

按 mcp_server/client.py 依赖的契约实现全部接口，数据保存在内存中，
上传 / 入库 / 删除会真实改变知识库列表，因此 upload -> add -> list 的
完整链路可以脱离真实 Java 服务完成联调。

两种用法：

1. 随 MCP 服务一起启动（单进程，推荐）：
       python src/mcp_server/server.py --mock

2. 独立进程启动（可同时被前端等其他调用方复用）：
       python src/mcp_server/mock_java_api.py                 # 127.0.0.1:8001
       python src/mcp_server/mock_java_api.py --port 9001

说明：mock 不校验 Authorization，真实服务的 Bearer 鉴权不在开发阶段覆盖。
"""
import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

# 把 src/ 放到 sys.path 顶部，使 mcp_server 包可被绝对导入（与 main.py 一致）
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import uvicorn
from fastapi import FastAPI, File, UploadFile

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8001

# 内存中的知识库文件列表，随 add / delete 变化
_documents: List[str] = ["员工手册.pdf", "差旅报销规范.md", "产品需求文档.docx"]

# 无法从文件内容切分出的兜底段落
_FALLBACK_SPLITS = [
    "第一段：本文件由 Mock Java Api 返回，用于开发阶段联调。",
    "第二段：切分结果仅为占位内容，不代表真实知识库切分策略。",
]

app = FastAPI(title="Mock Java Api", description="MCP 服务开发联调用 Mock，非真实业务服务")


def _ok(data: Any) -> Dict[str, Any]:
    """按 Spring Boot 风格响应包裹返回成功结果。"""
    return {"code": 0, "message": "ok", "data": data}


def _split_content(content: bytes) -> List[str]:
    """按空行切分上传文件文本；内容非纯文本时返回兜底段落。"""
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return list(_FALLBACK_SPLITS)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return paragraphs or list(_FALLBACK_SPLITS)


@app.get("/api/rag/list")
async def rag_list() -> Dict[str, Any]:
    """知识库文件列表。"""
    return _ok([{"name": name} for name in _documents])


@app.put("/api/rag/upload")
async def rag_upload(file: UploadFile = File(...)) -> Dict[str, Any]:
    """上传文件并返回切分结果（不入库）。"""
    splits = _split_content(await file.read())
    return _ok({"filename": file.filename, "splits": [{"content": s} for s in splits]})


@app.post("/api/rag/add")
async def rag_add(payload: Dict[str, Any]) -> Dict[str, Any]:
    """把切分内容入库：仅登记文件名，供列表接口体现链路效果。"""
    filename = payload.get("filename") or "未命名文件"
    if filename not in _documents:
        _documents.append(filename)
    return _ok({"added": len(payload.get("splits") or [])})


@app.delete("/api/rag/delete")
async def rag_delete(file_path: str) -> Dict[str, Any]:
    """按文件名删除知识库文件。"""
    removed = file_path in _documents
    if removed:
        _documents.remove(file_path)
    return _ok({"deleted": file_path, "removed": removed})


@app.post("/api/rag/chat")
async def rag_chat(payload: Dict[str, Any]) -> Dict[str, Any]:
    """知识库问答。"""
    question = payload.get("message") or ""
    return _ok({"message": f"[知识库问答·mock] 针对「{question}」检索到的答案是占位内容。"})


@app.post("/api/service/chat")
async def service_chat(payload: Dict[str, Any]) -> Dict[str, Any]:
    """智能客服问答。"""
    question = payload.get("message") or ""
    return _ok({"message": f"[智能客服·mock] 已收到「{question}」，客服稍后回复。"})


def main() -> None:
    """命令行入口：独立启动 Mock 服务。"""
    parser = argparse.ArgumentParser(description="Mock Java 服务端 Api（开发联调用）")
    parser.add_argument("--host", default=DEFAULT_HOST, help="监听地址")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="监听端口")
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
