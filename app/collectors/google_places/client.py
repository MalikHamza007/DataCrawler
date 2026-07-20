from __future__ import annotations

import time
from typing import Any

import httpx

from app.collectors.google_places.exceptions import (
    GooglePlacesAuthenticationError,
    GooglePlacesConfigurationError,
    GooglePlacesInvalidRequestError,
    GooglePlacesPermissionError,
    GooglePlacesRateLimitError,
    GooglePlacesServerError,
    GooglePlacesTimeoutError,
)
from app.collectors.google_places.field_masks import NEARBY_SEARCH_FIELD_MASK, TEXT_SEARCH_FIELD_MASK, validate_field_mask
from app.core.config import Settings, get_settings


class GooglePlacesClient:
    def __init__(self, settings: Settings | None = None, http_client: httpx.Client | None = None) -> None:
        self.settings = settings or get_settings()
        if self.settings.google_places_enabled and not self.settings.google_places_server_api_key:
            raise GooglePlacesConfigurationError("Google Places is enabled but the server API key is missing.")
        self.http_client = http_client or httpx.Client(timeout=self.settings.google_places_timeout_seconds)
        self.request_count = 0
        self.retry_count = 0

    def text_search(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._post("/places:searchText", body, TEXT_SEARCH_FIELD_MASK)

    def nearby_search(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._post("/places:searchNearby", body, NEARBY_SEARCH_FIELD_MASK)

    def _post(self, path: str, body: dict[str, Any], field_mask: str) -> dict[str, Any]:
        validate_field_mask(field_mask)
        if not self.settings.google_places_enabled:
            raise GooglePlacesConfigurationError("Google Places integration is disabled.")
        if not self.settings.google_places_server_api_key:
            raise GooglePlacesConfigurationError("Google Places server API key is missing.")
        url = f"{self.settings.google_places_api_base_url.rstrip('/')}{path}"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.settings.google_places_server_api_key,
            "X-Goog-FieldMask": field_mask,
        }
        last_error: Exception | None = None
        for attempt in range(1, self.settings.google_places_max_retries + 1):
            try:
                self.request_count += 1
                response = self.http_client.post(url, json=body, headers=headers, timeout=self.settings.google_places_timeout_seconds)
                if response.status_code in {429, 500, 502, 503, 504}:
                    if attempt < self.settings.google_places_max_retries:
                        self.retry_count += 1
                        self._sleep_for_retry(response, attempt)
                        continue
                    self._raise_for_status(response)
                self._raise_for_status(response)
                return response.json()
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt < self.settings.google_places_max_retries:
                    self.retry_count += 1
                    self._sleep(attempt)
                    continue
                raise GooglePlacesTimeoutError("Google Places request timed out.") from exc
            except httpx.TransportError as exc:
                last_error = exc
                if attempt < self.settings.google_places_max_retries:
                    self.retry_count += 1
                    self._sleep(attempt)
                    continue
                raise GooglePlacesServerError("Google Places request failed due to a network error.") from exc
        raise GooglePlacesServerError("Google Places request failed.") from last_error

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        if response.status_code == 400:
            raise GooglePlacesInvalidRequestError("Google Places rejected the request.")
        if response.status_code == 401:
            raise GooglePlacesAuthenticationError("Google Places server key is invalid.")
        if response.status_code == 403:
            raise GooglePlacesPermissionError("Google Places server key is not authorized for Places API.")
        if response.status_code == 429:
            raise GooglePlacesRateLimitError("Google Places rate limit was reached.")
        if response.status_code >= 500:
            raise GooglePlacesServerError("Google Places server error.")
        raise GooglePlacesServerError("Google Places request failed.")

    def _sleep_for_retry(self, response: httpx.Response, attempt: int) -> None:
        retry_after = response.headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            time.sleep(min(int(retry_after), 5))
            return
        self._sleep(attempt)

    def _sleep(self, attempt: int) -> None:
        delay = min(2 ** (attempt - 1), 5)
        if self.settings.google_places_request_delay_ms == 0:
            delay = 0
        time.sleep(delay)
