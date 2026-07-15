"""Async HTTP client for the Budget Planner backend.

Thin wrapper around httpx that talks to the FastAPI backend. Mirrors the
synchronous `_get`/`_post` pattern in telegram_bot/src/api/client.py, but async
and with a request timeout and LLM-readable structured errors so the MCP agent
can read failures and self-correct instead of seeing a raw traceback.
"""
import os
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

BACKEND_API_BASE_URL = os.getenv("BACKEND_API_BASE_URL")
if not BACKEND_API_BASE_URL:
    backend_host = os.getenv("BACKEND_API_HOST", "localhost")
    backend_port = os.getenv("BACKEND_API_PORT", "8000")
    BACKEND_API_BASE_URL = f"http://{backend_host}:{backend_port}"
BACKEND_REQUEST_TIMEOUT = float(os.getenv("BACKEND_REQUEST_TIMEOUT", "10.0"))


def _error(status_code: Optional[int], message: str, details: Any) -> Dict[str, Any]:
    """Build a structured, model-readable error payload."""
    return {
        "ok": False,
        "status_code": status_code,
        "error": message,
        "details": details,
    }


class BackendClient:
    """Async client returning parsed JSON on success or a structured error dict."""

    def __init__(self, base_url: str = BACKEND_API_BASE_URL, timeout: float = BACKEND_REQUEST_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout)

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.request(method, url, params=params, json=json)
                response.raise_for_status()
                # Some endpoints (rare) may return empty bodies.
                if not response.content:
                    return {"ok": True}
                return response.json()
        except httpx.HTTPStatusError as exc:
            # Backend responded with 4xx/5xx — surface its body so the model can fix the call.
            try:
                details = exc.response.json()
            except Exception:
                details = exc.response.text
            return _error(exc.response.status_code, "Backend request failed", details)
        except httpx.TimeoutException:
            return _error(None, "Backend request timed out", f"No response within {self.timeout.read}s")
        except httpx.RequestError as exc:
            return _error(None, "Could not reach backend", str(exc))

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return await self._request("GET", endpoint, params=params)

    async def post(self, endpoint: str, json: Optional[Dict[str, Any]] = None,
                   params: Optional[Dict[str, Any]] = None) -> Any:
        return await self._request("POST", endpoint, json=json, params=params)

    async def put(self, endpoint: str, json: Optional[Dict[str, Any]] = None,
                  params: Optional[Dict[str, Any]] = None) -> Any:
        return await self._request("PUT", endpoint, json=json, params=params)

    async def delete(self, endpoint: str) -> Any:
        return await self._request("DELETE", endpoint)
