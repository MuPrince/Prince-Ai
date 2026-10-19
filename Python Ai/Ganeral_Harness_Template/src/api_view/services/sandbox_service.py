"""沙箱文件下载：把 Agent 在沙箱中产出的文件回传给前端用户。"""
from typing import Tuple


def download(path: str, org_id: str) -> Tuple[bytes, str]:
    """按 org_id 找到对应沙箱，读取 path 指向的文件并返回字节流与文件名。"""
    print(
        f"[sandbox_service.download] GET /api/sandbox/download "
        f"org_id={org_id} path={path}"
    )
    filename = path.rsplit("/", 1)[-1] or "download.bin"
    return b"mock file content", filename
