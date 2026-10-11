"""Unit tests for configuration loader."""

from unittest.mock import Mock

import pytest

from feedbackpulse import config, model_files
from feedbackpulse.config import DEFAULT_MODEL_VERSION, load_settings


def test_load_settings_defaults_require_an_explicit_token(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "get_default_model_dir", lambda: tmp_path / "model")
    settings = load_settings(environ={"SERVICE_TOKEN": "unit-test-token"})
    assert settings.service_token == "unit-test-token"
    assert settings.model_dir == tmp_path / "model"
    assert settings.model_version == DEFAULT_MODEL_VERSION
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000


def test_load_settings_from_custom_env(tmp_path):
    custom_env = {
        "SERVICE_TOKEN": "my-secret-token",
        "MODEL_DIR": str(tmp_path / "model"),
        "MODEL_VERSION": "sentiment-custom-12345",
        "HOST": "127.0.0.1",
        "PORT": "9000",
    }
    settings = load_settings(environ=custom_env)
    assert settings.service_token == "my-secret-token"
    assert settings.model_dir == tmp_path / "model"
    assert settings.model_version == "sentiment-custom-12345"
    assert settings.host == "127.0.0.1"
    assert settings.port == 9000


@pytest.mark.parametrize("model_exists", [False, True])
def test_default_model_path_never_downloads(tmp_path, monkeypatch, model_exists):
    model_dir = tmp_path / "packaged" / "model"
    if model_exists:
        model_dir.mkdir(parents=True)
    monkeypatch.setattr(config, "DEFAULT_ARTIFACT_DIR", model_dir)
    downloader = Mock(side_effect=AssertionError("Config must not download a model"))
    monkeypatch.setattr(model_files, "ensure_model_files", downloader)

    settings = load_settings(environ={"SERVICE_TOKEN": "unit-test-token"})

    assert settings.model_dir == model_dir
    assert model_dir.exists() == model_exists
    downloader.assert_not_called()


@pytest.mark.parametrize(
    "environ",
    [{}, {"SERVICE_TOKEN": ""}, {"SERVICE_TOKEN": "   "}, {"SERVICE_TOKEN": "\n\t"}],
    ids=["missing", "empty", "spaces", "other-whitespace"],
)
def test_load_settings_rejects_missing_or_blank_token_before_model_lookup(
    environ, monkeypatch
):
    def unexpected_model_lookup():
        pytest.fail("Invalid token configuration must fail before model lookup")

    monkeypatch.setattr(config, "get_default_model_dir", unexpected_model_lookup)
    with pytest.raises(ValueError, match="SERVICE_TOKEN must be set"):
        load_settings(environ=environ)


def test_load_settings_reads_explicit_token_from_process_environment(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("SERVICE_TOKEN", "process-test-token")
    monkeypatch.setenv("MODEL_DIR", str(tmp_path / "model"))
    assert load_settings().service_token == "process-test-token"


def test_load_settings_does_not_fall_back_when_process_token_is_missing(monkeypatch):
    monkeypatch.delenv("SERVICE_TOKEN", raising=False)
    monkeypatch.setenv("MODEL_DIR", "unused-model-path")
    with pytest.raises(ValueError, match="SERVICE_TOKEN must be set"):
        load_settings()
