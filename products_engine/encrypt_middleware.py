import json
import os
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from crypto_util import encrypt_payload


def _encrypt_enabled() -> bool:
    return os.getenv("ENCRYPT_RESPONSES", "").lower() in ("1", "true", "yes")


def _skip_path(path: str) -> bool:
    return (
        path.startswith("/docs")
        or path.startswith("/openapi")
        or path.startswith("/redoc")
        or path == "/health"
        or path.startswith("/tasks/")
    )


class EncryptJsonMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not _encrypt_enabled():
            return await call_next(request)

        response = await call_next(request)
        if _skip_path(request.url.path):
            return response

        ct = response.headers.get("content-type", "")
        if response.status_code != 200 or "application/json" not in ct:
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        try:
            payload = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        encrypted = encrypt_payload(payload)
        encoded = json.dumps(encrypted).encode("utf-8")
        headers = {
            k: v
            for k, v in response.headers.items()
            if k.lower() not in ("content-length", "content-type")
        }
        headers["content-type"] = "application/json"
        return Response(content=encoded, status_code=response.status_code, headers=headers)
