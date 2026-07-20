from __future__ import annotations

import csv
import json
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.db.session import make_engine
from app.models import Contact, Developer, Project, SourceEvidence
from app.models.collection_job import CollectionJob
from app.models.project_developer_relationship import ProjectDeveloperRelationship
from app.models.project_discovery import ProjectDiscovery
from app.schemas.export import ExportCreateRequest
from app.services.exports import create_export, export_root, generate_export_artifact, safe_artifact_path
from app.services.refinement import REFINEMENT_SCHEMA_VERSION, build_refined_records, finalize_refinement, queue_refinement, refined_project_ids


def _db(tmp_path: Path):
    engine = make_engine(f"sqlite:///{tmp_path / 'refinement.db'}")
    Base.metadata.create_all(bind=engine)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return engine, sessions


def _seed(db):
    search_job = CollectionJob(job_type="places_discovery", status="completed", city="Lahore", search_config_json={})
    wrong_identity = Developer(name="Autograph Luxury Apartments", normalized_name="autograph luxury apartments", website_url="https://autograph.com")
    project = Project(
        name="Autograph Luxury Apartments",
        normalized_name="autograph luxury apartments",
        address="Main Boulevard, Gulberg III, Lahore",
        latitude=31.5101,
        longitude=74.3441,
        google_place_id="place-123",
        google_maps_url="https://maps.google.com/?q=place-123",
        official_website_url="https://autograph.com",
    )
    db.add_all([search_job, wrong_identity, project])
    db.flush()
    discovery = ProjectDiscovery(
        project_id=project.id,
        collection_job_id=search_job.id,
        source_method="text_search",
        source_query="apartment project in Lahore",
        google_primary_type="apartment_building",
        google_types_json=["apartment_building"],
    )
    evidence = SourceEvidence(
        developer_id=wrong_identity.id,
        project_id=project.id,
        collection_job_id=search_job.id,
        source_type="project_website",
        source_url="https://autograph.com/about",
        captured_text="Autograph has been developed by Concept Developers, a trusted Lahore developer.",
        field_name="developer_relationship",
        extracted_value="Autograph -> Concept Developers",
    )
    db.add_all([discovery, evidence])
    db.flush()
    relationship = ProjectDeveloperRelationship(
        project_id=project.id,
        developer_id=wrong_identity.id,
        relationship_type="developer",
        status="candidate",
        source_evidence_id=evidence.id,
        source_url="https://autograph.com/about",
        evidence_text="Autograph has been developed by Concept Developers, a trusted Lahore developer.",
    )
    db.add_all(
        [
            relationship,
            Contact(project_id=project.id, contact_type="phone", value="+92 300 1234567", normalized_value="+923001234567", is_primary=True, source_url="https://autograph.com/contact"),
            Contact(project_id=project.id, contact_type="email", value="sales@autograph.com", normalized_value="sales@autograph.com", is_primary=True, source_url="https://autograph.com/contact"),
        ]
    )
    db.commit()
    return project


def test_refiner_repairs_explicit_developer_and_builds_complete_record(tmp_path):
    _, sessions = _db(tmp_path)
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'refinement.db'}")
    with sessions() as db:
        project = _seed(db)
        summary = finalize_refinement(db, settings)
        db.refresh(project)
        assert summary["developer_identities_repaired"] == 1
        assert summary["relationships_auto_verified"] == 1
        assert summary["developer_contacts_copied"] == 2
        assert project.developer.name == "Concept Developers"
        assert refined_project_ids(db) == [project.id]
        record = build_refined_records(db)[0]
        assert record["developer_phone"] == "+92 300 1234567"
        assert record["developer_email"] == "sales@autograph.com"
        assert record["address"] == "Main Boulevard, Gulberg III, Lahore"


def test_refined_csv_and_json_are_minimal_and_complete(tmp_path):
    _, sessions = _db(tmp_path)
    settings = Settings(export_directory=str(tmp_path / "exports"), database_url=f"sqlite:///{tmp_path / 'refinement.db'}")
    with sessions() as db:
        project = _seed(db)
        finalize_refinement(db, settings)
        for fmt in ("csv", "json"):
            artifact = create_export(db, ExportCreateRequest(format=fmt, scope="refined_projects", filename_label="clean projects"), settings)
            db.commit()
            generate_export_artifact(db, artifact.id, settings)
            db.commit()
            path = safe_artifact_path(export_root(settings), artifact.internal_filename)
            if fmt == "csv":
                with path.open("r", encoding=settings.export_csv_encoding, newline="") as handle:
                    rows = list(csv.DictReader(handle))
                assert len(rows) == 1
                assert rows[0]["Project ID"] == str(project.id)
                assert rows[0]["Developer Name"] == "Concept Developers"
                assert rows[0]["Developer Email"] == "sales@autograph.com"
            else:
                payload = json.loads(path.read_text(encoding="utf-8"))
                assert payload["schema_version"] == REFINEMENT_SCHEMA_VERSION
                assert len(payload["projects"]) == 1
                assert payload["projects"][0]["developer"]["phone"] == "+92 300 1234567"
                assert payload["projects"][0]["location"]["latitude"] == 31.5101


def test_prepare_clean_data_queues_enrichment_before_final_refinement(tmp_path):
    _, sessions = _db(tmp_path)
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'refinement.db'}",
        refinement_max_websites=5,
        refinement_max_pages_per_website=3,
    )
    with sessions() as db:
        _seed(db)
        job, summary = queue_refinement(db, settings)
        jobs = list(db.query(CollectionJob).order_by(CollectionJob.id).all())
        website_jobs = [item for item in jobs if item.job_type == "website_enrichment"]
        assert summary["website_jobs_queued"] == 1
        assert len(website_jobs) == 1
        assert website_jobs[0].id < job.id
        assert job.job_type == "classification_analysis"
        assert job.search_config_json["refine_clean_data"] is True
