from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router as api_router
from app.clients.ledger import ExpensesUnavailableError, GroupNotFoundError
from app.config import get_settings
from app.logging_mw import RequestLogMiddleware, configure_logging
from app.security import require_api_key


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    app = FastAPI(title=f"{settings.service_name}-service")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origin],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-API-Key"],
    )
    app.add_middleware(RequestLogMiddleware, service_name=settings.service_name)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": settings.service_name}

    @app.exception_handler(ExpensesUnavailableError)
    def expenses_unavailable(request: Request, exc: ExpensesUnavailableError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"error": str(exc)}
        )

    @app.exception_handler(GroupNotFoundError)
    def group_not_found(request: Request, exc: GroupNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    app.include_router(api_router, dependencies=[Depends(require_api_key)])
    return app


app = create_app()
