"""Startup must bind the public version to registered model bytes, without downloads."""

import asyncio
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from feedbackpulse import config, model_files, registry
from feedbackpulse.config import Settings
from feedbackpulse.inference import Prediction, SentimentClassifier


@pytest.fixture
def registered_model(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    artifact = tmp_path / "artifacts" / "sentiment-test"
    model_dir = artifact / "model"
    model_dir.mkdir(parents=True)
    contents = {
        "model/config.json": b'{"model_type": "roberta"}',
        "model/model.safetensors": b"small test weights, not a real model",
        "upstream-model-card.md": b"test model card",
    }
    for name, content in contents.items():
        (artifact / name).write_bytes(content)
    lineage = {
        "artifact": {
            "artifact_id": "sentiment-test",
            "loadable_dir": "model",
            "manifest_sha256": "historical packaging metadata",
            "files_sha256": {
                name: hashlib.sha256(content).hexdigest()
                for name, content in contents.items()
            },
        }
    }
    version = registry.model_version_for("sentiment-test", lineage)
    entry = tmp_path / "reports" / "registry" / f"{version}.json"
    entry.parent.mkdir(parents=True)
    entry.write_text(json.dumps({"model_version": version, "lineage": lineage}))
    # A fresh package timestamp is not a change to the registered model bytes.
    (artifact / "manifest.json").write_text('{"created_utc": "a later build"}')
    return model_dir, version, entry


FAILURES = [
    "unregistered-version",
    "invalid-json",
    "wrong-entry-version",
    "changed-lineage",
    "missing-weights",
    "changed-weights",
    "changed-config",
    "missing-model-card",
    "extra-tokenizer-config",
    "wrong-model-dir",
]


def break_binding(model_dir, entry, failure):
    if failure == "unregistered-version":
        entry.unlink()
    elif failure == "invalid-json":
        entry.write_text("not json")
    elif failure in {"wrong-entry-version", "changed-lineage"}:
        data = json.loads(entry.read_text())
        if failure == "wrong-entry-version":
            data["model_version"] = "sentiment-something-else"
        else:
            data["lineage"]["artifact"]["artifact_id"] = "sentiment-something-else"
        entry.write_text(json.dumps(data))
    elif failure == "missing-weights":
        (model_dir / "model.safetensors").unlink()
    elif failure == "changed-weights":
        (model_dir / "model.safetensors").write_bytes(b"different weights")
    elif failure == "changed-config":
        (model_dir / "config.json").write_text('{"id2label": {"0": "changed"}}')
    elif failure == "missing-model-card":
        (model_dir.parent / "upstream-model-card.md").unlink()
    elif failure == "extra-tokenizer-config":
        (model_dir / "tokenizer_config.json").write_text("{}")
    elif failure == "wrong-model-dir":
        model_dir = model_dir.parent
    return model_dir


def test_matching_model_returns_the_registered_version(registered_model):
    model_dir, version, _ = registered_model
    assert registry.verify_model(version, model_dir) == version


@pytest.mark.parametrize("failure", FAILURES)
def test_registry_rejects_a_broken_binding(registered_model, failure):
    model_dir, version, entry = registered_model
    model_dir = break_binding(model_dir, entry, failure)
    with pytest.raises((registry.CannotRegister, ValueError)):
        registry.verify_model(version, model_dir)


def test_registry_version_cannot_select_a_file_outside_registry(registered_model):
    model_dir, version, entry = registered_model
    outside = entry.parent.parent / entry.name
    outside.write_bytes(entry.read_bytes())
    with pytest.raises(registry.CannotRegister):
        registry.verify_model(f"../{version}", model_dir)


async def request(
    app, path, method="GET", token=None, body=b'{"text":"Great service"}'
):
    """Exercise the real ASGI routes without a socket or an HTTP client dependency."""
    headers = [(b"content-type", b"application/json")]
    if token:
        headers.append((b"authorization", f"Bearer {token}".encode()))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 1),
        "server": ("test.local", 80),
    }
    sent_body = False
    messages = []

    async def receive():
        nonlocal sent_body
        if not sent_body:
            sent_body = True
            return {
                "type": "http.request",
                "body": body,
                "more_body": False,
            }
        await asyncio.Event().wait()

    async def send(message):
        messages.append(message)

    await asyncio.wait_for(app(scope, receive, send), timeout=5)
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in messages)
    return status, json.loads(body)


