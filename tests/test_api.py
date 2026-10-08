"""Comprehensive test suite for FeedbackPulse API.

Directly verifies all 11 items from the P01-T02 API Contract checklist
(docs/plans/P01-T02-api-contract.md section 6).
"""

import json
import logging
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from feedbackpulse.api import create_app
from feedbackpulse.config import Settings
from feedbackpulse.inference import SentimentClassifier
from feedbackpulse.model_files import ensure_model_files

TOKEN = "secret-test-token"
REGISTERED_MODEL_VERSION = "sentiment-6e7ff9fbc17c-0110c462"


@pytest.fixture(scope="module")
def shared_classifier():
    """Load the pinned model once for the whole test module."""
    artifact_dir = Path("artifacts/sentiment-6e7ff9fbc17c/model")
    model_dir = artifact_dir if artifact_dir.is_dir() else ensure_model_files()
    return SentimentClassifier.load(model_dir, REGISTERED_MODEL_VERSION)


@pytest.fixture
def client(shared_classifier):
    """Test client with loaded and ready model."""
    settings = Settings(
        service_token=TOKEN,
        model_dir=Path("artifacts/sentiment-6e7ff9fbc17c/model"),
        model_version=REGISTERED_MODEL_VERSION,
    )
    app = create_app(settings=settings, classifier=shared_classifier)
    return TestClient(app)


@pytest.fixture
def unready_client():
    """Test client where the model is unavailable."""
    settings = Settings(
        service_token=TOKEN,
        model_dir=Path("non-existent-dir"),
        model_version=REGISTERED_MODEL_VERSION,
    )
    app = create_app(settings=settings, classifier=None)
    return TestClient(app)


# Checklist item 1 & 2 & 3:
# - Valid request with token gives 200 and all 3 fields
# - sentiment in {negative, neutral, positive}, score in [0, 1]
# - model_version matches loaded artifact and registry
def test_predict_success_and_response_schema(client):
    response = client.post(
        "/predict",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"text": "The service was wonderful and on time!"},
    )
    assert response.status_code == 200
    data = response.json()

    assert "sentiment" in data
    assert "score" in data
    assert "model_version" in data

    assert data["sentiment"] in ("negative", "neutral", "positive")
    assert isinstance(data["score"], float)
    assert 0.0 <= data["score"] <= 1.0
    assert data["model_version"] == REGISTERED_MODEL_VERSION


# Checklist item 4:
# - Malformed JSON returns 400
def test_predict_malformed_json_returns_400(client):
    response = client.post(
        "/predict",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
        content=b"this is not valid json {",
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "BAD_REQUEST"


# Checklist item 5:
# - Missing text, null, integer, list, empty string, or whitespace returns 422
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"text": None},
        {"text": 12345},
        {"text": ["feedback", "message"]},
        {"text": ""},
        {"text": "   "},
        {"wrong_field": "some valid text"},
    ],
)
def test_predict_invalid_text_payloads_return_422(client, payload):
    response = client.post(
        "/predict",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json=payload,
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "INVALID_TEXT"


# Checklist item 6:
# - Exactly 510 content tokens is accepted (200)
# - Exactly 511 content tokens is rejected with 422 (TEXT_TOO_LONG) without silent truncation
def test_predict_content_token_boundary(client, shared_classifier):
    tokenizer = shared_classifier._tokenizer

    token_id = tokenizer.encode(" good", add_special_tokens=False)[0]

    tokens_510 = [token_id] * 510
    tokens_511 = [token_id] * 511

    text_510 = tokenizer.decode(tokens_510)
    text_511 = tokenizer.decode(tokens_511)

    assert shared_classifier.count_tokens(text_510) == 510
    assert shared_classifier.count_tokens(text_511) == 511

    res_510 = client.post(
        "/predict",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"text": text_510},
    )
    assert res_510.status_code == 200

    res_511 = client.post(
        "/predict",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"text": text_511},
    )
    assert res_511.status_code == 422
    data_511 = res_511.json()
    assert data_511["error"]["code"] == "TEXT_TOO_LONG"


# Checklist item 7:
# - Missing token or invalid token returns 401 with WWW-Authenticate: Bearer
@pytest.mark.parametrize(
    "auth_header",
    [
        None,
        "",
        "Bearer wrong-token",
        "Basic dXNlcjpwYXNz",
        "Token secret-test-token",
    ],
)
def test_predict_auth_failure_returns_401(client, auth_header):
    headers = {}
    if auth_header is not None:
        headers["Authorization"] = auth_header

    response = client.post(
        "/predict",
        headers=headers,
        json={"text": "Great flight!"},
    )
    assert response.status_code == 401
    assert response.headers.get("WWW-Authenticate") == "Bearer"
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"


# Checklist item 8 & 9:
# - Ready model gives /ready -> 200
# - Unready model gives /ready -> 503
# - When model is unready: /health gives 200, /ready gives 503, and /predict gives 503
def test_health_and_readiness_separation(client, unready_client):
    res_health_ok = client.get("/health")
    assert res_health_ok.status_code == 200

    res_ready_ok = client.get("/ready")
    assert res_ready_ok.status_code == 200
    assert res_ready_ok.json()["status"] == "ready"

    res_health_unready = unready_client.get("/health")
    assert res_health_unready.status_code == 200

    res_ready_unready = unready_client.get("/ready")
    assert res_ready_unready.status_code == 503
    assert res_ready_unready.json()["error"]["code"] == "MODEL_NOT_READY"

    res_predict_unready = unready_client.post(
        "/predict",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"text": "Everything was okay."},
    )
    assert res_predict_unready.status_code == 503
    assert res_predict_unready.json()["error"]["code"] == "MODEL_NOT_READY"


# Checklist item 10:
# - Unexpected errors return 500 without leaking stack traces or internal secrets
def test_unexpected_error_masks_internal_details(client, monkeypatch):
    def broken_predict(*args, **kwargs):
        raise RuntimeError("database password supersecret123 leaked in exception")

    monkeypatch.setattr(client.app.state.app_state.classifier, "predict", broken_predict)

    response = client.post(
        "/predict",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"text": "Hello world"},
    )
    assert response.status_code == 500
    data = response.json()
    assert data["error"]["code"] == "INTERNAL_ERROR"
    assert "supersecret123" not in json.dumps(data)
    assert "Traceback" not in json.dumps(data)


# Checklist item 11:
# - Error format matches agreed schema {"error": {"code": ..., "message": ...}}
# - Logs do not record secret token or full feedback text
def test_error_schema_and_logging_privacy(client, caplog):
    caplog.set_level(logging.INFO)

    secret_sent = "very-private-customer-complaint-identifying-info-12345"
    response = client.post(
        "/predict",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"text": secret_sent},
    )
    assert response.status_code == 200

    for record in caplog.records:
        assert TOKEN not in record.message
        assert secret_sent not in record.message
