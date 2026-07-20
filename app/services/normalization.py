from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit


def normalize_name(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip().lower()
    text = re.sub(r"[().,]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_url(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return text
    parts = urlsplit(text)
    netloc = parts.netloc.lower()
    path = parts.path.rstrip("/") if parts.path != "/" else ""
    return urlunsplit((parts.scheme.lower(), netloc, path, parts.query, parts.fragment))


def normalize_contact_value(value: str, contact_type: str) -> str:
    text = value.strip()
    if contact_type == "email":
        return text.lower()
    if contact_type in {"phone", "mobile", "whatsapp", "landline"}:
        return re.sub(r"[\s().-]+", "", text)
    if contact_type == "address":
        return normalize_name(text) or text
    return text
