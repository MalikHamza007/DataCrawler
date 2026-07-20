from __future__ import annotations

import hashlib
import re

from bs4 import BeautifulSoup, Comment

from app.collectors.websites.canonicalization import canonicalize_url
from app.collectors.websites.contacts import extract_contacts
from app.collectors.websites.jsonld import extract_jsonld
from app.collectors.websites.organization import extract_organizations
from app.collectors.websites.page_priority import score_link
from app.collectors.websites.projects import extract_projects
from app.collectors.websites.social_links import extract_social_links
from app.collectors.websites.types import LinkCandidate, ParsedPage


def parse_html(html: str, url: str, *, max_links: int = 200, max_text_length: int = 200_000) -> ParsedPage:
    soup = BeautifulSoup(html, "lxml")
    script_count = len(soup.find_all("script"))
    app_shell_markers = len(soup.select("#app, #root, #__next, [data-reactroot], [ng-version]"))
    jsonld = extract_jsonld(soup)
    for tag in soup(["script", "style", "noscript", "svg", "template", "iframe"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()
    raw_links: list[tuple[str, str]] = []
    links: list[LinkCandidate] = []
    for anchor in soup.find_all("a", href=True)[:max_links]:
        href = str(anchor["href"]).strip()
        label = anchor.get_text(" ", strip=True)
        raw_links.append((href, label))
        try:
            absolute = canonicalize_url(href, url)
        except ValueError:
            continue
        if absolute.startswith(("http://", "https://")):
            links.append(LinkCandidate(absolute, label, score_link(absolute, label)))
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:max_text_length]
    title = soup.title.get_text(" ", strip=True)[:500] if soup.title else None
    description_tag = soup.select_one('meta[name="description"]')
    canonical_tag = soup.select_one('link[rel~="canonical"]')
    facts = extract_contacts(text, raw_links) + extract_social_links(raw_links)
    organizations = extract_organizations(soup, jsonld)
    projects = extract_projects(soup, jsonld, url)
    return ParsedPage(
        url=url, title=title,
        description=str(description_tag.get("content"))[:2000] if description_tag and description_tag.get("content") else None,
        canonical_tag=canonicalize_url(str(canonical_tag.get("href")), url) if canonical_tag and canonical_tag.get("href") else None,
        text=text, links=links, facts=facts, organization_names=organizations, project_candidates=projects,
        script_count=script_count, app_shell_markers=app_shell_markers,
    )


def content_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip().casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def should_use_playwright(page: ParsedPage) -> bool:
    useful = len(page.facts) + len(page.organization_names) + len(page.project_candidates)
    return len(page.text) < 250 and useful == 0 and (page.script_count >= 3 or page.app_shell_markers > 0)
