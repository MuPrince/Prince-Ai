"""
沙箱文件下载：从本地 download/ 目录读取已持久化的产物文件。

说明：
- 沙箱任务完成后，产物已自动持久化到 download/{task_id}/
- 用户通过 /api/sandbox/download?path=... 下载时，从 download/ 读取
- 不再实时从沙箱拉取，避免沙箱已销毁导致下载失败
"""
import logging
from pathlib import Path
from typing import Tuple

from agent.backends.sandbox import DOWNLOAD_ROOT

logger = logging.getLogger(__name__)


def download(path: str, org_id: str) -> Tuple[bytes, str]:
    """
    从 download/ 目录读取文件。

    path 格式支持两种：
    1. task_id/filename（推荐，明确指定任务目录）
    2. /workspace/outputs/xxx 或 /workspace/skills/xxx（尝试匹配 task_id）

    返回: (文件字节, 文件名)
    """
    # 清理路径，防止目录遍历
    clean_path = path.strip().lstrip("/")
    if ".." in clean_path:
        raise ValueError("非法路径：不允许目录遍历")

    # 尝试直接匹配 task_id/filename 格式
    candidate = DOWNLOAD_ROOT / clean_path
    if candidate.exists() and candidate.is_file():
        return _read_file(candidate)

    # 尝试从路径中提取 task_id（兼容 /workspace/outputs/ 等沙箱路径格式）
    # 例如：/workspace/outputs/abc123/report.pptx -> 尝试匹配 download/abc123/report.pptx
    parts = clean_path.split("/")
    for i, part in enumerate(parts):
        if part in ("outputs", "skills", "dist", "analysis", "convert", "debug", "batch", "env"):
            # 取下一级作为 task_id
            if i + 1 < len(parts):
                task_id = parts[i + 1]
                filename = parts[-1] if parts else "download.bin"
                candidate = DOWNLOAD_ROOT / task_id / filename
                if candidate.exists() and candidate.is_file():
                    return _read_file(candidate)

    # 未找到文件
    raise FileNotFoundError(f"文件不存在或已过期: {path}")


def _read_file(filepath: Path) -> Tuple[bytes, str]:
    """读取文件并返回字节流与文件名。"""
    try:
        data = filepath.read_bytes()
        filename = filepath.name
        logger.info(f"[sandbox_service.download] 读取文件 {filepath} ({len(data)} bytes)")
        return data, filename
    except Exception as e:
        logger.error(f"[sandbox_service.download] 读取文件失败 {filepath} - {e}")
        raise
