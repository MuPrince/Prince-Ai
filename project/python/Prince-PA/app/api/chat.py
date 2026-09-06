import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from agents.assistant import stream_agent_response
from app.api.deps import get_session_factory
from app.core.database import get_db
from app.models.entities import MessageRole
from app.schemas.chat import ChatRequest
from app.services.chat_service import (
    create_message,
    create_session,
    get_session,
    list_messages,
    list_sessions,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/sessions")
def api_create_session(db: Session = Depends(get_db)):
    return create_session(db)


@router.get("/sessions")
def api_list_sessions(db: Session = Depends(get_db)):
    return list_sessions(db)


@router.get("/sessions/{session_id}/messages")
def api_list_messages(session_id: int, db: Session = Depends(get_db)):
    try:
        get_session(db, session_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="会话不存在")
    return list_messages(db, session_id)


@router.post("/sessions/{session_id}/messages")
def api_send_message(
    session_id: int,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    session_factory=Depends(get_session_factory),
):
    try:
        get_session(db, session_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="会话不存在")
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    create_message(db, session_id, MessageRole.user, payload.content)

    async def events():
        assistant_text = ""
        try:
            async for item in stream_agent_response(session_factory, session_id, payload.content):
                if item.get("type") == "token":
                    assistant_text += item["content"]
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)}, ensure_ascii=False)}\n\n"
        finally:
            with session_factory() as persist_db:
                create_message(
                    persist_db,
                    session_id,
                    MessageRole.assistant,
                    assistant_text or "（无回复）",
                )

    return StreamingResponse(events(), media_type="text/event-stream")
