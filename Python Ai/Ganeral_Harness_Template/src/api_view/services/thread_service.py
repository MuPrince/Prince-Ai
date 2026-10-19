"""会话（Threads）相关业务。"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def list_threads(org_id: str, only_mine: bool, user_id: Optional[str]) -> List[dict]:
    print(
        f"[thread_service.list_threads] GET /api/threads "
        f"org_id={org_id} only_mine={only_mine} user_id={user_id}"
    )
    return []


def get_history(thread_id: str) -> dict:
    print(f"[thread_service.get_history] GET /api/history/{thread_id}")
    return {"thread_id": thread_id, "messages": []}


def delete_thread(thread_id: str) -> None:
    print(f"[thread_service.delete_thread] DELETE /api/threads/{thread_id}")
