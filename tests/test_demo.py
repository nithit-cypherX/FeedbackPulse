"""Offline relay tests. All outbound requests use a mock transport, never Azure."""

import asyncio
import json
import logging
import subprocess
import sys
from html.parser import HTMLParser
from unittest.mock import Mock

import httpx
import pytest
from starlette.testclient import TestClient

from demo import server

ORIGIN = "https://feedbackpulse.example.test"
TOKEN = "relay-test-only-token"
TEXT = "Private feedback from customer@example.test"
PREDICTION = {"sentiment": "positive", "score": 0.91, "model_version": "test-model-v1"}


@pytest.fixture(autouse=True)
def configuration(monkeypatch):
    monkeypatch.setenv("FEEDBACKPULSE_API_URL", ORIGIN)
    monkeypatch.setenv("SERVICE_TOKEN", TOKEN)


@pytest.fixture
def relay():
    clients = []

    def open_client(handler):
        client = TestClient(
            server.create_app(transport=httpx.MockTransport(handler)),
            base_url="http://127.0.0.1:8080",
        )
        client.__enter__()
        clients.append(client)
        return client

    yield open_client
    for client in reversed(clients):
        client.__exit__(None, None, None)


@pytest.mark.parametrize(
    "origin",
    [
        None,
        "",
        "http://example.test",
        "https://",
        "https://user:secret@example.test",
        "https://example.test/predict",
        "https://example.test?token=secret",
        "https://example.test#secret",
        "https://example.test?",
        "https://example.test:8080",
        "https://example.test:bad",
        "https://[bad",
        " https://example.test",
        "https://example.test\n",
        "https://example.test\\evil",
    ],
)
def test_invalid_origin_fails_without_printing_configuration(monkeypatch, origin):
    if origin is None:
        monkeypatch.delenv("FEEDBACKPULSE_API_URL")
    else:
        monkeypatch.setenv("FEEDBACKPULSE_API_URL", origin)
    with pytest.raises(ValueError, match="FEEDBACKPULSE_API_URL must") as exc:
        server.create_app()
    assert TOKEN not in str(exc.value)
    assert "secret" not in str(exc.value)


@pytest.mark.parametrize(
    "token", [None, "", " ", "two words", "token\r\nheader", "non-ascii-ไทย"]
)
def test_invalid_token_fails_before_startup(monkeypatch, token):
    if token is None:
        monkeypatch.delenv("SERVICE_TOKEN")
    else:
        monkeypatch.setenv("SERVICE_TOKEN", token)
    with pytest.raises(ValueError, match="SERVICE_TOKEN must"):
        server.create_app()


def test_predict_forwards_only_text_and_server_token(relay, monkeypatch):
    monkeypatch.setenv("FEEDBACKPULSE_API_URL", ORIGIN + "/")
    calls = []

    def upstream(request):
        calls.append(request)
        assert str(request.url) == ORIGIN + "/predict"
        assert request.method == "POST"
        assert request.headers["authorization"] == f"Bearer {TOKEN}"
        assert "cookie" not in request.headers
        assert "x-extra" not in request.headers
        assert json.loads(request.content) == {"text": TEXT}
        return httpx.Response(
            200, json={**PREDICTION, "debug": TOKEN}, headers={"Set-Cookie": TOKEN}
        )

    response = relay(upstream).post(
        "/api/predict",
        json={"text": TEXT},
        headers={
            "Authorization": "Bearer browser-value",
            "Cookie": "browser-cookie",
            "X-Extra": "not-forwarded",
            "Origin": "http://127.0.0.1:8080",
        },
    )
    assert response.status_code == 200
    assert response.json() == PREDICTION
    assert response.headers["cache-control"] == "no-store"
    assert "set-cookie" not in response.headers
    assert TOKEN not in response.text
    assert len(calls) == 1


