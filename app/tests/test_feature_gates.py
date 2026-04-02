"""
Tests that feature-gated tools degrade gracefully when their optional
integration is not configured, and do **not** attempt any outbound network
call in that state.

Only the lightweight ``general_agent`` tools are exercised here so the test
suite does not need to import the heavy ML stack pulled in by other agents.
"""

import os
import sys

import pytest

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from config import feature_disabled_message, get_settings  # noqa: E402


ALL_CONFIG_KEYS = (
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
)


@pytest.fixture(autouse=True)
def _minimal_env(monkeypatch, tmp_path):
    """Required LLM config only; every optional integration disabled."""
    for key in ALL_CONFIG_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("API_ENDPOINT", "https://example.com/v1/chat/completions")
    monkeypatch.setenv("API_KEY", "sk-test")
    monkeypatch.chdir(tmp_path)  # avoid picking up a real .env
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def forbid_outbound_requests(monkeypatch):
    """Fail the test if any code path tries to hit the network."""
    import requests

    def _boom(*args, **kwargs):  # pragma: no cover - should never run
        raise AssertionError("Unexpected outbound HTTP call while integration is disabled")

    monkeypatch.setattr(requests, "get", _boom)
    monkeypatch.setattr(requests, "post", _boom)


def test_news_tool_disabled_returns_stub(forbid_outbound_requests):
    from agents.general_agent import get_news_tool

    result = get_news_tool("fintech")

    assert result == {
        "tool_name": "get_news_tool",
        "Response": feature_disabled_message("News lookup"),
    }


def test_slack_tool_disabled_returns_stub(forbid_outbound_requests):
    from agents.general_agent import send_slack_notification_tool

    result = send_slack_notification_tool("user-1", "suspicious query")

    assert result == {
        "tool_name": "slack_notification",
        "Response": feature_disabled_message("Slack alerting"),
    }


def test_news_tool_enabled_attempts_request(monkeypatch):
    """When the integration IS configured the tool proceeds past the gate."""
    monkeypatch.setenv("NEWS_API_KEY", "pub_test")
    get_settings.cache_clear()

    import requests
    called = {}

    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": [{"title": "Headline A"}, {"title": "Headline B"}]}

    def fake_get(url, *args, **kwargs):
        called["url"] = url
        return _FakeResponse()

    monkeypatch.setattr(requests, "get", fake_get)

    from agents.general_agent import get_news_tool
    result = get_news_tool("fintech")

    assert "pub_test" in called["url"]
    assert result["tool_name"] == "get_news_tool"
    assert "Headline A" in result["Response"]
