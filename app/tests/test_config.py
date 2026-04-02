"""
Tests for the central configuration layer (``app/config.py``).

These tests construct ``Settings`` directly with an explicit ``_env_file``
so they are hermetic: they do not depend on the developer's real ``.env``
or ambient environment variables.
"""

import os
import sys

import pytest

# Make ``config`` importable when tests are run from the repo root.
APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from config import (  # noqa: E402
    ConfigurationError,
    Settings,
    feature_disabled_message,
    get_settings,
)
from pydantic import ValidationError  # noqa: E402


REQUIRED = {
    "API_ENDPOINT": "https://example.com/v1/chat/completions",
    "API_KEY": "sk-test-123",
}


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Strip any real config from the host environment so tests are deterministic."""
    for key in (
        "API_ENDPOINT",
        "API_KEY",
        "SLACK_WEBHOOK_URL",
        "NEWS_API_KEY",
        "SUPPORT_EMAIL",
        "SMTP_SERVER",
        "SMTP_PORT",
        "SENDER_EMAIL",
        "SENDER_PASSWORD",
        "ENVIRONMENT",
    ):
        monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def write_env(tmp_path, **values) -> str:
    path = tmp_path / ".env"
    path.write_text("\n".join(f"{k}={v}" for k, v in values.items()))
    return str(path)


# --------------------------------------------------------------------- #
# Happy paths
# --------------------------------------------------------------------- #

def test_loads_minimal_valid_env_file(tmp_path):
    """Only the required LLM settings are needed for local development."""
    env = write_env(tmp_path, **REQUIRED)

    s = Settings(_env_file=env)

    assert str(s.API_ENDPOINT) == REQUIRED["API_ENDPOINT"]
    assert s.API_KEY == REQUIRED["API_KEY"]
    assert s.ENVIRONMENT == "development"
    # All optional feature flags off by default.
    assert s.slack_enabled is False
    assert s.news_enabled is False
    assert s.email_enabled is False


def test_loads_full_production_env_file(tmp_path):
    """All optional integrations configured → feature flags flip on, port is coerced to int."""
    env = write_env(
        tmp_path,
        **REQUIRED,
        SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T000/B000/XXXX",
        NEWS_API_KEY="pub_abc",
        SUPPORT_EMAIL="support@example.com",
        SMTP_SERVER="smtp.example.com",
        SMTP_PORT="587",
        SENDER_EMAIL="bot@example.com",
        SENDER_PASSWORD="hunter2",
        ENVIRONMENT="production",
    )

    s = Settings(_env_file=env)

    assert s.SMTP_PORT == 587  # coerced from string
    assert isinstance(s.SMTP_PORT, int)
    assert s.email_enabled is True
    assert s.slack_enabled is True
    assert s.news_enabled is True
    assert s.ENVIRONMENT == "production"


# --------------------------------------------------------------------- #
# Helper behaviour
# --------------------------------------------------------------------- #

def test_llm_headers_contents(tmp_path):
    env = write_env(tmp_path, **REQUIRED)
    s = Settings(_env_file=env)

    headers = s.llm_headers()
    assert headers == {
        "Content-Type": "application/json",
        "api-key": "sk-test-123",
        "Authorization": "Bearer sk-test-123",
    }


def test_get_settings_is_cached(monkeypatch, tmp_path):
    """Repeated calls return the same instance; cache_clear resets it."""
    monkeypatch.chdir(tmp_path)
    for k, v in REQUIRED.items():
        monkeypatch.setenv(k, v)

    a = get_settings()
    b = get_settings()
    assert a is b

    get_settings.cache_clear()
    c = get_settings()
    assert c is not a


def test_feature_disabled_message_phrasing():
    assert feature_disabled_message("Slack alerting") == "Slack alerting is not configured on this server."
    assert feature_disabled_message("News lookup").endswith("is not configured on this server.")


# --------------------------------------------------------------------- #
# Failure modes – required values
# --------------------------------------------------------------------- #

def test_missing_api_key_fails_fast(tmp_path):
    env = write_env(tmp_path, API_ENDPOINT=REQUIRED["API_ENDPOINT"])

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=env)
    assert "API_KEY" in str(exc.value)


def test_missing_api_endpoint_fails_fast(tmp_path):
    env = write_env(tmp_path, API_KEY=REQUIRED["API_KEY"])

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=env)
    assert "API_ENDPOINT" in str(exc.value)


def test_malformed_api_endpoint_rejected(tmp_path):
    env = write_env(tmp_path, API_ENDPOINT="not-a-url", API_KEY="sk-test")

    with pytest.raises(ValidationError):
        Settings(_env_file=env)


def test_get_settings_wraps_validation_error(monkeypatch):
    """The cached accessor surfaces a friendly ConfigurationError naming the bad field."""
    # No .env, no env vars → required fields missing.
    monkeypatch.chdir("/")  # ensure no stray .env is picked up
    with pytest.raises(ConfigurationError) as exc:
        get_settings()
    msg = str(exc.value)
    assert "API_ENDPOINT" in msg
    assert "API_KEY" in msg


# --------------------------------------------------------------------- #
# Edge cases – SMTP group
# --------------------------------------------------------------------- #

def test_invalid_smtp_port_type_rejected(tmp_path):
    """Non-integer SMTP_PORT must raise rather than be silently accepted."""
    env = write_env(
        tmp_path,
        **REQUIRED,
        SUPPORT_EMAIL="support@example.com",
        SMTP_SERVER="smtp.example.com",
        SMTP_PORT="not-an-int",
        SENDER_EMAIL="bot@example.com",
        SENDER_PASSWORD="hunter2",
    )

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=env)
    assert "SMTP_PORT" in str(exc.value)


def test_smtp_port_out_of_range_rejected(tmp_path):
    env = write_env(
        tmp_path,
        **REQUIRED,
        SUPPORT_EMAIL="support@example.com",
        SMTP_SERVER="smtp.example.com",
        SMTP_PORT="70000",
        SENDER_EMAIL="bot@example.com",
        SENDER_PASSWORD="hunter2",
    )

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=env)
    assert "SMTP_PORT" in str(exc.value)


def test_partial_smtp_group_rejected(tmp_path):
    """Setting some-but-not-all SMTP vars is a misconfiguration, not a silent no-op."""
    env = write_env(
        tmp_path,
        **REQUIRED,
        SMTP_SERVER="smtp.example.com",
        SMTP_PORT="587",
    )

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=env)
    msg = str(exc.value)
    assert "Incomplete SMTP configuration" in msg
    assert "SENDER_EMAIL" in msg


def test_malformed_support_email_rejected(tmp_path):
    """EmailStr validation catches obviously invalid addresses."""
    env = write_env(
        tmp_path,
        **REQUIRED,
        SUPPORT_EMAIL="not-an-email",
        SMTP_SERVER="smtp.example.com",
        SMTP_PORT="587",
        SENDER_EMAIL="bot@example.com",
        SENDER_PASSWORD="hunter2",
    )

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=env)
    assert "SUPPORT_EMAIL" in str(exc.value)
