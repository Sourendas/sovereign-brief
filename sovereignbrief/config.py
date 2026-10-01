"""Environment configuration. Fails clearly when HF_TOKEN is missing for remote calls."""

from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_BASE_URL = "https://router.huggingface.co/v1"
DEFAULT_MODEL = "swiss-ai/Apertus-v1.5-8B"
# Live free-tier route on HF Inference Providers (Public AI). v1.5-8B has no
# provider mapping as of 2026-10-02, so remote 404s fall back to this id.
# Pin :publicai so the router cannot switch to a different billed provider.
DEFAULT_FREE_FALLBACK_MODEL = "swiss-ai/Apertus-8B-Instruct-2509:publicai"
DEFAULT_TIMEOUT = 120.0


@dataclass(frozen=True)
class Settings:
    hf_token: str | None
    apertus_base_url: str
    apertus_model: str
    apertus_timeout: float
    apertus_fallback_model: str | None = None

    @property
    def is_local_endpoint(self) -> bool:
        url = self.apertus_base_url.lower()
        return any(
            host in url
            for host in ("127.0.0.1", "localhost", "0.0.0.0", "[::1]")
        )

    def require_token_for_remote(self) -> str | None:
        """Return token, or None for local endpoints. Raise if remote and missing."""
        if self.hf_token:
            return self.hf_token
        if self.is_local_endpoint:
            return None
        raise RuntimeError(
            "HF_TOKEN is required for remote Apertus inference "
            f"(base URL: {self.apertus_base_url}). "
            "Copy .env.example to .env and set HF_TOKEN, "
            "or set APERTUS_BASE_URL to a local OpenAI-compatible endpoint "
            "(e.g. http://127.0.0.1:8000/v1)."
        )


def load_settings() -> Settings:
    timeout_raw = os.environ.get("APERTUS_TIMEOUT", str(DEFAULT_TIMEOUT))
    try:
        timeout = float(timeout_raw)
    except ValueError:
        timeout = DEFAULT_TIMEOUT
    token = os.environ.get("HF_TOKEN") or os.environ.get("APERTUS_API_KEY")
    if token is not None:
        token = token.strip() or None
    fallback_raw = os.environ.get("APERTUS_FALLBACK_MODEL", DEFAULT_FREE_FALLBACK_MODEL)
    fallback = (fallback_raw or "").strip() or None
    # Empty string disables fallback (local/offline). "0" / "off" also disable.
    if fallback and fallback.lower() in {"0", "off", "none", "false"}:
        fallback = None
    primary = os.environ.get("APERTUS_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    if fallback == primary:
        fallback = None
    return Settings(
        hf_token=token,
        apertus_base_url=os.environ.get("APERTUS_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        apertus_model=primary,
        apertus_timeout=timeout,
        apertus_fallback_model=fallback,
    )
