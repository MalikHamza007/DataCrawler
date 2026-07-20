from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.websites.types import ExtractedFact, ParsedPage
from app.db.base import utc_now
from app.models.contact import Contact
from app.models.developer import Developer
from app.models.project import Project
from app.models.project_developer_relationship import ProjectDeveloperRelationship
from app.models.social_profile import SocialProfile
from app.models.source_evidence import SourceEvidence
from app.models.website_crawl import WebsiteCrawl
from app.services.normalization import normalize_contact_value, normalize_name, normalize_url


def persist_page_facts(db: Session, *, crawl: WebsiteCrawl, page: ParsedPage, excerpt_limit: int = 2000) -> dict[str, int]:
    counts = {"developers_created": 0, "projects_created": 0, "projects_reused": 0, "contacts_created": 0, "social_profiles_created": 0, "relationship_candidates_created": 0, "evidence_records_created": 0}
    developer = _resolve_developer(db, crawl, page, counts, excerpt_limit)
    projects: list[Project] = []
    for fact in page.project_candidates:
        normalized = normalize_name(fact.value)
        project = db.scalar(select(Project).where(Project.normalized_name == normalized))
        if project:
            counts["projects_reused"] += 1
        else:
            location = fact.metadata.get("location_status")
            project = Project(name=fact.value, normalized_name=normalized, developer_id=None, verification_status="unverified", project_status=fact.metadata.get("project_status", "unknown"), project_type=None if fact.metadata.get("project_type") == "unknown" else fact.metadata.get("project_type"), city="Lahore" if location in {"confirmed_lahore", "probable_lahore"} else "Unknown", country="Pakistan", official_website_url=fact.metadata.get("detail_url"))
            db.add(project)
            db.flush()
            counts["projects_created"] += 1
        projects.append(project)
        counts["evidence_records_created"] += _evidence(db, crawl, project_id=project.id, fact=fact, page=page, excerpt_limit=excerpt_limit)
        for field in ("location_status", "project_type", "project_status"):
            value = fact.metadata.get(field)
            if value and value != "unknown":
                counts["evidence_records_created"] += _evidence(db, crawl, project_id=project.id, fact=ExtractedFact(f"project_{field}", value, fact.excerpt), page=page, excerpt_limit=excerpt_limit)
    if crawl.project_id:
        owner_project = db.get(Project, crawl.project_id)
        if owner_project and all(project.id != owner_project.id for project in projects):
            projects.append(owner_project)
    owner_project_id = crawl.project_id if crawl.project_id and crawl.crawl_mode == "project_site" else None
    owner_developer_id = crawl.developer_id or (developer.id if developer else None)
    for fact in page.facts:
        counts["evidence_records_created"] += _evidence(db, crawl, developer_id=owner_developer_id if not owner_project_id else None, project_id=owner_project_id, fact=fact, page=page, excerpt_limit=excerpt_limit)
        if not owner_developer_id and not owner_project_id:
            continue
        if fact.field_name.startswith("official_"):
            platform = fact.metadata["platform"]
            normalized = normalize_url(fact.value)
            exists = db.scalar(select(SocialProfile).where(SocialProfile.normalized_url == normalized, SocialProfile.developer_id == owner_developer_id, SocialProfile.project_id == owner_project_id))
            if not exists:
                db.add(SocialProfile(developer_id=owner_developer_id if not owner_project_id else None, project_id=owner_project_id, platform=platform, profile_url=fact.value, normalized_url=normalized, is_official=False, verification_status="unverified"))
                counts["social_profiles_created"] += 1
        elif fact.metadata.get("contact_type"):
            contact_type = fact.metadata["contact_type"]
            value = fact.metadata.get("displayed_value") or fact.value
            normalized = fact.metadata.get("normalized_value") or normalize_contact_value(value, contact_type)
            exists = db.scalar(select(Contact).where(Contact.normalized_value == normalized, Contact.contact_type == contact_type, Contact.developer_id == owner_developer_id, Contact.project_id == owner_project_id))
            if not exists:
                db.add(Contact(developer_id=owner_developer_id if not owner_project_id else None, project_id=owner_project_id, contact_type=contact_type, value=value, normalized_value=normalized, verification_status="unverified", source_url=page.url, is_public_business_contact=True))
                counts["contacts_created"] += 1
    if developer:
        for project in projects:
            relation = _relationship(page.text)
            # If this crawl was launched FOR this exact project (project.official_website_url
            # is what we're crawling), we already know the answer with high confidence -
            # we don't need the page to literally say "developed by X". Text-mined phrases
            # are only needed (and only trusted as "candidate") for OTHER projects the page
            # happens to mention alongside the seed project.
            is_seed_project = crawl.project_id is not None and project.id == crawl.project_id
            if not relation and not is_seed_project:
                continue
            if relation:
                evidence_text, signal = relation, "explicit_developer_relationship"
            else:
                evidence_text = (f"Crawl was seeded from project '{project.name}''s official website "
                                  f"({crawl.canonical_seed_url}), which resolved to developer '{developer.name}'.")
                signal = "seed_project_website_match"
            evidence_fact = ExtractedFact("developer_relationship", f"{project.name} -> {developer.name}", evidence_text, metadata={"signal": signal})
            counts["evidence_records_created"] += _evidence(db, crawl, developer_id=developer.id, project_id=project.id, fact=evidence_fact, page=page, excerpt_limit=excerpt_limit)
            evidence = db.scalar(select(SourceEvidence).where(SourceEvidence.collection_job_id == crawl.collection_job_id, SourceEvidence.project_id == project.id, SourceEvidence.developer_id == developer.id, SourceEvidence.field_name == "developer_relationship", SourceEvidence.source_url == page.url))
            existing_rel = db.scalar(select(ProjectDeveloperRelationship).where(ProjectDeveloperRelationship.project_id == project.id, ProjectDeveloperRelationship.developer_id == developer.id, ProjectDeveloperRelationship.relationship_type == "developer", ProjectDeveloperRelationship.source_url == page.url))
            if existing_rel:
                continue
            if is_seed_project and project.developer_id in (None, developer.id):
                # High-confidence, structurally-derived link: record it as already verified
                # instead of leaving it to sit unlinked in a manual review queue.
                db.add(ProjectDeveloperRelationship(project_id=project.id, developer_id=developer.id, relationship_type="developer", status="verified", source_evidence=evidence, source_url=page.url, evidence_text=evidence_text[:excerpt_limit], reviewed_at=utc_now(), review_note="Auto-verified: crawl seeded from this project's official website."))
                project.developer_id = developer.id
                counts["relationship_candidates_created"] += 1
            else:
                db.add(ProjectDeveloperRelationship(project_id=project.id, developer_id=developer.id, relationship_type="developer", status="candidate", source_evidence=evidence, source_url=page.url, evidence_text=evidence_text[:excerpt_limit]))
                counts["relationship_candidates_created"] += 1
    db.commit()
    return counts


