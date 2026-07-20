from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import phonenumbers
from rapidfuzz import fuzz

from app.collectors.websites.security import registered_domain

LEGAL_SUFFIXES = {"private", "pvt", "limited", "ltd", "company", "co", "incorporated", "inc"}
TRACKING = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}


def normalize_name_storage(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold().replace("&", " and ")
    return re.sub(r"\s+", " ", re.sub(r"[^\w]+", " ", text)).strip()


def normalize_name_matching(value: str) -> str:
    return " ".join(token for token in normalize_name_storage(value).split() if token not in LEGAL_SUFFIXES)


def name_similarity(left: str, right: str) -> int:
    a, b = normalize_name_matching(left), normalize_name_matching(right)
    if not a or not b:
        return 0
    return round(0.50 * fuzz.WRatio(a, b) + 0.30 * fuzz.token_set_ratio(a, b) + 0.20 * fuzz.token_sort_ratio(a, b))


@dataclass(frozen=True)
class PhoneValue:
    original: str
    possible: bool
    valid: bool
    country_code: int | None
    national_number: str | None
    e164: str | None
    international: str | None
    national: str | None
    extension: str | None


def normalize_phone(value: str) -> PhoneValue:
    cleaned = re.sub(r"^00", "+", value.strip())
    try:
        parsed = phonenumbers.parse(cleaned, "PK")
        possible, valid = phonenumbers.is_possible_number(parsed), phonenumbers.is_valid_number(parsed)
        return PhoneValue(value, possible, valid, parsed.country_code, str(parsed.national_number), phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164) if possible else None, phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL) if possible else None, phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL) if possible else None, parsed.extension or None)
    except phonenumbers.NumberParseException:
        return PhoneValue(value, False, False, None, None, None, None, None, None)


def phone_match(left: str, right: str) -> str:
    a, b = normalize_phone(left), normalize_phone(right)
    if a.valid and b.valid and a.e164 == b.e164:
        return "exact_valid_e164"
    if a.possible and b.possible and a.country_code == b.country_code and a.national_number == b.national_number:
        return "exact_possible_number"
    if a.national_number and b.national_number and a.national_number[-7:] == b.national_number[-7:]:
        return "partial_last_digits"
    return "unparseable" if not a.possible or not b.possible else "different"


def normalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    host = (parts.hostname or "").encode("idna").decode("ascii").lower()
    if host.startswith("www."):
        host = host[4:]
    port = parts.port
    netloc = host if not port or (parts.scheme.lower() == "http" and port == 80) or (parts.scheme.lower() == "https" and port == 443) else f"{host}:{port}"
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.casefold() not in TRACKING))
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower() or "https", netloc, path, query, ""))


def domain(value: str) -> str:
    return registered_domain(normalize_url(value))


def normalize_social_url(value: str) -> str | None:
    normalized = normalize_url(value)
    parts = urlsplit(normalized)
    host = parts.hostname or ""
    path = parts.path.rstrip("/")
    rejected = ("/sharer", "/share", "/intent", "/status/", "/posts/", "/p/", "/watch")
    if any(item in path.casefold() for item in rejected) or not path:
        return None
    host = host.removeprefix("m.").removeprefix("www.")
    return urlunsplit(("https", host, path, "", ""))


def normalize_address(value: str) -> str:
    text = normalize_name_storage(value)
    replacements = {r"\broad\b": "rd", r"\bstreet\b": "st", r"\bboulevard\b": "blvd", r"\bgulberg\s+(?:iii|3rd)\b": "gulberg 3"}
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)
    return re.sub(r"\s+", " ", text).strip()


def address_similarity(left: str, right: str) -> int:
    return round(fuzz.token_set_ratio(normalize_address(left), normalize_address(right)))


def haversine_meters(lat1: float | None, lon1: float | None, lat2: float | None, lon2: float | None) -> float | None:
    if None in (lat1, lon1, lat2, lon2):
        return None
    if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90 and -180 <= lon1 <= 180 and -180 <= lon2 <= 180):
        raise ValueError("Invalid coordinates")
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 6_371_000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
