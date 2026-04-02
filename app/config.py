"""
Central application configuration.

All runtime configuration for the Agent Swarm is defined here in a single
``Settings`` model. Values are loaded from environment variables (and an
optional ``.env`` file) via ``pydantic-settings`` and validated on first
access, so misconfiguration surfaces as a clear error at process start
rather than as an obscure failure deep inside an agent.

Configuration is split into two tiers:

* **Required** – the service cannot function without these (the LLM API
  endpoint and key). Missing or malformed values raise ``ConfigurationError``
  immediately.

* **Optional / feature‑gated** – Slack alerts, the news API, and outbound
  support email. These are ``None`` by default so the app runs in local
  development without them; the corresponding agent tools degrade gracefully
  when unset. The SMTP group is validated *as a unit*: either leave it all
  unset, or provide every field.

Access pattern
--------------
Application code should obtain configuration via the cached accessor::

    from config import get_settings
    cfg = get_settings()

Call ``get_settings()`` at the point of use (inside the function or method
that needs it) rather than binding a module-level ``settings`` global. The
``lru_cache`` guarantees a single validated instance per process, and
deferring the call keeps modules importable in tests that override the
environment before invoking ``get_settings.cache_clear()``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import AnyHttpUrl, EmailStr, Field, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(RuntimeError):
    """Raised when the application configuration is invalid or incomplete."""


class Settings(BaseSettings):
    # ----------------------------------------------------------------- #
    # Required – the LLM backend every agent talks to.
    # ----------------------------------------------------------------- #
    API_ENDPOINT: AnyHttpUrl = Field(
        ...,
        description="Chat-completions endpoint used by all agents.",
    )
    API_KEY: str = Field(
        ...,
        min_length=1,
        description="API key / bearer token for the LLM endpoint.",
    )

    # ----------------------------------------------------------------- #
    # Optional – integrations that are nice-to-have in production but
    # not needed for local development. Leaving them unset disables the
    # corresponding feature gracefully.
    # ----------------------------------------------------------------- #
    SLACK_WEBHOOK_URL: Optional[AnyHttpUrl] = Field(
        default=None,
        description="Incoming webhook for suspicious-activity alerts.",
    )
    NEWS_API_KEY: Optional[str] = Field(
        default=None,
        description="newsdata.io API key used by the GeneralAgent news tool.",
    )

    # --- Outbound support email (all-or-nothing group) ---------------- #
    SUPPORT_EMAIL: Optional[EmailStr] = Field(
        default=None,
        description="Destination address for escalated support tickets.",
    )
    SMTP_SERVER: Optional[str] = Field(default=None)
    SMTP_PORT: Optional[int] = Field(
        default=None,
        ge=1,
        le=65535,
        description="SMTP server port (e.g. 587).",
    )
    SENDER_EMAIL: Optional[EmailStr] = Field(default=None)
    SENDER_PASSWORD: Optional[str] = Field(default=None)

    # ----------------------------------------------------------------- #
    # App behaviour
    # ----------------------------------------------------------------- #
    ENVIRONMENT: str = Field(
        default="development",
        description='Deployment environment: "development" or "production".',
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ----------------------------------------------------------------- #
    # Cross-field validation
    # ----------------------------------------------------------------- #
    _SMTP_FIELDS = (
        "SUPPORT_EMAIL",
        "SMTP_SERVER",
        "SMTP_PORT",
        "SENDER_EMAIL",
        "SENDER_PASSWORD",
    )

    @model_validator(mode="after")
    def _validate_smtp_group(self) -> "Settings":
        provided = [f for f in self._SMTP_FIELDS if getattr(self, f) is not None]
        if provided and len(provided) != len(self._SMTP_FIELDS):
            missing = sorted(set(self._SMTP_FIELDS) - set(provided))
            raise ValueError(
                "Incomplete SMTP configuration. Provide all of "
                f"{', '.join(self._SMTP_FIELDS)} or none of them. "
                f"Missing: {', '.join(missing)}."
            )
        return self

    # ----------------------------------------------------------------- #
    # Convenience helpers
    # ----------------------------------------------------------------- #
    @property
    def email_enabled(self) -> bool:
        """True when the full SMTP group is configured."""
        return all(getattr(self, f) is not None for f in self._SMTP_FIELDS)

    @property
    def slack_enabled(self) -> bool:
        return self.SLACK_WEBHOOK_URL is not None

    @property
    def news_enabled(self) -> bool:
        return self.NEWS_API_KEY is not None

    def llm_headers(self) -> dict[str, str]:
        """Standard headers for calls to ``API_ENDPOINT``."""
        return {
            "Content-Type": "application/json",
            "api-key": self.API_KEY,
            "Authorization": f"Bearer {self.API_KEY}",
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the process-wide ``Settings`` instance.

    Cached so the ``.env`` file is read and validated exactly once. Wraps
    pydantic's ``ValidationError`` in ``ConfigurationError`` with a friendlier
    message so operators see immediately which variables are wrong.
    """
    try:
        return Settings()
    except ValidationError as exc:
        details = "\n".join(
            f"  - {'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        )
        raise ConfigurationError(
            "Invalid or missing configuration. Set the following environment "
            f"variables (see README → Configuration):\n{details}"
        ) from exc


def feature_disabled_message(feature: str) -> str:
    """
    Standard user-facing message returned by a tool when its backing
    integration is not configured. Keeps phrasing consistent across
    Slack, news and support-email tools.
    """
    return f"{feature} is not configured on this server."
