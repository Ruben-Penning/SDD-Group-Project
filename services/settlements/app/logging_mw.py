"""One JSON log line per request to stdout: method, path, status, duration."""

import json
import logging
import sys
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("request")


def configure_logging() -> None:
    """Add one stdout handler (once) and log at INFO level."""
    root = logging.getLogger()
    if not any(getattr(h, "is_app_stdout", False) for h in root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler.is_app_stdout = True
        root.addHandler(handler)
    root.setLevel(logging.INFO)
    # Keep log volume low: no per-call lines from the HTTP client.
    logging.getLogger("httpx").setLevel(logging.WARNING)


class RequestLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            # Log the route template (/groups/{group_id}), not the raw path,
            # so Log Analytics queries group requests cleanly.
            route = request.scope.get("route")
            path = getattr(route, "path", request.url.path)
            logger.info(
                json.dumps(
                    {
                        "service": self.service_name,
                        "method": request.method,
                        "path": path,
                        "status": status,
                        "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                    }
                )
            )
