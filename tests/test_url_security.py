import socket

import pytest

from app.collectors.websites.canonicalization import canonicalize_url
from app.collectors.websites.exceptions import UnsafeURLError
from app.collectors.websites.security import is_same_site, validate_url_dns, validate_url_syntax


@pytest.mark.parametrize("url", ["https://example.com", "http://example.com/path"])
def test_allows_public_http_urls_without_dns(url):
    assert validate_url_syntax(url).startswith(("http://", "https://"))


@pytest.mark.parametrize("url", ["file:///etc/passwd", "data:text/plain,x", "http://user:pass@example.com", "http://localhost", "http://x.local", "http://127.0.0.1", "http://10.1.2.3", "http://172.20.0.1", "http://192.168.1.1", "http://169.254.1.1", "http://[::1]", "http://[fc00::1]", "http://[fe80::1]", "http://internal"])
def test_rejects_unsafe_urls(url):
    with pytest.raises(UnsafeURLError):
        validate_url_syntax(url)


def test_dns_rejects_private_result():
    resolver = lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]
    with pytest.raises(UnsafeURLError):
        validate_url_dns("https://example.com", resolver)


def test_dns_retries_on_transient_failure_then_succeeds():
    calls = {"count": 0}

    def flaky_resolver(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            raise OSError("temporary DNS failure")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    sleeps = []
    result = validate_url_dns("https://example.com", flaky_resolver, sleeper=sleeps.append)
    assert result == "https://example.com/"
    assert calls["count"] == 3
    assert len(sleeps) == 2


def test_dns_raises_after_exhausting_retries():
    def always_fails(*args, **kwargs):
        raise OSError("permanent DNS failure")

    with pytest.raises(UnsafeURLError):
        validate_url_dns("https://example.com", always_fails, sleeper=lambda _: None)


def test_canonicalization_and_same_site_policy():
    assert canonicalize_url("HTTPS://Example.COM:443/a?utm_source=x&b=2&a=1#part") == "https://example.com/a?a=1&b=2"
    assert is_same_site("https://example.com/projects", "https://example.com/")
    assert not is_same_site("https://sales.example.com/", "https://example.com/")
    assert is_same_site("https://sales.example.com/", "https://example.com/", True)
