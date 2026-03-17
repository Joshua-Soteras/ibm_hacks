"""Shared HTTP client helper for ADK tools calling back to the FastAPI backend."""

import os
import requests

# Connection app_id — used in @tool(expected_credentials=...) declarations
BACKEND_CONNECTION = {"app_id": "backend_api", "type": "key_value_creds"}

_cached_url = None


def _resolve_backend_url() -> str:
    """Resolve backend API URL from Orchestrate connection or env var.

    Priority:
    1. Orchestrate key_value connection (app_id: backend_api) — cloud deployment
    2. BACKEND_API_URL environment variable — local testing
    """
    # Try Orchestrate connection first (cloud deployment)
    try:
        from ibm_watsonx_orchestrate.run import connections
        conn = connections.key_value("backend_api")
        url = conn.get("BACKEND_API_URL", "")
        if url:
            return url.rstrip("/")
    except Exception:
        pass

    # Fallback to environment variable (local dev / testing)
    return os.environ.get("BACKEND_API_URL", "").rstrip("/")


def _get_url() -> str:
    """Lazy-resolve and cache the backend URL."""
    global _cached_url
    if _cached_url is None:
        _cached_url = _resolve_backend_url()
    return _cached_url


def is_api_mode() -> bool:
    """Return True when tools should use HTTP callbacks instead of local SQLite."""
    return bool(_get_url())


def api_get(path: str, params: dict = None, timeout: int = 30) -> dict:
    """GET request to the FastAPI backend, returning parsed JSON."""
    url = _get_url()
    headers = {
        # Skip ngrok free-tier browser interstitial when tunneling
        "ngrok-skip-browser-warning": "true",
    }
    resp = requests.get(f"{url}{path}", params=params, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()
