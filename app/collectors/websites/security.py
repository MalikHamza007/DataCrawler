from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urlsplit

import tldextract

from app.collectors.websites.canonicalization import canonicalize_url
from app.collectors.websites.exceptions import UnsafeURLError

Resolver = Callable[..., list[tuple]]
_TLD_EXTRACT = tldextract.TLDExtract(cache_dir=None, suffix_list_urls=())


def _is_unsafe_ip(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return any((address.is_private, address.is_loopback, address.is_link_local, address.is_reserved, address.is_multicast, address.is_unspecified))


def validate_url_syntax(url: str) -> str:
    try:
        original = urlsplit(url)
        if original.username or original.password:
            raise UnsafeURLError("URL credentials are prohibited")
        canonical = canonicalize_url(url)
        parts = urlsplit(canonical)
        if parts.scheme not in {"http", "https"}:
            raise UnsafeURLError("Only HTTP and HTTPS URLs are allowed")
        host = parts.hostname
        if not host:
            raise UnsafeURLError("URL hostname is required")
        lower = host.lower().rstrip(".")
        if lower == "localhost" or lower.endswith(".localhost") or lower == "local" or lower.endswith(".local"):
            raise UnsafeURLError("Local hostnames are prohibited")
        try:
            if _is_unsafe_ip(lower):
                raise UnsafeURLError("Private or non-public IP addresses are prohibited")
        except ValueError:
            extracted = _TLD_EXTRACT(lower, include_psl_private_domains=True)
            if not extracted.domain or not extracted.suffix:
                raise UnsafeURLError("Hostname must have a public suffix")
        return canonical
    except UnsafeURLError:
        raise
    except (ValueError, UnicodeError) as exc:
        raise UnsafeURLError("Invalid URL") from exc


def validate_url_dns(url: str, resolver: Resolver = socket.getaddrinfo) -> str:
    canonical = validate_url_syntax(url)
    host = urlsplit(canonical).hostname or ""
    try:
        results = resolver(host, None, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise UnsafeURLError("Hostname could not be resolved safely") from exc
    addresses = {item[4][0] for item in results}
    if not addresses or any(_is_unsafe_ip(address) for address in addresses):
        raise UnsafeURLError("Hostname resolves to a private or non-public address")
    return canonical


def registered_domain(url: str) -> str:
    host = urlsplit(url).hostname or ""
    result = _TLD_EXTRACT(host, include_psl_private_domains=True)
    return result.top_domain_under_public_suffix


def is_same_site(candidate: str, seed: str, allow_subdomains: bool = False) -> bool:
    candidate_host = (urlsplit(candidate).hostname or "").lower()
    seed_host = (urlsplit(seed).hostname or "").lower()
    if not allow_subdomains:
        return candidate_host == seed_host
    return registered_domain(candidate) == registered_domain(seed) and bool(registered_domain(seed))
