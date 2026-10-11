"""Error logs must not retain feedback or credentials, including traceback text."""

import asyncio
import json
import logging
from pathlib import Path
from unittest.mock import Mock

import pytest
from test_model_binding import request

from feedbackpulse import api
from feedbackpulse.config import Settings
from feedbackpulse.inference import Prediction, SentimentClassifier

TOKEN = "logging-test-only-token"
FEEDBACK = "Private feedback from customer@example.com"


def assert_private_error_is_hidden(caplog, body, expected_event):
    # getMessage() alone misses the traceback and chained exception messages.
    rendered = "\n".join(logging.Formatter().format(r) for r in caplog.records)
    for output in (rendered, json.dumps(body)):
        assert TOKEN not in output
        assert FEEDBACK not in output
        assert "Traceback" not in output
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errors) == 1, "Keep one useful error event rather than silencing logs"
    assert expected_event in errors[0].getMessage()
    assert "RuntimeError" in errors[0].getMessage()
    assert errors[0].exc_info is None
    assert errors[0].exc_text is None


@pytest.mark.parametrize("stage", ["inference", "chained-inference", "response"])
def test_request_errors_do_not_leak_into_logs_or_escape_to_server(caplog, stage):
    caplog.set_level(logging.INFO)
    settings = Settings(TOKEN, Path("unused-model"), "logging-test-version")

    def fail(text):
        private_message = f"feedback={text}; token={TOKEN}"
        if stage == "chained-inference":
            try:
                raise ValueError(private_message)
            except ValueError as cause:
                error = RuntimeError("Prediction failed")
                error.add_note(private_message)
                raise error from cause
        raise RuntimeError(private_message)

    class BrokenScore:
        def __round__(self, _digits):
            fail(FEEDBACK)

    classifier = Mock(model_version=settings.model_version)
    if stage == "response":
        # Fail after predict(), when the response is built outside its try block.
        classifier.predict.return_value = Prediction(
            "positive", BrokenScore(), settings.model_version
        )
    else:
        classifier.predict.side_effect = fail
    app = api.create_app(settings, classifier)

    async def check():
        # This must return normally. An escaping exception would be logged by
        # the ASGI server with exc_info even if the API had already sent a 500.
        status, body = await request(
            app, "/predict", "POST", TOKEN, json.dumps({"text": FEEDBACK}).encode()
        )
        assert status == 500
        assert body == {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again later."
                if stage == "response"
                else "An error occurred during prediction.",
            }
        }
        expected_event = (
            "Unexpected error" if stage == "response" else "Inference failed"
        )
        assert_private_error_is_hidden(caplog, body, expected_event)
        assert any("POST /predict -> 500" in r.getMessage() for r in caplog.records)
        assert await request(app, "/health") == (200, {"status": "healthy"})

    asyncio.run(check())
    classifier.predict.assert_called_once_with(FEEDBACK)


def test_model_load_error_logs_only_safe_diagnostics(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    settings = Settings(TOKEN, Path("unused-model"), "logging-test-version")
    monkeypatch.setattr(api, "verify_model", Mock(return_value=settings.model_version))
    monkeypatch.setattr(
        SentimentClassifier,
        "load",
        Mock(side_effect=RuntimeError(f"{FEEDBACK}; token={TOKEN}")),
    )
    app = api.create_app(settings)

    async def check():
        async with app.router.lifespan_context(app):
            assert await request(app, "/health") == (200, {"status": "healthy"})
            status, body = await request(app, "/ready")
            assert status == 503
            assert body["error"]["code"] == "MODEL_NOT_READY"
            assert_private_error_is_hidden(caplog, body, "Failed to load model")

    asyncio.run(check())
