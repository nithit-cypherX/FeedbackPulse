"""FeedbackPulse HTTP Service.

Implements the contract agreed in docs/plans/P01-T02-api-contract.md:
- POST /predict: classifies short English feedback (requires Bearer token)
- GET /health: liveness probe (200 if server process is running)
- GET /ready: readiness probe (200 if model is loaded and ready, 503 otherwise)
"""

import json
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from feedbackpulse.config import Settings, load_settings
from feedbackpulse.inference import (
    InvalidText,
    SentimentClassifier,
    TextTooLong,
)

logger = logging.getLogger("feedbackpulse.api")


class AppState:
    """Holds runtime dependencies and application state."""

    def __init__(
        self,
        settings: Settings,
        classifier: SentimentClassifier | None = None,
        load_error: str | None = None,
    ) -> None:
        self.settings = settings
        self.classifier = classifier
        self.load_error = load_error

    @property
    def is_ready(self) -> bool:
        return self.classifier is not None


def create_error_response(
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Standardized error envelope matching P01-T02 section 4."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
        headers=headers,
    )


def create_app(
    settings: Settings | None = None,
    classifier: SentimentClassifier | None = None,
) -> FastAPI:
    """Application factory with lifespan management."""
    if settings is None:
        settings = load_settings()

    state = AppState(settings=settings, classifier=classifier)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup: attempt to load model if not pre-injected
        if state.classifier is None:
            try:
                logger.info(
                    "Loading model from %s (version: %s)",
                    state.settings.model_dir,
                    state.settings.model_version,
                )
                state.classifier = SentimentClassifier.load(
                    state.settings.model_dir,
                    state.settings.model_version,
                )
                logger.info("Model loaded successfully")
            except Exception as exc:  # noqa: BLE001
                # Do not raise: server must start so /health works and /ready fails with 503
                logger.error("Failed to load model: %s", exc)
                state.load_error = str(exc)
        yield
        # Teardown
        state.classifier = None

    app = FastAPI(
        title="FeedbackPulse",
        version="0.1.0",
        description="Sentiment classification API for customer feedback",
        lifespan=lifespan,
    )
    app.state.app_state = state

    # Request logging middleware that protects privacy and credentials
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        start_time = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start_time) * 1000.0

        # Log path, status, and duration without logging headers or body content
        logger.info(
            "%s %s -> %s (%.2f ms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return create_error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "INVALID_TEXT",
            "The submitted data does not satisfy the input requirements.",
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        headers = getattr(exc, "headers", None)
        return create_error_response(
            exc.status_code,
            "HTTP_ERROR",
            exc.detail if isinstance(exc.detail, str) else "HTTP error",
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unexpected error handling %s", request.url.path)
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "An unexpected error occurred. Please try again later.",
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Liveness probe: verifies the service process is alive."""
        return {"status": "healthy"}

    @app.get("/ready")
    async def ready() -> Response:
        """Readiness probe: verifies the model is loaded and ready."""
        classifier = state.classifier
        if classifier is None:
            return create_error_response(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "MODEL_NOT_READY",
                "The model is not ready. Please try again later.",
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
                "model_version": classifier.model_version,
            },
        )

    @app.post("/predict")
    async def predict(request: Request) -> Response:
        """Classify single feedback text into negative, neutral, or positive."""
        # 1. Access control: Validate Bearer token
        auth_header = request.headers.get("Authorization")
        expected_token = state.settings.service_token
        expected_auth = f"Bearer {expected_token}"

        if not auth_header or auth_header != expected_auth:
            return create_error_response(
                status.HTTP_401_UNAUTHORIZED,
                "UNAUTHORIZED",
                "Missing or invalid service token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 2. Check model readiness
        classifier = state.classifier
        if classifier is None:
            return create_error_response(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "MODEL_NOT_READY",
                "The model is not ready. Please try again later.",
            )

        # 3. Parse JSON body
        try:
            body = await request.json()
        except (json.JSONDecodeError, ValueError):
            return create_error_response(
                status.HTTP_400_BAD_REQUEST,
                "BAD_REQUEST",
                "Request body must be valid JSON.",
            )

        if not isinstance(body, dict):
            return create_error_response(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "INVALID_TEXT",
                "Request body must be a JSON object.",
            )

        # 4. Validate 'text' field
        if "text" not in body:
            return create_error_response(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "INVALID_TEXT",
                "Missing required field 'text'.",
            )

        raw_text = body["text"]
        if not isinstance(raw_text, str) or not raw_text.strip():
            return create_error_response(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "INVALID_TEXT",
                "text must be a non-empty string.",
            )

        # 5. Classify text using shared inference module
        try:
            result = classifier.predict(raw_text)
        except TextTooLong as exc:
            return create_error_response(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "TEXT_TOO_LONG",
                str(exc),
            )
        except InvalidText as exc:
            return create_error_response(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "INVALID_TEXT",
                str(exc),
            )
        except Exception:
            logger.exception("Inference failed")
            return create_error_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "INTERNAL_ERROR",
                "An error occurred during prediction.",
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "sentiment": result.sentiment,
                "score": round(result.score, 4),
                "model_version": result.model_version,
            },
        )

    return app


# Module-level default application instance for uvicorn
app = create_app()
