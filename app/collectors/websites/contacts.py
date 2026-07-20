from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlsplit

import phonenumbers
from email_validator import EmailNotValidError, validate_email

from app.collectors.websites.types import ExtractedFact

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+92|0092|0)?[\s().-]*(?:\d[\s().-]*){9,11}(?!\d)")
BAD_EMAIL_PREFIXES = ("noreply@", "no-reply@", "example@", "test@", "wordpress@")


def normalize_phone(value: str) -> str | None:
    try:
        parsed = phonenumbers.parse(value, "PK")
        if not phonenumbers.is_possible_number(parsed):
            return None
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        return None


def extract_contacts(text: str, links: list[tuple[str, str]], max_emails: int = 20, max_phones: int = 30) -> list[ExtractedFact]:
    facts: list[ExtractedFact] = []
    emails = set(EMAIL_RE.findall(text))
    for href, _ in links:
        if href.lower().startswith("mailto:"):
            emails.add(unquote(href[7:].split("?", 1)[0]))
    for email in sorted(emails):
        lowered = email.lower()
        if lowered.startswith(BAD_EMAIL_PREFIXES):
            continue
        try:
            normalized = validate_email(email, check_deliverability=False).normalized
        except EmailNotValidError:
            continue
        facts.append(ExtractedFact("business_email", normalized, email, metadata={"normalized_value": normalized, "contact_type": "email"}))
        if len([f for f in facts if f.field_name == "business_email"]) >= max_emails:
            break
    phones: dict[str, str] = {}
    for displayed in PHONE_RE.findall(text):
        normalized = normalize_phone(displayed)
        phones.setdefault(normalized or re.sub(r"\D", "", displayed), displayed.strip())
    for href, label in links:
        lower = href.lower()
        if lower.startswith("tel:"):
            displayed = unquote(href[4:].split("?", 1)[0])
            normalized = normalize_phone(displayed)
            phones.setdefault(normalized or re.sub(r"\D", "", displayed), label.strip() or displayed)
        if "wa.me/" in lower or "api.whatsapp.com" in lower or lower.startswith("whatsapp://"):
            number = urlsplit(href).path.strip("/") if "wa.me/" in lower else parse_qs(urlsplit(href).query).get("phone", [""])[0]
            normalized = normalize_phone("+" + number.lstrip("+"))
            facts.append(ExtractedFact("whatsapp", href, label or href, metadata={"normalized_value": normalized, "contact_type": "whatsapp", "displayed_value": number}))
    for normalized, displayed in list(phones.items())[:max_phones]:
        facts.append(ExtractedFact("sales_phone", displayed, displayed, metadata={"normalized_value": normalized or None, "contact_type": "phone"}))
    address_match = re.search(r"(?:office|address|head office)\s*[:\-]?\s*([^\n]{10,250})", text, re.I)
    if address_match:
        value = address_match.group(1).strip()
        facts.append(ExtractedFact("office_address", value, address_match.group(0), metadata={"contact_type": "address"}))
    return facts