def test_ready_reads_real_upstream_status_without_sending_token(relay):
    def upstream(request):
        assert request.method == "GET"
        assert str(request.url) == ORIGIN + "/ready"
        assert "authorization" not in request.headers
        assert not request.content
        return httpx.Response(
            200, json={"status": "ready", "model_version": "test-model-v1"}
        )

    response = relay(upstream).get("/api/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "model_version": "test-model-v1"}


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"text": None},
        {"text": 123},
        {"text": " "},
        {"text": "ok", "url": "https://attacker.test"},
        {"text": "ok", "headers": {"Authorization": "wrong"}},
    ],
)
def test_invalid_input_never_reaches_upstream(relay, payload):
    upstream = Mock(side_effect=AssertionError("Must not call Azure"))
    response = relay(upstream).post(
        "/api/predict",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_TEXT"
    upstream.assert_not_called()


@pytest.mark.parametrize(
    "content,content_type,status",
    [
        (b"{", "application/json", 400),
        (b"\xff", "application/json", 400),
        (b'{"text":"ok"}', "text/plain", 415),
    ],
)
def test_bad_body_is_handled_without_upstream(relay, content, content_type, status):
    upstream = Mock(side_effect=AssertionError("Must not call Azure"))
    response = relay(upstream).post(
        "/api/predict", content=content, headers={"Content-Type": content_type}
    )
    assert response.status_code == status
    upstream.assert_not_called()


@pytest.mark.parametrize(
    "headers",
    [
        {"Host": "attacker.test:8080"},
        {"Host": "0.0.0.0:8080"},
        {"Origin": "https://attacker.test"},
        {"Origin": "null"},
        {"Origin": "http://127.0.0.1:9999"},
        {"Sec-Fetch-Site": "cross-site"},
    ],
)
def test_untrusted_browser_requests_are_rejected(relay, headers):
    upstream = Mock(side_effect=AssertionError("Must not call Azure"))
    response = relay(upstream).post(
        "/api/predict", json={"text": "ok"}, headers=headers
    )
    assert response.status_code == 403
    assert "access-control-allow-origin" not in response.headers
    upstream.assert_not_called()


@pytest.mark.parametrize(
    "path,method,status",
    [
        ("/api/ready?url=https://attacker.test", "GET", 400),
        ("/api/predict?token=bad", "POST", 400),
        ("/api/proxy", "POST", 404),
        ("/api/predict/", "POST", 404),
        ("/api/ready", "POST", 405),
        ("/api/predict", "GET", 405),
        ("/docs", "GET", 404),
        ("/openapi.json", "GET", 404),
    ],
)
def test_only_fixed_api_routes_exist(relay, path, method, status):
    upstream = Mock(side_effect=AssertionError("Must not call Azure"))
    response = relay(upstream).request(method, path)
    assert response.status_code == status
    upstream.assert_not_called()


@pytest.mark.parametrize(
    "path,content_type,expected",
    [
        ("/", "text/html", "FeedbackPulse"),
        ("/static/styles.css", "text/css", ".workspace"),
        ("/static/app.js", "javascript", "/api/predict"),
    ],
)
def test_frontend_files_are_local_and_do_not_call_upstream(
    relay, path, content_type, expected
):
    upstream = Mock(side_effect=AssertionError("Must not call Azure"))
    response = relay(upstream).get(path)
    assert response.status_code == 200
    assert content_type in response.headers["content-type"]
    assert expected in response.text
    assert TOKEN not in response.text
    assert ORIGIN not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert "connect-src 'self'" in response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"
    upstream.assert_not_called()


def test_monitoring_link_opens_private_azure_dashboard_without_api_credentials(relay):
    class Links(HTMLParser):
        def __init__(self):
            super().__init__()
            self.monitoring = []

        def handle_starttag(self, tag, attrs):
            attributes = dict(attrs)
            if tag == "a" and attributes.get("id") == "open-monitoring":
                self.monitoring.append(attributes)

    upstream = Mock(side_effect=AssertionError("Must not call Azure"))
    response = relay(upstream).get("/")
    parser = Links()
    parser.feed(response.text)
    assert len(parser.monitoring) == 1
    link = parser.monitoring[0]
    assert link["href"] == (
        "https://portal.azure.com/#@student.mahidol.ac.th/dashboard/private/"
        "ad763481-176e-4f6f-a279-f4ebbdec412f"
    )
    assert link["target"] == "_blank"
    assert {"noopener", "noreferrer"} <= set(link["rel"].split())
    assert link["aria-describedby"] == "monitoring-note"
    assert "Open monitoring" in response.text
    assert "Azure sign-in required" in response.text
    assert TOKEN not in response.text
    assert ORIGIN not in response.text
    upstream.assert_not_called()


@pytest.mark.parametrize(
    "path",
    [
        "/cloud.env",
        "/demo/server.py",
        "/static/server.py",
        "/static/%2e%2e/server.py",
        "/static/%2e%2e/%2e%2e/cloud.env",
        "/static/",
    ],
)
def test_static_serving_cannot_expose_repo_files(relay, path):
    upstream = Mock(side_effect=AssertionError("Must not call Azure"))
    response = relay(upstream).get(path)
    assert response.status_code == 404
    assert TOKEN not in response.text
    upstream.assert_not_called()


def test_frontend_still_rejects_other_browser_origins(relay):
    upstream = Mock(side_effect=AssertionError("Must not call Azure"))
    client = relay(upstream)
    for path in ("/", "/static/app.js", "/static/styles.css"):
        assert (
            client.get(path, headers={"Origin": "https://other.test"}).status_code
            == 403
        )
    upstream.assert_not_called()


@pytest.mark.parametrize(
    "status,expected,code",
    [
        (401, 401, "UNAUTHORIZED"),
        (503, 503, "UPSTREAM_UNAVAILABLE"),
        (429, 429, "UPSTREAM_BUSY"),
        (400, 400, "INVALID_TEXT"),
        (422, 422, "INVALID_TEXT"),
        (500, 502, "UPSTREAM_ERROR"),
        (302, 502, "UPSTREAM_ERROR"),
        (307, 502, "UPSTREAM_ERROR"),
    ],
)
def test_upstream_errors_are_safe_and_redirects_not_followed(
    relay, caplog, status, expected, code
):
    calls = []

    def upstream(request):
        calls.append(request)
        return httpx.Response(
            status,
            text=f"<html>{TOKEN} {TEXT}</html>",
            headers={"Location": "https://attacker.test", "Set-Cookie": TOKEN},
        )

    response = relay(upstream).post("/api/predict", json={"text": TEXT})
    assert response.status_code == expected
    assert response.json()["error"]["code"] == code
    assert len(calls) == 1
    assert TOKEN not in response.text + caplog.text
    assert TEXT not in response.text + caplog.text
    assert "location" not in response.headers
    assert "set-cookie" not in response.headers


def test_model_unready_is_not_reported_as_healthy(relay):
    response = relay(
        lambda _: httpx.Response(503, json={"error": {"code": "MODEL_NOT_READY"}})
    ).get("/api/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "UPSTREAM_UNAVAILABLE"


def test_token_limit_is_left_to_azure_not_reimplemented_locally(relay):
    text = "word " * 511

    def upstream(request):
        assert json.loads(request.content) == {"text": text}
        return httpx.Response(
            422, json={"error": {"code": "TEXT_TOO_LONG", "message": TOKEN}}
        )

    response = relay(upstream).post("/api/predict", json={"text": text})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "TEXT_TOO_LONG"
    assert TOKEN not in response.text


@pytest.mark.parametrize(
    "body",
    [
        None,
        [],
        {},
        {**PREDICTION, "score": True},
        {**PREDICTION, "score": "0.91"},
        {**PREDICTION, "score": 2},
        {**PREDICTION, "sentiment": "unknown"},
        {**PREDICTION, "model_version": ""},
        {**PREDICTION, "model_version": TOKEN},
    ],
)
def test_invalid_success_body_never_becomes_a_prediction(relay, body):
    response = relay(lambda _: httpx.Response(200, json=body)).post(
        "/api/predict", json={"text": "ok"}
    )
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "INVALID_UPSTREAM_RESPONSE"
    assert TOKEN not in response.text


def test_html_instead_of_result_is_safe(relay):
    response = relay(lambda _: httpx.Response(200, text=f"<html>{TOKEN}</html>")).post(
        "/api/predict", json={"text": "ok"}
    )
    assert response.status_code == 502
    assert TOKEN not in response.text


@pytest.mark.parametrize(
    "failure,expected,code",
    [
        (httpx.ReadTimeout, 504, "UPSTREAM_TIMEOUT"),
        (httpx.ConnectTimeout, 504, "UPSTREAM_TIMEOUT"),
        (httpx.ConnectError, 502, "UPSTREAM_UNREACHABLE"),
    ],
)
def test_network_failures_do_not_leak_exception_details_or_retry(
    relay, caplog, failure, expected, code
):
    calls = []

    def upstream(request):
        calls.append(request)
        raise failure(f"{TOKEN} {TEXT}", request=request)

    caplog.set_level(logging.WARNING)
    response = relay(upstream).post("/api/predict", json={"text": TEXT})
    assert response.status_code == expected
    assert response.json()["error"]["code"] == code
    assert len(calls) == 1
    assert TOKEN not in response.text + caplog.text
    assert TEXT not in response.text + caplog.text
    assert caplog.records
    assert all(record.exc_info is None for record in caplog.records)


def test_total_timeout_stops_a_stalled_request(relay, monkeypatch):
    monkeypatch.setattr(server, "REQUEST_TIMEOUT_SECONDS", 0.01)
    cancelled = []

    async def upstream(_):
        try:
            await asyncio.sleep(10)
        finally:
            cancelled.append(True)

    response = relay(upstream).get("/api/ready")
    assert response.status_code == 504
    assert cancelled == [True]


def test_entrypoint_binds_loopback_without_access_logs(monkeypatch):
    run = Mock()
    monkeypatch.setattr(server.uvicorn, "run", run)
    server.main()
    assert run.call_args.kwargs == {
        "host": "127.0.0.1",
        "port": 8080,
        "access_log": False,
        "proxy_headers": False,
        "log_level": "warning",
    }


def test_import_does_not_load_model_or_read_runtime_configuration(monkeypatch):
    monkeypatch.delenv("FEEDBACKPULSE_API_URL")
    monkeypatch.delenv("SERVICE_TOKEN")
    check = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            "import sys; import demo.server; assert not any(m.split('.')[0] in {'torch', 'transformers', 'feedbackpulse'} for m in sys.modules)",
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert check.returncode == 0, check.stderr


def test_localhost_origin_is_allowed_and_client_closes(relay):
    client = relay(lambda _: httpx.Response(200, json=PREDICTION))
    response = client.post(
        "/api/predict",
        json={"text": "Good flight"},
        headers={"Host": "localhost:8080", "Origin": "http://localhost:8080"},
    )
    assert response.status_code == 200
    assert client.app.state.upstream.follow_redirects is False
    assert client.app.state.upstream.trust_env is False
    assert client.app.state.upstream.timeout.connect == 10.0
    client.__exit__(None, None, None)
    assert client.app.state.upstream.is_closed


@pytest.mark.parametrize("score", [0, 1, 0.5])
def test_valid_score_boundaries_are_preserved(relay, score):
    prediction = {**PREDICTION, "score": score}
    response = relay(lambda _: httpx.Response(200, json=prediction)).post(
        "/api/predict", json={"text": "ok"}
    )
    assert response.json() == prediction


@pytest.mark.parametrize("score", [float("nan"), float("inf"), -1])
def test_invalid_numeric_score_is_rejected(relay, score):
    body = json.dumps({**PREDICTION, "score": score})
    response = relay(lambda _: httpx.Response(200, content=body)).post(
        "/api/predict", json={"text": "ok"}
    )
    assert response.status_code == 502


@pytest.mark.parametrize(
    "body", [{"status": "healthy", "model_version": "v1"}, {"status": "ready"}, None]
)
def test_invalid_readiness_response_is_not_ready(relay, body):
    response = relay(lambda _: httpx.Response(200, json=body)).get("/api/ready")
    assert response.status_code == 502


def test_unpaired_unicode_surrogate_is_a_safe_input_error(relay):
    upstream = Mock(side_effect=AssertionError("Must not call Azure"))
    response = relay(upstream).post(
        "/api/predict",
        content=b'{"text":"\\ud800"}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    upstream.assert_not_called()


def test_invalid_unicode_in_upstream_result_is_safe(relay):
    response = relay(
        lambda _: httpx.Response(
            200, content=json.dumps({**PREDICTION, "model_version": "bad-\ud800"})
        )
    ).post("/api/predict", json={"text": "ok"})
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "INVALID_UPSTREAM_RESPONSE"
