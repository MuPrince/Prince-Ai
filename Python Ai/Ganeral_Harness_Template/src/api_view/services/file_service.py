"""文件上传 / 读取 / 删除相关业务。

P0-4：上传字节真实落盘到 uploads/{file_id}/{filename}，返回真实 file_id；
read_upload(file_id) 读取落盘内容供沙箱导入使用。
"""
import logging
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Tuple

from agent.config.config import UPLOAD_ROOT

logger = logging.getLogger(__name__)

# file_id 安全校验：防目录穿越
_FILE_ID_RE = re.compile(r"^file-[A-Za-z0-9]+$")


def _sanitize_filename(filename: str) -> str:
    """清洗文件名：去除路径成分，仅保留 basename。"""
    name = os.path.basename(filename or "").strip()
    return name or "unnamed"


async def upload(file_bytes: bytes, filename: str, org_id: str) -> dict:
    """上传文件：字节落盘到 uploads/{file_id}/{filename}，返回真实 file_id。"""
    file_id = f"file-{uuid.uuid4().hex[:8]}"
    safe_name = _sanitize_filename(filename)

    file_dir = UPLOAD_ROOT / file_id
    file_dir.mkdir(parents=True, exist_ok=True)
    target = file_dir / safe_name
    target.write_bytes(file_bytes)

    logger.info(
        f"[file_service.upload] filename={safe_name} org_id={org_id} "
        f"size={len(file_bytes)} -> {target}"
    )
    return {
        "file_id": file_id,
        "filename": safe_name,
        "file_type": "unknown",
        "row_count": 0,
        "columns": [],
        "analysis_type": "direct",
        "code": None,
    }


def read_upload(file_id: str) -> Tuple[bytes, str]:
    """读取已上传文件内容。

    返回: (文件字节, 文件名)
    文件不存在时抛 FileNotFoundError。
    """
    if not _FILE_ID_RE.match(file_id or ""):
        raise FileNotFoundError(f"非法 file_id: {file_id}")

    file_dir = UPLOAD_ROOT / file_id
    if not file_dir.is_dir():
        raise FileNotFoundError(f"上传文件不存在: {file_id}")

    # 每个 file_id 目录下落盘单个文件，取第一个文件
    for item in sorted(file_dir.iterdir()):
        if item.is_file():
            return item.read_bytes(), item.name

    raise FileNotFoundError(f"上传文件内容缺失: {file_id}")


def delete(file_id: str) -> None:
    """删除上传文件（移除 uploads/{file_id}/ 整个目录）。"""
    logger.info(f"[file_service.delete] file_id={file_id}")
    if not _FILE_ID_RE.match(file_id or ""):
        return
    file_dir = UPLOAD_ROOT / file_id
    if file_dir.is_dir():
        shutil.rmtree(file_dir, ignore_errors=True)
