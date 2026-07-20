from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from app.collectors.websites.crawler import WebsiteCrawler
from app.collectors.websites.exceptions import RobotsBlockedError, SeedFetchError, UnsafeURLError, UnsupportedContentError
from app.core.config import Settings
from app.db.base import utc_now
from app.models.website_crawl import WebsiteCrawl
from app.workers.context import JobExecutionContext
from app.workers.exceptions import JobCancellationRequested
from sqlalchemy import select


class WebsiteEnrichmentJobHandler:
    def __init__(self, *, session_factory: sessionmaker, settings: Settings, crawler: WebsiteCrawler | None = None) -> None:
        self.session_factory = session_factory
        self.crawler = crawler or WebsiteCrawler(session_factory=session_factory, settings=settings)

    def execute(self, job_id: int, context: JobExecutionContext) -> dict:
        try:
            return self.crawler.run(job_id, progress=context.update_progress, cancellation_check=context.check_cancelled)
        except JobCancellationRequested:
            self._finalize_crawl(job_id, "cancelled")
            raise
        except Exception as exc:
            self._finalize_crawl(job_id, "failed", str(exc))
            raise

    def _finalize_crawl(self, job_id: int, status: str, error: str | None = None) -> None:
        with self.session_factory() as db:
            crawl = db.scalar(select(WebsiteCrawl).where(WebsiteCrawl.collection_job_id == job_id))
            if crawl and crawl.status != "blocked_by_robots":
                crawl.status = status
                crawl.error_message = error
                crawl.completed_at = utc_now()
                db.commit()


WEBSITE_TERMINAL_EXCEPTIONS = (UnsafeURLError, RobotsBlockedError, SeedFetchError, UnsupportedContentError)
