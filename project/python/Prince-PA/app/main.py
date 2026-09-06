from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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


WEB_DIST = Path(__file__).resolve().parents[1] / "web" / "dist"
if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="接口不存在")
        candidate = WEB_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(WEB_DIST / "index.html")
