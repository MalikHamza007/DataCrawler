from pathlib import Path

from sqlalchemy import select

from app.collectors.websites.parser import parse_html
from app.collectors.websites.persistence import persist_page_facts
from app.models.collection_job import CollectionJob
from app.models.developer import Developer
from app.models.project import Project
from app.models.project_developer_relationship import ProjectDeveloperRelationship
from app.models.source_evidence import SourceEvidence
from app.models.website_crawl import WebsiteCrawl

FIXTURES = Path(__file__).parent / "fixtures" / "websites" / "developer_site"


def test_persistence_creates_unverified_candidates_relationships_and_evidence(client):
    dependency = next(iter(client.app.dependency_overrides.values()))
    db = next(dependency())
    try:
        job = CollectionJob(job_type="website_enrichment", status="running", city="Lahore", search_config_json={})
        db.add(job); db.flush()
        crawl = WebsiteCrawl(collection_job_id=job.id, seed_url="https://developer.example/", canonical_seed_url="https://developer.example/", registered_domain="developer.example", crawl_mode="developer_site", status="running")
        db.add(crawl); db.commit(); db.refresh(crawl)
        identity = parse_html((FIXTURES / "index.html").read_text(), "https://developer.example/")
        portfolio = parse_html((FIXTURES / "projects.html").read_text(), "https://developer.example/projects")
        persist_page_facts(db, crawl=crawl, page=identity)
        counts = persist_page_facts(db, crawl=crawl, page=portfolio)
        projects = list(db.scalars(select(Project)).all())
        assert counts["projects_created"] == 2
        assert all(project.verification_status == "unverified" and project.developer_id is None for project in projects)
        assert {project.city for project in projects} == {"Lahore", "Unknown"}
        developer = db.scalar(select(Developer))
        assert developer and developer.classification == "uncertain" and developer.verification_status == "unverified"
        assert len(db.scalars(select(ProjectDeveloperRelationship)).all()) == 2
        assert all(item.status == "candidate" for item in db.scalars(select(ProjectDeveloperRelationship)).all())
        assert db.scalar(select(SourceEvidence).where(SourceEvidence.field_name == "developer_relationship"))
        before = len(db.scalars(select(SourceEvidence)).all())
        persist_page_facts(db, crawl=crawl, page=portfolio)
        assert len(db.scalars(select(SourceEvidence)).all()) == before
    finally:
        db.close()
