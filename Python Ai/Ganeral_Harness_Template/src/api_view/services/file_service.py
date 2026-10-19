"""文件上传 / 删除相关业务。"""
import uuid


async def upload(file_bytes: bytes, filename: str, org_id: str) -> dict:
    print(
        f"[file_service.upload] POST /api/files/upload "
        f"filename={filename} org_id={org_id} size={len(file_bytes)}"
    )
    return {
        "file_id": f"file-{uuid.uuid4().hex[:8]}",
        "filename": filename,
        "file_type": "unknown",
        "row_count": 0,
        "columns": [],
        "analysis_type": "direct",
        "code": None,
    }


def delete(file_id: str) -> None:
    print(f"[file_service.delete] DELETE /api/files/{file_id}")
