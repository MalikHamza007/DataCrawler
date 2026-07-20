from __future__ import annotations

import heapq
import time
from datetime import timedelta
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.collectors.websites.canonicalization import canonicalize_url
from app.collectors.websites.client import WebsiteClient
from app.collectors.websites.exceptions import RobotsBlockedError, SeedFetchError, TemporaryWebsiteError
from app.collectors.websites.page_priority import prioritize_links, score_link
from app.collectors.websites.parser import content_hash, parse_html, should_use_playwright
from app.collectors.websites.persistence import persist_page_facts
from app.collectors.websites.playwright_renderer import PlaywrightRenderer
from app.collectors.websites.robots import is_allowed, parse_robots
from app.collectors.websites.security import is_same_site, validate_url_dns
from app.collectors.websites.sitemap import parse_sitemap
from app.collectors.websites.types import RobotsResult
from app.core.config import Settings
from app.db.base import utc_now
from app.models.collection_job import CollectionJob
from app.models.website_crawl import WebsiteCrawl, WebsitePage

_ROBOTS_CACHE: dict[str, tuple[float, RobotsResult]] = {}


class WebsiteCrawler:
    def __init__(self, *, session_factory: sessionmaker, settings: Settings, client: WebsiteClient | None = None, renderer: PlaywrightRenderer | None = None, url_validator: callable = validate_url_dns) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.client = client or WebsiteClient(settings)
        self.renderer = renderer or PlaywrightRenderer(settings)
        self.url_validator = url_validator

    def run(self, job_id: int, *, progress: callable, cancellation_check: callable) -> dict:
        with self.session_factory() as db:
            job = db.get(CollectionJob, job_id)
            if not job or job.job_type != "website_enrichment":
                raise ValueError("Website enrichment job was not found")
            config = dict(job.search_config_json or {})
            crawl = db.scalar(select(WebsiteCrawl).where(WebsiteCrawl.collection_job_id == job_id))
            if not crawl:
                raise ValueError("Website crawl record was not found")
            crawl.status = "running"; crawl.started_at = crawl.started_at or utc_now(); db.commit()
            crawl_id = crawl.id; seed_url = crawl.canonical_seed_url
        cancellation_check()
        self.url_validator(seed_url)
        progress(phase="robots_check", message="Checking robots.txt")
        robots = self._fetch_robots(seed_url, config, cancellation_check)
        with self.session_factory() as db:
            crawl = db.get(WebsiteCrawl, crawl_id)
            crawl.robots_status = robots.status; crawl.robots_url = robots.robots_url; crawl.robots_fetched_at = utc_now(); crawl.robots_expires_at = utc_now() + timedelta(hours=self.settings.website_crawler_robots_cache_hours)
            if robots.warning: crawl.warning_message = robots.warning
            db.commit()
        if robots.status == "unreachable":
            self._block(crawl_id, "robots.txt was temporarily unreachable")
            raise RobotsBlockedError("robots.txt was temporarily unreachable; crawl denied")
        if not is_allowed(robots.rules, seed_url):
            self._block(crawl_id, "Seed URL is disallowed by robots.txt")
            raise RobotsBlockedError("Seed URL is disallowed by robots.txt")
        progress(phase="sitemap_discovery", message="Discovering relevant sitemap pages")
        self._discover_sitemaps(crawl_id, seed_url, robots, config, cancellation_check)
        summary = {key: 0 for key in ("pages_discovered", "pages_selected", "pages_fetched_static", "pages_rendered", "pages_blocked_by_robots", "pages_failed", "duplicate_content_pages", "developers_created", "projects_created", "projects_reused", "contacts_created", "social_profiles_created", "relationship_candidates_created", "evidence_records_created")}
        max_pages = min(int(config["max_pages"]), self.settings.website_crawler_max_pages_per_site)
        seen_hashes: set[str] = set()
        rendered = 0
        usable = 0
        while summary["pages_selected"] < max_pages:
            counts: dict[str, int] = {}
            cancellation_check()
            page_record = self._next_page(crawl_id)
            if not page_record:
                break
            summary["pages_selected"] += 1
            if not is_allowed(robots.rules, page_record.canonical_url):
                self._update_page(page_record.id, status="blocked_by_robots")
                summary["pages_blocked_by_robots"] += 1
                progress(phase="crawling", message=f"Skipped robots-blocked page {summary['pages_selected']} of {max_pages}", processed_delta=1)
                continue
            progress(phase="crawling", message=f"Fetching page {summary['pages_selected']} of {max_pages}")
            try:
                result = self.client.fetch(page_record.canonical_url, seed_url=seed_url, allow_subdomains=bool(config.get("allow_subdomains")), cancellation_check=cancellation_check)
                if page_record.depth == 0 and result.status_code >= 400:
                    raise SeedFetchError(f"Seed page returned HTTP {result.status_code}")
                if result.status_code >= 400:
                    raise TemporaryWebsiteError(f"Page returned HTTP {result.status_code}")
                parsed = parse_html(result.content.decode("utf-8", errors="replace"), result.url, max_links=self.settings.website_crawler_max_links_per_page, max_text_length=self.settings.website_crawler_max_text_length)
                method = "httpx"
                summary["pages_fetched_static"] += 1
                if config.get("use_playwright_fallback") and self.settings.website_crawler_enable_playwright and rendered < self.settings.website_crawler_playwright_max_pages and should_use_playwright(parsed):
                    cancellation_check(); progress(phase="rendering", message="Rendering JavaScript project page")
                    try:
                        html = self.renderer.render(result.url, seed_url=seed_url, allow_subdomains=bool(config.get("allow_subdomains")), cancellation_check=cancellation_check)
                        parsed = parse_html(html, result.url, max_links=self.settings.website_crawler_max_links_per_page, max_text_length=self.settings.website_crawler_max_text_length)
                        rendered += 1; summary["pages_rendered"] += 1; method = "playwright"
                    except Exception as exc:
                        self._warn(crawl_id, f"Playwright fallback failed: {exc}")
                digest = content_hash(parsed.text)
                if digest in seen_hashes:
                    self._update_page(page_record.id, status="duplicate_content", http_status=result.status_code, content_type=result.content_type, fetch_method=method, content_hash=digest)
                    summary["duplicate_content_pages"] += 1
                else:
                    seen_hashes.add(digest); usable += 1
                    progress(phase="extracting", message="Extracting public business information")
                    with self.session_factory() as db:
                        crawl = db.get(WebsiteCrawl, crawl_id)
                        counts = persist_page_facts(db, crawl=crawl, page=parsed, excerpt_limit=self.settings.website_crawler_max_evidence_excerpt_length)
                    for key, value in counts.items(): summary[key] += value
                    self._update_page(page_record.id, status="parsed", http_status=result.status_code, content_type=result.content_type, fetch_method=method, title=parsed.title, meta_description=parsed.description, canonical_tag=parsed.canonical_tag, etag=result.headers.get("etag"), last_modified=result.headers.get("last-modified"), content_hash=digest, text_length=len(parsed.text), word_count=len(parsed.text.split()), fetched_at=utc_now())
                    self._enqueue_links(crawl_id, parsed, page_record.depth + 1, seed_url, bool(config.get("allow_subdomains")), robots.rules)
                progress(phase="crawling", message=f"Processed page {summary['pages_selected']} of {max_pages}", processed_delta=1, created_delta=sum(counts.get(k, 0) for k in ("developers_created", "projects_created", "contacts_created", "social_profiles_created")))
            except RobotsBlockedError:
                raise
            except Exception as exc:
                self._update_page(page_record.id, status="failed", error_type=exc.__class__.__name__, error_message=str(exc))
                summary["pages_failed"] += 1
                progress(phase="crawling", message="Page failed; continuing crawl", processed_delta=1, failed_delta=1)
                if page_record.depth == 0:
                    raise SeedFetchError(str(exc)) from exc
        if usable == 0:
            raise SeedFetchError("No usable page could be fetched")
        summary["pages_discovered"] = self._finalize(crawl_id, summary)
        progress(phase="finalizing", message="Finalizing website evidence")
        return summary

    def _fetch_robots(self, seed_url: str, config: dict, cancellation_check: callable) -> RobotsResult:
        parts = urlsplit(seed_url); url = urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
        if not self.settings.website_crawler_respect_robots:
            return RobotsResult("disabled", url, None)
        cached = _ROBOTS_CACHE.get(url)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        try:
            response = self.client.fetch(url, seed_url=seed_url, allow_subdomains=bool(config.get("allow_subdomains")), cancellation_check=cancellation_check, allowed_content_types={"text/plain", "text/html", "application/octet-stream"})
        except Exception as exc:
            return RobotsResult("unreachable", url, None, warning=str(exc))
        if 400 <= response.status_code < 500:
            return RobotsResult("unavailable", url, None)
        if response.status_code >= 500:
            return RobotsResult("unreachable", url, None)
        rules, sitemaps = parse_robots(response.content.decode("utf-8", errors="replace"), self.settings.website_crawler_user_agent)
        result = RobotsResult("fetched", response.url, rules, sitemaps)
        _ROBOTS_CACHE[url] = (time.monotonic() + self.settings.website_crawler_robots_cache_hours * 3600, result)
        return result

    def _discover_sitemaps(self, crawl_id: int, seed_url: str, robots: RobotsResult, config: dict, cancellation_check: callable) -> None:
        parts = urlsplit(seed_url)
        candidates = list(robots.sitemaps) + [urlunsplit((parts.scheme, parts.netloc, path, "", "")) for path in ("/sitemap.xml", "/sitemap_index.xml", "/wp-sitemap.xml")]
        visited: set[str] = set()
        urls: list[str] = []
        while candidates and len(visited) < self.settings.website_crawler_max_sitemaps and len(urls) < self.settings.website_crawler_max_sitemap_urls:
            cancellation_check(); sitemap_url = canonicalize_url(candidates.pop(0))
            if sitemap_url in visited or not is_same_site(sitemap_url, seed_url, bool(config.get("allow_subdomains"))): continue
            visited.add(sitemap_url)
            try:
                response = self.client.fetch(sitemap_url, seed_url=seed_url, allow_subdomains=bool(config.get("allow_subdomains")), cancellation_check=cancellation_check, allowed_content_types={"application/xml", "text/xml", "application/x-gzip", "application/gzip", "text/plain"})
                found, nested = parse_sitemap(response.content, max_urls=self.settings.website_crawler_max_sitemap_urls - len(urls)); urls.extend(found); candidates.extend(nested)
            except Exception:
                continue
        for url in urls:
            try:
                canonical = canonicalize_url(url)
                if is_same_site(canonical, seed_url, bool(config.get("allow_subdomains"))) and is_allowed(robots.rules, canonical) and score_link(canonical) >= 50:
                    self._add_page(crawl_id, canonical, None, 1, score_link(canonical))
            except Exception:
                continue

    def _enqueue_links(self, crawl_id: int, parsed: object, depth: int, seed_url: str, allow_subdomains: bool, rules: object) -> None:
        if depth > self.settings.website_crawler_max_depth: return
        for link in prioritize_links(parsed.links, self.settings.website_crawler_max_links_per_page):
            if is_same_site(link.url, seed_url, allow_subdomains) and is_allowed(rules, link.url):
                self._add_page(crawl_id, link.url, parsed.url, depth, link.priority)

    def _add_page(self, crawl_id: int, url: str, parent: str | None, depth: int, priority: int) -> None:
        with self.session_factory() as db:
            if not db.scalar(select(WebsitePage).where(WebsitePage.website_crawl_id == crawl_id, WebsitePage.canonical_url == url)):
                db.add(WebsitePage(website_crawl_id=crawl_id, url=url, canonical_url=url, parent_url=parent, depth=depth, priority_score=priority, status="queued"))
                crawl = db.get(WebsiteCrawl, crawl_id); crawl.pages_discovered += 1; crawl.pages_queued += 1; db.commit()

    def _next_page(self, crawl_id: int) -> WebsitePage | None:
        with self.session_factory() as db:
            page = db.scalar(select(WebsitePage).where(WebsitePage.website_crawl_id == crawl_id, WebsitePage.status == "queued").order_by(WebsitePage.priority_score.desc(), WebsitePage.id).limit(1))
            if not page: return None
            page.status = "fetched"; db.commit(); db.refresh(page); db.expunge(page); return page

    def _update_page(self, page_id: int, **values: object) -> None:
        with self.session_factory() as db:
            page = db.get(WebsitePage, page_id)
            for key, value in values.items(): setattr(page, key, value)
            db.commit()

    def _warn(self, crawl_id: int, message: str) -> None:
        with self.session_factory() as db:
            crawl = db.get(WebsiteCrawl, crawl_id); crawl.warning_message = "\n".join(filter(None, [crawl.warning_message, message])); db.commit()

    def _block(self, crawl_id: int, message: str) -> None:
        with self.session_factory() as db:
            crawl = db.get(WebsiteCrawl, crawl_id); crawl.status = "blocked_by_robots"; crawl.error_message = message; crawl.completed_at = utc_now(); db.commit()

    def _finalize(self, crawl_id: int, summary: dict) -> int:
        with self.session_factory() as db:
            crawl = db.get(WebsiteCrawl, crawl_id)
            crawl.pages_fetched = summary["pages_fetched_static"]; crawl.pages_failed = summary["pages_failed"]; crawl.pages_skipped = summary["pages_blocked_by_robots"] + summary["duplicate_content_pages"]
            crawl.playwright_pages = summary["pages_rendered"]; crawl.projects_discovered = summary["projects_created"] + summary["projects_reused"]; crawl.developers_discovered = summary["developers_created"]; crawl.contacts_discovered = summary["contacts_created"]; crawl.social_profiles_discovered = summary["social_profiles_created"]
            warnings = bool(crawl.warning_message or crawl.pages_failed or crawl.pages_skipped or crawl.pages_discovered > summary["pages_selected"])
            crawl.status = "completed_with_warnings" if warnings else "completed"; crawl.completed_at = utc_now(); count = crawl.pages_discovered; db.commit(); return count
