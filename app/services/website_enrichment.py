from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.websites.exceptions import UnsafeURLError
from app.collectors.websites.security import registered_domain, validate_url_syntax
from app.core.config import Settings, get_settings
from app.core.exceptions import EntityNotFoundError
from app.models.collection_job import CollectionJob
from app.models.developer import Developer
from app.models.project import Project
from app.models.project_discovery import ProjectDiscovery
from app.models.source_evidence import SourceEvidence
from app.models.website_crawl import WebsiteCrawl, WebsitePage
from app.schemas.website_enrichment import ManualWebsiteEnrichmentRequest, WebsiteEnrichmentRequest, WebsitePreviewRequest


def preview(payload: WebsitePreviewRequest, settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    canonical = validate_url_syntax(payload.seed_url)
    parts = urlsplit(canonical)
    robots_url = urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
    return {"canonical_seed_url": canonical, "registered_domain": registered_domain(canonical), "robots_url": robots_url, "allowed_scheme": True, "ssrf_check": "passed_syntax_only", "estimated_limits": {"maximum_pages": settings.website_crawler_max_pages_per_site, "maximum_depth": settings.website_crawler_max_depth, "playwright_pages": settings.website_crawler_playwright_max_pages}}


def create_project_job(db: Session, project_id: int, payload: WebsiteEnrichmentRequest, settings: Settings | None = None) -> CollectionJob:
    project = db.get(Project, project_id)
    if not project:
        raise EntityNotFoundError(f"Project {project_id} was not found.")
    values = payload.model_dump()
    values["crawl_mode"] = "project_site"
    data = ManualWebsiteEnrichmentRequest(**values, project_id=project_id)
    return _create_job(db, data, settings)


def create_developer_job(db: Session, developer_id: int, payload: WebsiteEnrichmentRequest, settings: Settings | None = None) -> CollectionJob:
    developer = db.get(Developer, developer_id)
    if not developer:
        raise EntityNotFoundError(f"Developer {developer_id} was not found.")
    values = payload.model_dump()
    values["crawl_mode"] = "developer_site"
    data = ManualWebsiteEnrichmentRequest(**values, developer_id=developer_id)
    return _create_job(db, data, settings)


def create_manual_job(db: Session, payload: ManualWebsiteEnrichmentRequest, settings: Settings | None = None) -> CollectionJob:
    if payload.project_id is not None and not db.get(Project, payload.project_id):
        raise EntityNotFoundError(f"Project {payload.project_id} was not found.")
    if payload.developer_id is not None and not db.get(Developer, payload.developer_id):
        raise EntityNotFoundError(f"Developer {payload.developer_id} was not found.")
    return _create_job(db, payload, settings)


def queue_for_places_job(db: Session, parent_job_id: int, settings: Settings | None = None) -> list[int]:
    settings = settings or get_settings()
    if not settings.area_research_auto_enrich_websites or not settings.website_crawler_enabled:
        return []
    project_ids = list(dict.fromkeys(db.scalars(select(ProjectDiscovery.project_id).where(ProjectDiscovery.collection_job_id == parent_job_id)).all()))
    queued: list[int] = []
    queued_urls: set[str] = set()
    for project_id in project_ids:
        if len(queued) >= settings.area_research_max_websites:
            break
        project = db.get(Project, project_id)
        if not project or not project.official_website_url:
            continue
        try:
            canonical_url = validate_url_syntax(project.official_website_url)
        except (UnsafeURLError, ValueError):
            continue
        if canonical_url in queued_urls:
            continue
        existing = [
            item for item in db.scalars(select(CollectionJob).where(CollectionJob.job_type == "website_enrichment")).all()
            if (item.search_config_json or {}).get("parent_collection_job_id") == parent_job_id
            and (item.search_config_json or {}).get("project_id") == project_id
        ]
        if existing:
            continue
        child = create_project_job(
            db,
            project_id,
            WebsiteEnrichmentRequest(
                seed_url=project.official_website_url,
                max_pages=min(settings.area_research_max_pages_per_website, settings.website_crawler_max_pages_per_site),
                use_playwright_fallback=True,
                crawl_mode="project_site",
            ),
            settings,
        )
        config = dict(child.search_config_json or {})
        config["parent_collection_job_id"] = parent_job_id
        child.search_config_json = config
        db.commit()
        queued_urls.add(canonical_url)
        queued.append(child.id)
    return queued


def _create_job(db: Session, payload: ManualWebsiteEnrichmentRequest, settings: Settings | None) -> CollectionJob:
    settings = settings or get_settings()
    canonical = validate_url_syntax(payload.seed_url)
    max_pages = payload.max_pages or settings.website_crawler_max_pages_per_site
    if max_pages > settings.website_crawler_max_pages_per_site:
        raise ValueError("max_pages exceeds application configuration")
    config = payload.model_dump()
    config.update(seed_url=canonical, max_pages=max_pages, allow_subdomains=payload.allow_subdomains if payload.allow_subdomains is not None else settings.website_crawler_allow_subdomains)
    job = CollectionJob(job_type="website_enrichment", status="queued", city="Lahore", search_config_json=config, total_items=max_pages, progress_phase="queued", max_attempts=settings.worker_max_job_attempts)
    db.add(job)
    db.flush()
    crawl = WebsiteCrawl(collection_job_id=job.id, project_id=payload.project_id, developer_id=payload.developer_id, seed_url=payload.seed_url, canonical_seed_url=canonical, registered_domain=registered_domain(canonical), crawl_mode=payload.crawl_mode, status="queued", robots_url=_robots_url(canonical), pages_discovered=1, pages_queued=1)
    db.add(crawl)
    db.flush()
    db.add(WebsitePage(website_crawl_id=crawl.id, url=canonical, canonical_url=canonical, depth=0, priority_score=1000, status="queued"))
    db.commit()
    db.refresh(job)
    return job


def get_crawl(db: Session, crawl_id: int) -> WebsiteCrawl:
    crawl = db.get(WebsiteCrawl, crawl_id)
    if not crawl:
        raise EntityNotFoundError(f"Website crawl {crawl_id} was not found.")
    return crawl


def list_pages(db: Session, crawl_id: int) -> list[WebsitePage]:
    get_crawl(db, crawl_id)
    return list(db.scalars(select(WebsitePage).where(WebsitePage.website_crawl_id == crawl_id).order_by(WebsitePage.priority_score.desc(), WebsitePage.id)).all())


def list_evidence(db: Session, crawl_id: int) -> list[SourceEvidence]:
    crawl = get_crawl(db, crawl_id)
    return list(db.scalars(select(SourceEvidence).where(SourceEvidence.collection_job_id == crawl.collection_job_id).order_by(SourceEvidence.id)).all())


def _robots_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
