from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from app.collectors.websites.types import ExtractedFact

PLATFORMS = {
    "facebook.com": "facebook", "instagram.com": "instagram", "x.com": "x", "twitter.com": "x",
    "linkedin.com": "linkedin", "youtube.com": "youtube", "youtu.be": "youtube", "tiktok.com": "tiktok",
}
REJECTED = ("/sharer", "/share", "/intent/", "/login", "/oauth", "/dialog/", "/home")


def extract_social_links(links: list[tuple[str, str]]) -> list[ExtractedFact]:
    facts: list[ExtractedFact] = []
    seen: set[tuple[str, str]] = set()
    for href, label in links:
        parts = urlsplit(href)
        host = (parts.hostname or "").lower().removeprefix("www.")
        platform = next((value for domain, value in PLATFORMS.items() if host == domain or host.endswith("." + domain)), None)
        path = parts.path.rstrip("/")
        if not platform or not path or path == "/" or any(marker in path.lower() for marker in REJECTED):
            continue
        if platform == "linkedin" and not path.lower().startswith(("/company/", "/showcase/")):
            continue
        normalized = urlunsplit(("https", host, path, "", ""))
        key = (platform, normalized)
        if key not in seen:
            seen.add(key)
            facts.append(ExtractedFact(f"official_{platform}", normalized, label or normalized, metadata={"platform": platform}))
    return facts
