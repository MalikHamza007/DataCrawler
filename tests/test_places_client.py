import json
from pathlib import Path

import httpx
import pytest

from app.collectors.google_places.client import GooglePlacesClient
from app.collectors.google_places.exceptions import GooglePlacesInvalidRequestError, GooglePlacesPermissionError, GooglePlacesRateLimitError, GooglePlacesTimeoutError
from app.collectors.google_places.field_masks import TEXT_SEARCH_FIELD_MASK, validate_field_mask
from app.core.config import Settings


def settings() -> Settings:
    return Settings(
        google_places_enabled=True,
        google_places_server_api_key="test-fake-key",
        google_places_request_delay_ms=0,
        google_places_max_retries=2,
    )


def test_text_search_request_format_and_secret_handling() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["json"] = json.loads(request.content)
        return httpx.Response(200, json={"places": []})

    client = GooglePlacesClient(settings=settings(), http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    response = client.text_search({"textQuery": "apartment project in Gulberg Lahore"})
    assert response == {"places": []}
    assert captured["url"] == "https://places.googleapis.com/v1/places:searchText"
    assert "test-fake-key" not in captured["url"]
    assert captured["headers"]["X-Goog-Api-Key"] == "test-fake-key"
    assert captured["headers"]["X-Goog-FieldMask"] == TEXT_SEARCH_FIELD_MASK


def test_nearby_search_url_and_wildcard_mask_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/places:searchNearby")
        return httpx.Response(200, json={"places": []})

    client = GooglePlacesClient(settings=settings(), http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert client.nearby_search({"includedTypes": ["shopping_mall"]}) == {"places": []}
    with pytest.raises(ValueError):
        validate_field_mask("*")


def test_retry_and_non_retryable_errors() -> None:
    calls = {"count": 0}

    def retry_handler(_: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, json={"error": {"message": "rate"}})
        return httpx.Response(200, json={"places": []})

    client = GooglePlacesClient(settings=settings(), http_client=httpx.Client(transport=httpx.MockTransport(retry_handler)))
    assert client.text_search({"textQuery": "x"}) == {"places": []}
    assert calls["count"] == 2
    assert client.retry_count == 1

    bad = GooglePlacesClient(settings=settings(), http_client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(400, json={}))))
    with pytest.raises(GooglePlacesInvalidRequestError):
        bad.text_search({"textQuery": "x"})

    forbidden = GooglePlacesClient(settings=settings(), http_client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(403, json={}))))
    with pytest.raises(GooglePlacesPermissionError):
        forbidden.text_search({"textQuery": "x"})

    rate_limited_settings = settings()
    rate_limited_settings.google_places_max_retries = 1
    rate_limited = GooglePlacesClient(settings=rate_limited_settings, http_client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(429, json={}))))
    with pytest.raises(GooglePlacesRateLimitError):
        rate_limited.text_search({"textQuery": "x"})


def test_timeout_is_retried() -> None:
    calls = {"count": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        raise httpx.TimeoutException("timeout")

    client = GooglePlacesClient(settings=settings(), http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(GooglePlacesTimeoutError):
        client.text_search({"textQuery": "x"})
    assert calls["count"] == 2
