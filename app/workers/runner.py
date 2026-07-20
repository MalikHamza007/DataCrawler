from __future__ import annotations

import argparse
import logging
import os
import socket
import sys
import time
import uuid

from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal, engine
from app.services.collection_jobs import (
    claim_next_job,
    finalize_cancelled_job,
    finalize_completed_job,
    recover_stale_jobs,
    schedule_retry_or_fail,
)
from app.services.worker_leases import WorkerLeaseActiveError, acquire_worker_lease, release_worker_lease, renew_worker_lease
from app.workers.context import JobExecutionContext
from app.workers.exceptions import JobCancellationRequested
from app.workers.classification_handler import ClassificationAnalysisJobHandler
from app.workers.duplicate_scan_handler import DuplicateScanJobHandler
from app.workers.export_handler import ExportGenerationJobHandler
from app.workers.places_handler import TERMINAL_EXCEPTIONS, PlacesDiscoveryJobHandler
from app.workers.signals import ShutdownFlag, install_signal_handlers
from app.workers.website_handler import WEBSITE_TERMINAL_EXCEPTIONS, WebsiteEnrichmentJobHandler

logger = logging.getLogger(__name__)


class LocalWorker:
    def __init__(self, *, settings: Settings | None = None, session_factory: sessionmaker = SessionLocal) -> None:
        self.settings = settings or get_settings()
        self.session_factory = session_factory
        self.owner_id = f"{self.settings.worker_name}:{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:12]}"
        self.hostname = socket.gethostname()
        self.process_id = os.getpid()
        self.handlers = {
            "places_discovery": PlacesDiscoveryJobHandler(session_factory=session_factory, settings=self.settings),
            "website_enrichment": WebsiteEnrichmentJobHandler(session_factory=session_factory, settings=self.settings),
            "classification_analysis": ClassificationAnalysisJobHandler(session_factory=session_factory, settings=self.settings),
            "duplicate_scan": DuplicateScanJobHandler(session_factory=session_factory, settings=self.settings),
            "export_generation": ExportGenerationJobHandler(session_factory=session_factory, settings=self.settings),
        }

    def start(self, *, once: bool = False, job_id: int | None = None) -> int:
        flag = ShutdownFlag()
        install_signal_handlers(flag)
        logger.info("Alduor local collector starting")
        with self.session_factory() as db:
            acquire_worker_lease(
                db,
                lease_name=self.settings.worker_name,
                owner_id=self.owner_id,
                hostname=self.hostname,
                process_id=self.process_id,
                settings=self.settings,
            )
            recovered = recover_stale_jobs(db, self.settings)
            logger.info("Worker lease acquired; recovered %s stale jobs", recovered)
        try:
            while not flag.requested:
                with self.session_factory() as db:
                    renew_worker_lease(db, lease_name=self.settings.worker_name, owner_id=self.owner_id, settings=self.settings)
                    job = claim_next_job(db, worker_id=self.owner_id, settings=self.settings, job_id=job_id)
                    claimed_job_id = job.id if job else None
                    claimed_job_type = job.job_type if job else None
                if claimed_job_id is None:
                    if once or job_id is not None:
                        return 0
                    self._sleep(flag)
                    continue
                self.process_job(claimed_job_id, claimed_job_type or "")
                if once or job_id is not None:
                    return 0
            return 0
        finally:
            with self.session_factory() as db:
                release_worker_lease(db, lease_name=self.settings.worker_name, owner_id=self.owner_id)
            engine.dispose()
            logger.info("Worker lease released")

    def process_job(self, job_id: int, job_type: str) -> None:
        handler = self.handlers.get(job_type)
        if handler is None:
            with self.session_factory() as db:
                schedule_retry_or_fail(db, job_id=job_id, worker_id=self.owner_id, exc=RuntimeError("Unsupported job type"), retryable=False, settings=self.settings)
            return
        context = JobExecutionContext(session_factory=self.session_factory, job_id=job_id, worker_id=self.owner_id, settings=self.settings)
        try:
            context.log("info", "Job started", {"job_type": job_type})
            result = handler.execute(job_id, context)
            with self.session_factory() as db:
                finalize_completed_job(db, job_id=job_id, worker_id=self.owner_id, summary=result)
        except JobCancellationRequested:
            with self.session_factory() as db:
                finalize_cancelled_job(db, job_id=job_id, worker_id=self.owner_id)
        except TERMINAL_EXCEPTIONS + WEBSITE_TERMINAL_EXCEPTIONS as exc:
            with self.session_factory() as db:
                schedule_retry_or_fail(db, job_id=job_id, worker_id=self.owner_id, exc=exc, retryable=False, settings=self.settings)
        except Exception as exc:
            logger.exception("Retryable worker job failure")
            with self.session_factory() as db:
                schedule_retry_or_fail(db, job_id=job_id, worker_id=self.owner_id, exc=exc, retryable=True, settings=self.settings)

    def _sleep(self, flag: ShutdownFlag) -> None:
        deadline = time.monotonic() + self.settings.worker_poll_interval_seconds
        while not flag.requested and time.monotonic() < deadline:
            time.sleep(min(0.25, deadline - time.monotonic()))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Alduor local collection worker.")
    parser.add_argument("--once", action="store_true", help="Process at most one eligible job and exit.")
    parser.add_argument("--job-id", type=int, default=None, help="Process one specific eligible job.")
    parser.add_argument("--poll-interval", type=float, default=None, help="Override worker poll interval in seconds.")
    parser.add_argument("--log-level", default="INFO", help="Python logging level.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging()
    logging.getLogger().setLevel(args.log_level.upper())
    settings = get_settings()
    if args.poll_interval is not None:
        settings.worker_poll_interval_seconds = args.poll_interval
    try:
        return LocalWorker(settings=settings).start(once=args.once, job_id=args.job_id)
    except WorkerLeaseActiveError as exc:
        logger.error(str(exc))
        return 2
    except Exception:
        logger.exception("Worker failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
