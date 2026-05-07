from __future__ import annotations

import os
import secrets
from typing import Callable

from fastapi.openapi.utils import get_openapi
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp


def supervisor_auth_path_exempt(path: str) -> bool:
    """Return True for routes that stay reachable without auth."""
    if path in ("/health", "/docs", "/redoc", "/openapi.json"):
        return True
    if path.startswith("/docs/") or path.startswith("/redoc/"):
        return True
    return False


class SupervisorBearerAuthMiddleware(BaseHTTPMiddleware):
    """Require Authorization: Bearer <SUPERVISOR_API_KEY> except exempt paths."""

    def __init__(self, app: ASGIApp, api_key: str):
        super().__init__(app)
        self._api_key = api_key.strip()
        if not self._api_key:
            raise ValueError("SupervisorBearerAuthMiddleware requires non-empty api_key")

    async def dispatch(self, request: Request, call_next: Callable):
        if supervisor_auth_path_exempt(request.url.path):
            return await call_next(request)
        auth = request.headers.get("Authorization") or ""
        if not auth.startswith("Bearer "):
            return JSONResponse(
                {"detail": "Missing or invalid Authorization header"},
                status_code=401,
            )
        token = auth[7:].strip()
        if not secrets.compare_digest(token, self._api_key):
            return JSONResponse({"detail": "Invalid API key"}, status_code=403)
        return await call_next(request)


def install_openapi_bearer_for_swagger(app) -> None:
    """Inject BearerAuth into OpenAPI so Swagger Authorize can be used."""

    def _custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            routes=app.routes,
            tags=getattr(app, "openapi_tags", None),
            servers=getattr(app, "servers", None),
        )
        schema.setdefault("components", {}).setdefault("securitySchemes", {}).update(
            {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "API Key",
                    "description": (
                        "When SUPERVISOR_API_KEY is set, send "
                        "`Authorization: Bearer <key>` to call protected routes."
                    ),
                }
            }
        )
        schema["security"] = [{"BearerAuth": []}]
        for path, path_item in (schema.get("paths") or {}).items():
            if supervisor_auth_path_exempt(path):
                for op in path_item.values():
                    if isinstance(op, dict):
                        op["security"] = []
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = _custom_openapi


def install_supervisor_auth_if_configured(app) -> bool:
    """
    Install optional Bearer auth middleware for supervisor routes.

    Returns True when auth is enabled, else False.
    """
    key = (os.environ.get("SUPERVISOR_API_KEY") or "").strip()
    if not key:
        return False
    app.add_middleware(SupervisorBearerAuthMiddleware, api_key=key)
    install_openapi_bearer_for_swagger(app)
    return True