@pytest.mark.parametrize("failure", [None, *FAILURES])
def test_startup_only_serves_a_verified_model(registered_model, monkeypatch, failure):
    model_dir, version, entry = registered_model
    if failure:
        model_dir = break_binding(model_dir, entry, failure)
    # api.py also constructs a default app on import; never trigger model download.
    monkeypatch.setenv("MODEL_DIR", str(model_dir))
    from feedbackpulse import api

    verifier = Mock(wraps=api.verify_model)
    monkeypatch.setattr(api, "verify_model", verifier)
    classifier = Mock(model_version=version)
    classifier.predict.return_value = Prediction("positive", 0.9, version)
    loader = Mock(return_value=classifier)
    monkeypatch.setattr(SentimentClassifier, "load", loader)
    app = api.create_app(Settings("test-binding-token", model_dir, version))

    async def check():
        async with app.router.lifespan_context(app):
            assert await request(app, "/health") == (200, {"status": "healthy"})
            ready_status, ready = await request(app, "/ready")
            predict_status, prediction = await request(
                app, "/predict", "POST", "test-binding-token"
            )
            verifier.assert_called_once_with(version, model_dir)
            if failure:
                loader.assert_not_called()
                classifier.predict.assert_not_called()
                assert ready_status == predict_status == 503
                assert ready["error"]["code"] == "MODEL_NOT_READY"
                assert prediction["error"]["code"] == "MODEL_NOT_READY"
                assert app.state.app_state.load_error
            else:
                loader.assert_called_once_with(model_dir, version)
                assert ready_status == predict_status == 200
                assert ready["model_version"] == prediction["model_version"] == version
                assert app.state.app_state.load_error is None
        assert app.state.app_state.classifier is None

    asyncio.run(check())


@pytest.mark.parametrize("explicit_model_dir", [False, True])
def test_missing_model_starts_without_downloading(
    registered_model, monkeypatch, explicit_model_dir
):
    model_dir, version, _ = registered_model
    model_dir.rename(model_dir.with_name("model-moved"))
    monkeypatch.setattr(config, "DEFAULT_ARTIFACT_DIR", model_dir)
    monkeypatch.setenv("SERVICE_TOKEN", "test-startup-token")
    monkeypatch.setenv("MODEL_VERSION", version)
    if explicit_model_dir:
        monkeypatch.setenv("MODEL_DIR", str(model_dir))
    else:
        monkeypatch.delenv("MODEL_DIR", raising=False)
    downloader = Mock(side_effect=AssertionError("API startup must not download"))
    loader = Mock(side_effect=AssertionError("Missing files must not reach loader"))
    monkeypatch.setattr(model_files, "ensure_model_files", downloader)
    monkeypatch.setattr(SentimentClassifier, "load", loader)
    from feedbackpulse.api import create_app

    app = create_app()
    assert app.state.app_state.settings.model_dir == model_dir

    async def check():
        async with app.router.lifespan_context(app):
            assert await request(app, "/health") == (200, {"status": "healthy"})
            for path, method, token in [
                ("/ready", "GET", None),
                ("/predict", "POST", "test-startup-token"),
            ]:
                code, body = await request(app, path, method, token)
                assert code == 503
                assert body["error"]["code"] == "MODEL_NOT_READY"
            code, body = await request(app, "/predict", "POST")
            assert code == 401
            assert body["error"]["code"] == "UNAUTHORIZED"
            assert app.state.app_state.load_error

    asyncio.run(check())
    downloader.assert_not_called()
    loader.assert_not_called()


def test_default_app_import_needs_no_model_or_download(tmp_path):
    """Use a fresh process so a previously imported API cannot hide this regression."""
    env = os.environ.copy()
    env.pop("MODEL_DIR", None)
    env["SERVICE_TOKEN"] = "test-import-token"
    env["MODEL_VERSION"] = config.DEFAULT_MODEL_VERSION
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            """
from unittest.mock import Mock
from feedbackpulse import config, model_files
downloader = Mock(side_effect=AssertionError('Import must not download a model'))
model_files.ensure_model_files = downloader
from feedbackpulse.api import app
assert app.state.app_state.settings.model_dir == config.DEFAULT_ARTIFACT_DIR
assert app.state.app_state.classifier is None
downloader.assert_not_called()
""",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
