"""Polite HTTP: one request at a time, a minimum gap between requests, and backoff on 429 and 5xx."""

import time

import httpx

USER_AGENT = "chatbot-rag-tokenizers/0.1 (+https://github.com/mudassirkhan19/chatbot_rag_tokenizers)"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_BACKOFF_SECONDS = 60.0


class RateLimitedHttp:
    def __init__(self, min_interval: float, max_attempts: int = 6, timeout: float = 60.0) -> None:
        self.min_interval = min_interval
        self.max_attempts = max_attempts
        self._client = httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
        self._last_request = float("-inf")

    def _wait_for_slot(self) -> None:
        delay = self._last_request + self.min_interval - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        self._last_request = time.monotonic()

    def get(self, url: str, params: dict, headers: dict | None = None) -> str:
        """GET and return the body text. Credentials belong in ``headers``, never in ``params``."""
        response = self.response(url, params, headers)
        response.raise_for_status()
        return response.text

    def response(self, url: str, params: dict | None = None, headers: dict | None = None) -> httpx.Response:
        """GET with retries on transport errors, 429 and 5xx, and return the final response,
        whatever its status."""
        backoff = self.min_interval
        for attempt in range(1, self.max_attempts + 1):
            self._wait_for_slot()
            try:
                response = self._client.get(url, params=params, headers=headers)
            except httpx.TransportError:
                if attempt == self.max_attempts:
                    raise
            else:
                if response.status_code not in RETRYABLE_STATUS or attempt == self.max_attempts:
                    return response
                retry_after = response.headers.get("Retry-After", "")
                if retry_after.isdigit():
                    backoff = max(backoff, float(retry_after))
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
        raise AssertionError("unreachable")
