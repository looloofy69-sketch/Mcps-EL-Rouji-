"""Configuration and argument validation for the EL-Rouji MCP adapter."""
from __future__ import annotations

import os
from urllib.parse import urlsplit

DEFAULT_BASE_URL = "https://el-rouji-70120b.v2.appdeploy.ai"
ALLOWED_LANGUAGES = {"en", "fr", "ar"}
ALLOWED_MODES = {"assistant", "research", "writing", "study", "coding", "planning"}


def normalize_base_url(value: str | None = None) -> str:
    raw = (value if value is not None else os.getenv("EL_ROUJI_BASE_URL", DEFAULT_BASE_URL)).strip()
    if not raw:
        raise ValueError("EL_ROUJI_BASE_URL must be a non-empty URL.")
    try:
        parsed = urlsplit(raw)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("EL_ROUJI_BASE_URL is not a valid URL.") from exc

    if parsed.scheme not in {"https", "http"} or not parsed.netloc or not hostname:
        raise ValueError("EL_ROUJI_BASE_URL must be an absolute HTTP(S) URL.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials must not be embedded in EL_ROUJI_BASE_URL.")
    if parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("EL_ROUJI_BASE_URL must contain only an origin, without path, query, or fragment.")
    if parsed.scheme == "http" and hostname.lower() not in {"localhost", "127.0.0.1", "::1"} and not hostname.lower().endswith(".localhost"):
        raise ValueError("Plain HTTP is allowed only for localhost development; use HTTPS for remote services.")
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def generation_enabled() -> bool:
    """Generation calls require an explicit local opt-in."""
    return os.getenv("EL_ROUJI_ENABLE_GENERATION", "").strip().lower() in {"1", "true", "yes"}


def validate_text(value: str, field: str, maximum: int, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text.")
    value = value.strip()
    if not value and not allow_empty:
        raise ValueError(f"{field} must not be empty.")
    if len(value) > maximum:
        raise ValueError(f"{field} exceeds the {maximum}-character limit.")
    return value


def validate_language(language: str) -> str:
    if language not in ALLOWED_LANGUAGES:
        raise ValueError("language must be one of: en, fr, ar.")
    return language


def validate_mode(mode: str) -> str:
    if mode not in ALLOWED_MODES:
        raise ValueError("mode must be one of: assistant, research, writing, study, coding, planning.")
    return mode
