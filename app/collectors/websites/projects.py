from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.collectors.websites.types import ExtractedFact

WEAK_NAMES = {"learn more", "read more", "view project", "discover", "details", "coming soon", "click here", "projects", "our projects"}
LAHORE_TERMS = ("lahore", "gulberg", "dha lahore", "bahria town lahore", "raiwind road", "johar town", "lake city", "model town", "wapda town", "ferozepur road", "mall road", "jail road", "cantt lahore", "ring road lahore")


def extract_projects(soup: BeautifulSoup, jsonld: list[tuple[str, dict]], page_url: str) -> list[ExtractedFact]:
    candidates: list[ExtractedFact] = []
    selectors = ".project, .project-card, [class*='project-item'], [data-project], article"
    for card in soup.select(selectors):
        heading = card.find(["h1", "h2", "h3", "h4"])
        link = card.find("a", href=True)
        name = heading.get_text(" ", strip=True) if heading else (link.get_text(" ", strip=True) if link else "")
        if _valid_name(name):
            text = card.get_text(" ", strip=True)
            candidates.append(_fact(name, text, page_url, link.get("href") if link else None))
    for path, item in jsonld:
        types = item.get("@type", [])
        types = [types] if isinstance(types, str) else types
        if set(types).intersection({"Residence", "ApartmentComplex", "Product", "Place"}) and _valid_name(str(item.get("name", ""))):
            candidates.append(_fact(str(item["name"]), str(item.get("description") or item["name"]), page_url, item.get("url"), path))
        if "ItemList" in types:
            for entry in item.get("itemListElement", []):
                value = entry.get("item", entry) if isinstance(entry, dict) else {}
                if isinstance(value, dict) and _valid_name(str(value.get("name", ""))):
                    candidates.append(_fact(str(value["name"]), str(value.get("description") or value["name"]), page_url, value.get("url"), path))
    unique: dict[str, ExtractedFact] = {}
    for candidate in candidates:
        unique.setdefault(_normalize(candidate.value), candidate)
    return list(unique.values())


def _fact(name: str, text: str, page_url: str, detail_url: str | None, json_path: str | None = None) -> ExtractedFact:
    lowered = text.casefold()
    location = "confirmed_lahore" if "lahore" in lowered else ("probable_lahore" if any(term in lowered for term in LAHORE_TERMS[1:]) else "unknown_location")
    project_type = next((value for term, value in (("apartment", "apartments"), ("residential tower", "residential_tower"), ("mixed use", "mixed_use"), ("commercial", "commercial"), ("mall", "shopping_mall"), ("housing society", "housing_society"), ("villa", "villas")) if term in lowered), "unknown")
    status = next((value for term, value in (("under construction", "under_construction"), ("booking open", "booking_open"), ("upcoming", "upcoming"), ("completed", "completed"), ("delivered", "delivered"), ("sold out", "sold_out"), ("ongoing", "ongoing")) if term in lowered), "unknown")
    return ExtractedFact("project_name", name.strip(), text[:2000], metadata={"source_page_url": page_url, "detail_url": detail_url, "location_status": location, "project_type": project_type, "project_status": status, "json_path": json_path})


def _valid_name(name: str) -> bool:
    value = re.sub(r"\s+", " ", name).strip()
    return 2 < len(value) <= 255 and value.casefold() not in WEAK_NAMES


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.casefold()).strip()
