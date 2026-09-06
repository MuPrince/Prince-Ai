from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.task import LanguageCreate, LanguageOut
from app.services.language_service import get_or_create_language, list_languages

router = APIRouter(prefix="/api/languages", tags=["languages"])


@router.get("", response_model=list[LanguageOut])
def api_list_languages(db: Session = Depends(get_db)):
    return list_languages(db)


@router.post("", response_model=LanguageOut, status_code=201)
def api_create_language(payload: LanguageCreate, db: Session = Depends(get_db)):
    try:
        lang = get_or_create_language(db, payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    db.commit()
    return LanguageOut.model_validate(lang)
