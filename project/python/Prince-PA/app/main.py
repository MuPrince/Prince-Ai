from fastapi import FastAPI

from app.api import chat, languages, notes, profile, records, summaries, tasks
from app.core.errors import install_exception_handlers

app = FastAPI(title="Prince-PA", version="0.1.0")
install_exception_handlers(app)
app.include_router(languages.router)
app.include_router(tasks.router)
app.include_router(notes.router)
app.include_router(summaries.router)
app.include_router(records.router)
app.include_router(chat.router)
app.include_router(profile.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
