from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.collectors.websites.types import ExtractedFact

ORG_TYPES = {"Organization", "Corporation", "LocalBusiness"}
DIRECT_DEVELOPER_RE = re.compile(
    r"\b(?:developed\s+by|owned\s+and\s+developed\s+by|a\s+project\s+by)\s+"
    r"([A-Z][A-Za-z0-9&.'() -]{1,90}?(?:Developers?|Development|Properties|Group|Holdings|Limited|Ltd\.?|Pvt\.?\s+Ltd\.?))"
    r"(?=\s*(?:[,.;|]|\bis\b|\bhas\b|\bwith\b|$))",
    re.I,
)

# Names accepted here get stored as Developer records and shown to a real person doing
# outreach, so every signal (not just the footer) needs the same junk filter. Without
# this, a misconfigured og:site_name tag or an over-long JSON-LD "name" (a full page
# title, e.g. "The Skyscraper - Luxury Apartments in Lahore, Real Estate Investment")
# sails straight through and gets created as a "developer".
MAX_ORG_NAME_LENGTH = 60
JUNK_NAME_PATTERNS = re.compile(r"all rights reserved|copyright|©|\bhome\s*page\b|\bwelcome to\b", re.I)
TITLE_LIKE_SEPARATOR_RE = re.compile(r"\s[-|]\s.*\s[-|]\s|,.*,")


def _is_plausible_org_name(value: str) -> bool:
    if not value or len(value) < 3 or len(value) > MAX_ORG_NAME_LENGTH:
        return False
    if JUNK_NAME_PATTERNS.search(value):
        return False
    if TITLE_LIKE_SEPARATOR_RE.search(value):
        # More than one " - "/"|" or multiple commas usually means we captured a page
        # title or breadcrumb, not a company name (e.g. "X - Luxury Apartments, Lahore, PK")
        return False
    return True


def extract_organizations(soup: BeautifulSoup, jsonld: list[tuple[str, dict]]) -> list[ExtractedFact]:
    results: list[ExtractedFact] = []
    text = soup.get_text(" ", strip=True)
    for match in DIRECT_DEVELOPER_RE.finditer(text):
        value = re.sub(r"\s+", " ", match.group(1)).strip(" ,.;|-")
        results.append(ExtractedFact("developer_name", value, match.group(0), metadata={"signal": "explicit_developer_byline"}))
    for path, item in jsonld:
        types = item.get("@type", [])
        types = [types] if isinstance(types, str) else types
        if ORG_TYPES.intersection(types) and isinstance(item.get("name"), str):
            results.append(ExtractedFact("developer_name", item["name"].strip(), f"JSON-LD {path}: {item['name']}", metadata={"signal": "json_ld", "json_path": path}))
    og = soup.select_one('meta[property="og:site_name"]')
    if og and og.get("content"):
        value = str(og["content"]).strip()
        results.append(ExtractedFact("developer_name", value, value, metadata={"signal": "open_graph"}))
    footer = soup.find("footer")
    if footer:
        match = re.search(r"(?:©|copyright(?:\s+\d{4})?)\s*(?:\d{4}\s*)?([^.|\n]{3,100})", footer.get_text(" ", strip=True), re.I)
        if match:
            value = match.group(1).strip(" -|")
            results.append(ExtractedFact("developer_name", value, match.group(0), metadata={"signal": "footer"}))
    results = [result for result in results if _is_plausible_org_name(result.value)]
    unique: dict[str, ExtractedFact] = {}
    for result in results:
        unique.setdefault(result.value.casefold(), result)
    priority = {"explicit_developer_byline": 0, "json_ld": 1, "open_graph": 2, "footer": 3}
    return sorted(unique.values(), key=lambda item: priority.get(item.metadata.get("signal"), 99))
