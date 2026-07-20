from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.collectors.websites.client import WebsiteClient
from app.collectors.websites.crawler import WebsiteCrawler
from app.core.config import Settings
from app.db.base import Base
from app.db.session import make_engine
from app.models.collection_job import CollectionJob
from app.models.project import Project
from app.models.project_developer_relationship import ProjectDeveloperRelationship
from app.models.source_evidence import SourceEvidence
from app.models.website_crawl import WebsiteCrawl, WebsitePage
from app.schemas.website_enrichment import ManualWebsiteEnrichmentRequest
from app.services.collection_jobs import claim_next_job
from app.services.website_enrichment import create_manual_job
from app.workers.runner import LocalWorker
from app.workers.website_handler import WebsiteEnrichmentJobHandler

FIXTURES = Path(__file__).parent / "fixtures" / "websites" / "developer_site"


def test_worker_processes_fixture_site_without_live_requests(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'worker.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    settings = Settings(database_url=str(engine.url), website_crawler_min_request_delay_ms=0, website_crawler_max_request_delay_ms=0, website_crawler_enable_playwright=False, website_crawler_max_pages_per_site=5, website_crawler_playwright_max_pages=0)
    routes = {
        "/robots.txt": (200, "text/plain", (FIXTURES / "robots.txt").read_bytes()),
        "/": (200, "text/html", (FIXTURES / "index.html").read_bytes()),
        "/projects": (200, "text/html", (FIXTURES / "projects.html").read_bytes()),
        "/contact": (200, "text/html", (FIXTURES / "contact.html").read_bytes()),
        "/sitemap.xml": (200, "application/xml", (FIXTURES / "sitemap.xml").read_bytes()),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        status, content_type, body = routes.get(request.url.path, (404, "text/plain", b"not found"))
        return httpx.Response(status, headers={"content-type": content_type}, content=body, request=request)

    validator = lambda url: url
    client = WebsiteClient(settings, transport=httpx.MockTransport(handler), validator=validator, sleeper=lambda _: None)
    crawler = WebsiteCrawler(session_factory=sessions, settings=settings, client=client, url_validator=validator)
    with sessions() as db:
        job = create_manual_job(db, ManualWebsiteEnrichmentRequest(seed_url="https://developer.example.com/", crawl_mode="developer_site", max_pages=5, use_playwright_fallback=False), settings)
    worker = LocalWorker(settings=settings, session_factory=sessions)
    worker.handlers["website_enrichment"] = WebsiteEnrichmentJobHandler(session_factory=sessions, settings=settings, crawler=crawler)
    with sessions() as db:
        claimed = claim_next_job(db, worker_id=worker.owner_id, settings=settings, job_id=job.id)
        assert claimed and claimed.job_type == "website_enrichment"
    worker.process_job(job.id, "website_enrichment")
    with sessions() as db:
        completed = db.get(CollectionJob, job.id)
        crawl = db.scalar(select(WebsiteCrawl).where(WebsiteCrawl.collection_job_id == job.id))
        projects = list(db.scalars(select(Project)).all())
        assert completed.status == "completed"
        assert crawl.status in {"completed", "completed_with_warnings"}
        assert crawl.robots_status == "fetched"
        assert len(projects) == 2 and all(project.developer_id is None for project in projects)
        assert len(db.scalars(select(ProjectDeveloperRelationship)).all()) == 2
        assert len(db.scalars(select(SourceEvidence)).all()) > 5
        assert all("facebook.com" not in page.canonical_url for page in db.scalars(select(WebsitePage)).all())
    client.close()
    engine.dispose()
