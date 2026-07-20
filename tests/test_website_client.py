import httpx
import pytest

from app.collectors.websites.client import WebsiteClient
from app.collectors.websites.exceptions import ResponseTooLargeError, UnsupportedContentError
from app.core.config import Settings


def settings(**values):
    return Settings(website_crawler_min_request_delay_ms=0, website_crawler_max_request_delay_ms=0, **values)


def test_client_headers_retry_and_retry_after():
    calls = []
    sleeps = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"content-type": "text/html", "retry-after": "2"}, request=request)
        return httpx.Response(200, headers={"content-type": "text/html"}, text="ok", request=request)

    client = WebsiteClient(settings(), transport=httpx.MockTransport(handler), validator=lambda value: value, sleeper=sleeps.append)
    result = client.fetch("https://example.com/", seed_url="https://example.com/", allow_subdomains=False)
    assert result.content == b"ok" and len(calls) == 2 and sleeps == [2.0]
    assert calls[0].headers["user-agent"] == "AlduorProjectDiscoveryBot/0.1"
    client.close()


def test_client_does_not_retry_403():
    count = 0

    def handler(request):
        nonlocal count
        count += 1
        return httpx.Response(403, headers={"content-type": "text/html"}, request=request)

    client = WebsiteClient(settings(), transport=httpx.MockTransport(handler), validator=lambda value: value, sleeper=lambda _: None)
    assert client.fetch("https://example.com/", seed_url="https://example.com/", allow_subdomains=False).status_code == 403
    assert count == 1
    client.close()


def test_client_revalidates_redirect_and_rejects_external_or_private_target():
    validated = []

    def validator(value):
        validated.append(value)
        if "127.0.0.1" in value:
            raise ValueError("private")
        return value

    transport = httpx.MockTransport(lambda request: httpx.Response(302, headers={"location": "http://127.0.0.1/"}, request=request))
    client = WebsiteClient(settings(), transport=transport, validator=validator, sleeper=lambda _: None)
    with pytest.raises(ValueError):
        client.fetch("https://example.com/", seed_url="https://example.com/", allow_subdomains=False)
    assert len(validated) == 2
    client.close()


def test_client_enforces_type_and_body_limits():
    client = WebsiteClient(settings(website_crawler_max_response_bytes=4), transport=httpx.MockTransport(lambda request: httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"pdf", request=request)), validator=lambda value: value, sleeper=lambda _: None)
    with pytest.raises(UnsupportedContentError):
        client.fetch("https://example.com/", seed_url="https://example.com/", allow_subdomains=False)
    client.close()
    client = WebsiteClient(settings(website_crawler_max_response_bytes=4), transport=httpx.MockTransport(lambda request: httpx.Response(200, headers={"content-type": "text/html"}, content=b"12345", request=request)), validator=lambda value: value, sleeper=lambda _: None)
    with pytest.raises(ResponseTooLargeError):
        client.fetch("https://example.com/", seed_url="https://example.com/", allow_subdomains=False)
    client.close()