def _resolve_developer(db: Session, crawl: WebsiteCrawl, page: ParsedPage, counts: dict[str, int], excerpt_limit: int) -> Developer | None:
    if crawl.developer_id:
        return db.get(Developer, crawl.developer_id)
    if not page.organization_names:
        return None
    normalized_names = {normalize_name(fact.value) for fact in page.organization_names}
    if len(normalized_names) > 1:
        crawl.warning_message = "Conflicting organization identities require review"
    fact = page.organization_names[0]
    developer = db.scalar(select(Developer).where(Developer.normalized_name == normalize_name(fact.value)))
    if not developer:
        developer = Developer(name=fact.value, normalized_name=normalize_name(fact.value), classification="uncertain", verification_status="unverified", website_url=crawl.canonical_seed_url, city="Lahore", country="Pakistan")
        db.add(developer)
        db.flush()
        counts["developers_created"] += 1
    if crawl.developer_id is None:
        crawl.developer_id = developer.id
    for identity in page.organization_names:
        counts["evidence_records_created"] += _evidence(db, crawl, developer_id=developer.id, fact=identity, page=page, excerpt_limit=excerpt_limit)
    return developer


def _evidence(db: Session, crawl: WebsiteCrawl, *, fact: ExtractedFact, page: ParsedPage, excerpt_limit: int, developer_id: int | None = None, project_id: int | None = None) -> int:
    existing = db.scalar(select(SourceEvidence).where(SourceEvidence.collection_job_id == crawl.collection_job_id, SourceEvidence.developer_id == developer_id, SourceEvidence.project_id == project_id, SourceEvidence.source_url == page.url, SourceEvidence.field_name == fact.field_name, SourceEvidence.extracted_value == fact.value))
    if existing:
        return 0
    db.add(SourceEvidence(developer_id=developer_id, project_id=project_id, collection_job_id=crawl.collection_job_id, source_type="project_website" if crawl.crawl_mode == "project_site" else "official_website", source_url=page.url, source_title=page.title, captured_text=fact.excerpt[:excerpt_limit], field_name=fact.field_name, extracted_value=fact.value[:2048], verification_status="unverified", collected_at=utc_now()))
    db.flush()
    return 1


def _relationship(text: str) -> str | None:
    match = re.search(r"[^.]{0,120}\b(?:developed by|a project by|owned and developed by|development partner|joint venture|our project|our development)\b[^.]{0,160}[.]?", text, re.I)
    return match.group(0).strip() if match else None
