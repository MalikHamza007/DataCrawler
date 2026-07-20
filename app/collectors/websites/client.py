from __future__ import annotations

import asyncio
import email.utils
import time
from collections.abc import Callable
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

import httpx

from app.collectors.websites.exceptions import ResponseTooLargeError, TemporaryWebsiteError, UnsupportedContentError
from app.collectors.websites.security import is_same_site, validate_url_dns
from app.collectors.websites.types import FetchResult
from app.core.config import Settings

ALLOWED_TYPES = {"text/html", "application/xhtml+xml", "application/xml", "text/xml", "application/ld+json"}
RETRY_STATUSES = {429, 500, 502, 503, 504}


class WebsiteClient:
    def __init__(self, settings: Settings, *, transport: httpx.BaseTransport | None = None, validator: Callable[[str], str] = validate_url_dns, sleeper: Callable[[float], None] = time.sleep) -> None:
        self.settings = settings
        self.validator = validator
        self.sleeper = sleeper
        self.last_request: dict[str, float] = {}
        self.client = httpx.Client(
            transport=transport, follow_redirects=False,
            timeout=httpx.Timeout(connect=settings.website_crawler_connect_timeout_seconds, read=settings.website_crawler_timeout_seconds, write=10.0, pool=10.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5, keepalive_expiry=10),
            headers={"User-Agent": settings.website_crawler_user_agent, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.1", "Accept-Language": "en-PK,en;q=0.9"},
        )

    def close(self) -> None:
        self.client.close()

    def fetch(self, url: str, *, seed_url: str, allow_subdomains: bool, conditional_headers: dict[str, str] | None = None, cancellation_check: Callable[[], None] | None = None, allowed_content_types: set[str] | None = None) -> FetchResult:
        current = self.validator(url)
        redirects = 0
        retries = 0
        while True:
            if cancellation_check:
                cancellation_check()
            if not is_same_site(current, seed_url, allow_subdomains):
                raise ValueError("Redirect or request left the approved site")
            self._delay(urlsplit(current).hostname or "")
            try:
                with self.client.stream("GET", current, headers=conditional_headers) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        if redirects >= self.settings.website_crawler_max_redirects or not response.headers.get("location"):
                            raise ValueError("Maximum redirects exceeded")
                        current = self.validator(urljoin(current, response.headers["location"]))
                        redirects += 1
                        continue
                    if response.status_code in RETRY_STATUSES and retries < self.settings.website_crawler_max_retries:
                        self.sleeper(self._retry_delay(response, retries))
                        retries += 1
                        continue
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                    permitted = allowed_content_types or ALLOWED_TYPES
                    if response.status_code != 304 and content_type not in permitted:
                        raise UnsupportedContentError(f"Unsupported content type: {content_type or 'missing'}")
                    length = response.headers.get("content-length")
                    if length and int(length) > self.settings.website_crawler_max_response_bytes:
                        raise ResponseTooLargeError("Response exceeds maximum size")
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > self.settings.website_crawler_max_response_bytes:
                            raise ResponseTooLargeError("Response exceeds maximum size")
                    if response.status_code in RETRY_STATUSES:
                        raise TemporaryWebsiteError(f"Temporary HTTP {response.status_code}")
                    return FetchResult(current, response.status_code, content_type, bytes(body), dict(response.headers))
            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as exc:
                if retries >= self.settings.website_crawler_max_retries:
                    raise TemporaryWebsiteError(str(exc)) from exc
                self.sleeper(2 ** retries)
                retries += 1

    def _delay(self, host: str) -> None:
        minimum = self.settings.website_crawler_min_request_delay_ms / 1000
        remaining = minimum - (time.monotonic() - self.last_request.get(host, 0))
        if remaining > 0:
            self.sleeper(remaining)
        self.last_request[host] = time.monotonic()

    @staticmethod
    def _retry_delay(response: httpx.Response, retries: int) -> float:
        value = response.headers.get("retry-after")
        if value:
            try:
                return max(0.0, float(value))
            except ValueError:
                try:
                    parsed = email.utils.parsedate_to_datetime(value)
                    return max(0.0, (parsed - datetime.now(timezone.utc)).total_seconds())
                except (TypeError, ValueError):
                    pass
        return float(2 ** retries)
