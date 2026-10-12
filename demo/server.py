"""Local-only relay for the demo; never imports or runs the ML model.

Run from the repository root with ``python -m demo.server``.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)
REQUEST_TIMEOUT_SECONDS = 60.0
LOCAL_HOSTS = {"127.0.0.1:8080", "localhost:8080"}
STATIC_DIR = Path(__file__).resolve().parent / "static"


def load_config() -> tuple[str, str]:
    """Require an explicit HTTPS origin and header-safe token, without echoing either."""
    origin = os.environ.get("FEEDBACKPULSE_API_URL", "")
    invalid_origin = (
        "FEEDBACKPULSE_API_URL must be an HTTPS origin (port 443) "
        "without credentials, path, query or fragment."
    )
    try:
        parsed = urlsplit(origin)
        valid = (
            origin.startswith("https://")
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
            and parsed.port in (None, 443)
            and parsed.path in ("", "/")
            and not parsed.query
            and not parsed.fragment
            and not any(char.isspace() or ord(char) < 33 for char in origin)
            and "?" not in origin
            and "#" not in origin
            and "\\" not in origin
        )
    except ValueError:
        raise ValueError(invalid_origin) from None
    if not valid:
        raise ValueError(invalid_origin)

    token = os.environ.get("SERVICE_TOKEN", "")
    if not token or any(not 33 <= ord(char) <= 126 for char in token):
        raise ValueError(
            "SERVICE_TOKEN must be non-empty printable ASCII without spaces."
        )
    return origin.rstrip("/"), token


def error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "message": message}},
        status_code=status,
        headers={"Cache-Control": "no-store"},
    )


def create_app(*, transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    """The optional transport is used by offline tests, not by browser requests."""
    origin, token = load_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with httpx.AsyncClient(
            base_url=origin,
            timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS, connect=10.0),
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        ) as client:
            app.state.upstream = client
            yield

    app = FastAPI(
        title="FeedbackPulse local relay",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        redirect_slashes=False,
    )

    @app.middleware("http")
    async def local_requests_only(request: Request, call_next):
        # Host blocks DNS rebinding; Origin blocks another website using our token.
        host = request.headers.get("host", "")
        request_origin = request.headers.get("origin")
        if (
            host not in LOCAL_HOSTS
            or request_origin not in (None, f"http://{host}")
            or request.headers.get("sec-fetch-site") == "cross-site"
        ):
            return error(403, "LOCAL_ONLY", "Use the demo on localhost:8080.")
        if request.url.query:
            return error(400, "INVALID_REQUEST", "Query parameters are not supported.")
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; base-uri 'none'; form-action 'none'; "
            "frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    async def forward(method: str, path: str, payload: dict | None = None):
        # Only the two fixed route handlers below choose method/path. Never forward
        # browser headers, cookies, query strings or a caller-supplied destination.
        headers = {"Authorization": f"Bearer {token}"} if path == "/predict" else {}
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                upstream = await app.state.upstream.request(
                    method, path, json=payload, headers=headers
                )
        except (TimeoutError, httpx.TimeoutException):
            logger.warning("Azure request timed out")
            return error(
                504,
                "UPSTREAM_TIMEOUT",
                "The Azure API took too long to respond. Try again later.",
            )
        except httpx.RequestError as exc:
            logger.warning("Azure request failed (%s)", type(exc).__name__)
            return error(502, "UPSTREAM_UNREACHABLE", "Could not reach the Azure API.")

        # Do not return raw upstream errors/headers: gateways may send HTML,
        # diagnostic details or redirects instead of the API's error envelope.
        if upstream.status_code == 401:
            return error(
                401,
                "UNAUTHORIZED",
                "The Azure API rejected the configured service token.",
            )
        if upstream.status_code == 503:
            return error(
                503,
                "UPSTREAM_UNAVAILABLE",
                "The Azure API is not ready. Try again later.",
            )
        if upstream.status_code == 429:
            return error(
                429, "UPSTREAM_BUSY", "The Azure API is busy. Try again later."
            )
        if upstream.status_code in (400, 422):
            try:
                body = upstream.json()
                details = body.get("error") if isinstance(body, dict) else None
                code = details.get("code") if isinstance(details, dict) else None
            except ValueError:
                code = None
            if upstream.status_code == 422 and code == "TEXT_TOO_LONG":
                return error(
                    422, "TEXT_TOO_LONG", "The text exceeds the API's 510-token limit."
                )
            return error(
                upstream.status_code,
                "INVALID_TEXT",
                "The Azure API rejected this input.",
            )
        if upstream.status_code != 200:
            return error(
                502, "UPSTREAM_ERROR", "The Azure API returned an unexpected response."
            )

        try:
            body = upstream.json()
        except ValueError:
            body = None
        valid = isinstance(body, dict)
        if valid:
            version = body.get("model_version")
            valid = (
                isinstance(version, str)
                and bool(version.strip())
                and token not in version
            )
        if valid and path == "/predict":
            score = body.get("score")
            valid = (
                body.get("sentiment") in ("negative", "neutral", "positive")
                and type(score) in (int, float)
                and 0 <= score <= 1
            )
            fields = ("sentiment", "score", "model_version")
        else:
            valid = valid and body.get("status") == "ready"
            fields = ("status", "model_version")
        if not valid:
            return error(
                502,
                "INVALID_UPSTREAM_RESPONSE",
                "The Azure API returned an invalid result.",
            )
        try:
            return JSONResponse(
                {key: body[key] for key in fields},
                headers={"Cache-Control": "no-store"},
            )
        except UnicodeEncodeError:
            return error(
                502,
                "INVALID_UPSTREAM_RESPONSE",
                "The Azure API returned an invalid result.",
            )

    @app.get("/api/ready")
    async def ready():
        return await forward("GET", "/ready")

    @app.post("/api/predict")
    async def predict(request: Request):
        if (
            request.headers.get("content-type", "").split(";")[0].strip().lower()
            != "application/json"
        ):
            return error(415, "JSON_REQUIRED", "Send application/json.")
        try:
            body = await request.json()
        except (ValueError, UnicodeDecodeError):
            return error(400, "BAD_REQUEST", "The request body must be valid JSON.")
        if (
            not isinstance(body, dict)
            or set(body) != {"text"}
            or not isinstance(body["text"], str)
            or not body["text"].strip()
        ):
            return error(422, "INVALID_TEXT", "Provide only a non-empty text string.")
        try:
            body["text"].encode("utf-8")
        except UnicodeEncodeError:
            return error(422, "INVALID_TEXT", "The text must contain valid Unicode.")
        return await forward("POST", "/predict", {"text": body["text"]})

    @app.get("/")
    async def index():
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


def main():
    uvicorn.run(
        create_app(),
        host="127.0.0.1",
        port=8080,
        access_log=False,
        proxy_headers=False,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
