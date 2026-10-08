"""Unit tests for configuration loader."""

from feedbackpulse.config import DEFAULT_MODEL_VERSION, load_settings


def test_load_settings_defaults():
    settings = load_settings(environ={})
    assert settings.service_token == "test-service-token"
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
