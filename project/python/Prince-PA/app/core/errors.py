from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=400, content={"code": "bad_request", "message": str(exc)}
        )

    @app.exception_handler(LookupError)
    async def not_found_handler(request: Request, exc: LookupError):
        return JSONResponse(
            status_code=404, content={"code": "not_found", "message": str(exc)}
        )
