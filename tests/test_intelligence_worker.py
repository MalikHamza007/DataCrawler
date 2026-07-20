from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.db.session import make_engine
from app.models.collection_job import CollectionJob
from app.models.developer import Developer
from app.models.intelligence import ClassificationAssessment, DuplicateCandidate
from app.models.source_evidence import SourceEvidence
from app.services.collection_jobs import claim_next_job
from app.workers.runner import LocalWorker


def test_classification_and_duplicate_jobs_run_through_worker_without_network(tmp_path, monkeypatch):
    engine = make_engine(f"sqlite:///{tmp_path / 'intelligence.db'}"); Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    settings = Settings(database_url=str(engine.url), worker_supported_job_types=["classification_analysis", "duplicate_scan"])
    monkeypatch.setattr("httpx.Client.request", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("intelligence must not use network")))
    with sessions() as db:
        left = Developer(name="Alpha Developers", normalized_name="alpha developers", website_url="https://alpha.com", city="Lahore", country="Pakistan")
        right = Developer(name="Alpha Developers Pvt Ltd", normalized_name="alpha developers pvt ltd", website_url="https://www.alpha.com", city="Lahore", country="Pakistan")
        db.add_all([left, right]); db.flush()
        db.add(SourceEvidence(developer_id=left.id, source_type="official_website", source_url="https://alpha.com", captured_text="We are a property developer", field_name="description", extracted_value="property developer", verification_status="unverified"))
        classification_job = CollectionJob(job_type="classification_analysis", status="queued", city="Lahore", search_config_json={"entity_type": "developer", "entity_ids": [], "rule_version": "m6-v1"}, max_attempts=3)
        duplicate_job = CollectionJob(job_type="duplicate_scan", status="queued", city="Lahore", search_config_json={"entity_type": "developer", "minimum_score": 55, "rule_version": "m6-v1"}, max_attempts=3)
        db.add_all([classification_job, duplicate_job]); db.commit(); classification_id, duplicate_id = classification_job.id, duplicate_job.id
    worker = LocalWorker(settings=settings, session_factory=sessions)
    for job_id, job_type in ((classification_id, "classification_analysis"), (duplicate_id, "duplicate_scan")):
        with sessions() as db: assert claim_next_job(db, worker_id=worker.owner_id, settings=settings, job_id=job_id)
        worker.process_job(job_id, job_type)
    with sessions() as db:
        assert db.get(CollectionJob, classification_id).status == "completed"
        assert db.get(CollectionJob, duplicate_id).status == "completed"
        assert len(db.scalars(select(ClassificationAssessment)).all()) == 2
        assert len(db.scalars(select(DuplicateCandidate)).all()) == 1
    engine.dispose()
