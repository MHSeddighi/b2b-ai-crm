"""Central runtime configuration for the backend.
All values are read from environment variables (.env) so nothing is hard-coded.
Supports OpenAI, DeepSeek, and any OpenAI-compatible endpoint.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Neutralize any environment proxy that would break outbound LLM calls.
for _v in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
           "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(_v, None)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# Load .env if present (best-effort).
try:
    from dotenv import load_dotenv

    load_dotenv(_repo_root() / ".env")
except Exception:  # pragma: no cover
    pass


@dataclass
class Settings:
    # --- paths ---
    repo_root: Path = field(default_factory=_repo_root)
    db_path: Path = field(
        default_factory=lambda: _repo_root()
        / os.getenv("CUSTOMER360_DB", "data/processed/customer_360.duckdb")
    )

    # --- LLM ---
    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai"))
    # provider = "openai" | "deepseek" | "arvan" | "custom"  (any OpenAI-compatible)
    api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", ""))
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))
    # Session cookie some gateways (e.g. ArvanCloud AI) require alongside the
    # API key. Optional for every other provider.
    cookie: str = field(default_factory=lambda: os.getenv("LLM_COOKIE", ""))

    @property
    def resolved_base_url(self) -> str:
        if self.base_url:
            return self.base_url.rstrip("/")
        if self.provider == "deepseek":
            return "https://api.deepseek.com/v1"
        return "https://api.openai.com/v1"

    @property
    def resolved_model(self) -> str:
        if self.model:
            return self.model
        if self.provider == "deepseek":
            return "deepseek-chat"
        return "gpt-4o-mini"

    @property
    def extra_headers(self) -> dict[str, str]:
        """Headers to override/add on top of the SDK's default ``Authorization:
        Bearer <key>``, for gateways with a non-standard auth scheme.

        ArvanCloud AI Gateway expects ``Authorization: apikey <key>`` plus a
        session cookie rather than a bearer token.
        """
        headers: dict[str, str] = {}
        if self.provider == "arvan":
            headers["Authorization"] = f"apikey {self.api_key}"
        if self.cookie:
            headers["Cookie"] = self.cookie
        return headers

    @property
    def has_key(self) -> bool:
        # A key is needed except when pointing at a local endpoint.
        return bool(self.api_key) or "localhost" in self.resolved_base_url or "127.0.0.1" in self.resolved_base_url


settings = Settings()
