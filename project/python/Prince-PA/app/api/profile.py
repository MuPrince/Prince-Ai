from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from agents.memory import profile as memory_profile
from app.api.deps import get_session_factory
from app.core.database import get_db
from app.schemas.profile import PreferenceOut, ProfileSnapshotOut

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileSnapshotOut)
def api_get_profile(db: Session = Depends(get_db)):
    return ProfileSnapshotOut(
        profile=memory_profile.latest_profile(db),
        pending=[
            PreferenceOut.model_validate(p) for p in memory_profile.list_pending(db)
        ],
    )


@router.post("/extract")
def api_extract_profile(
    background: BackgroundTasks, session_factory=Depends(get_session_factory)
):
    background.add_task(memory_profile.trigger_manual_extract, session_factory)
    return {"status": "started"}


@router.post("/preferences/{preference_id}/confirm", response_model=PreferenceOut)
def api_confirm_preference(preference_id: int, db: Session = Depends(get_db)):
    try:
        return memory_profile.confirm_preference(db, preference_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="偏好项不存在")


@router.post("/preferences/{preference_id}/dismiss", response_model=PreferenceOut)
def api_dismiss_preference(preference_id: int, db: Session = Depends(get_db)):
    try:
        return memory_profile.dismiss_preference(db, preference_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="偏好项不存在")
