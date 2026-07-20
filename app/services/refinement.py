from __future__ import annotations

import re
from collections import defaultdict
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.collectors.websites.exceptions import UnsafeURLError
from app.db.base import utc_now
from app.intelligence.relationships import score_relationship
from app.models.collection_job import CollectionJob
from app.models.contact import Contact
from app.models.developer import Developer
from app.models.intelligence import ClassificationAssessment
from app.models.project import Project
from app.models.project_developer_relationship import ProjectDeveloperRelationship
from app.models.project_discovery import ProjectDiscovery
from app.models.website_crawl import WebsiteCrawl
from app.schemas.website_enrichment import WebsiteEnrichmentRequest
from app.services.normalization import normalize_contact_value, normalize_name
from app.services.website_enrichment import create_project_job


REFINEMENT_SCHEMA_VERSION = "alduor-refined-v1"
POSITIVE_PLACE_TYPES = {
    "apartment_building",
    "apartment_complex",
    "housing_complex",
    "condominium_complex",
    "shopping_mall",
    "business_center",
    "plaza",
    "premise",
}
NEGATIVE_PLACE_TYPES = {
    "real_estate_agency",
    "general_contractor",
    "association_or_organization",
    "service",
    "consultant",
    "corporate_office",
}
PROJECT_NAME_TERMS = {
    "apartment",
    "apartments",
    "arcade",
    "business center",
    "business centre",
    "heights",
    "homes",
    "housing scheme",
    "mall",
    "plaza",
    "residencia",
    "residences",
    "residency",
    "square",
    "tower",
    "towers",
    "villas",
}
JUNK_DEVELOPER_NAMES = {
    "all rights reserved",
    "copyright",
    "home",
    "official website",
}
DEVELOPER_BYLINE_RE = re.compile(
    r"\b(?:developed\s+by|owned\s+and\s+developed\s+by|a\s+project\s+by)\s+"
    r"([A-Z][A-Za-z0-9&.'() -]{1,90}?(?:Developers?|Development|Properties|Group|Holdings|Limited|Ltd\.?|Pvt\.?\s+Ltd\.?))"
    r"(?=\s*(?:[,.;|]|\bis\b|\bhas\b|\bwith\b|$))",
    re.IGNORECASE,
)


def explicit_developer_name(text: str | None) -> str | None:
    if not text:
        return None
    match = DEVELOPER_BYLINE_RE.search(text)
    if not match:
        return None
    value = re.sub(r"\s+", " ", match.group(1)).strip(" ,.;|-\n\t")
    if len(value) < 3 or value.casefold() in JUNK_DEVELOPER_NAMES:
        return None
    return value


def refinement_summary(db: Session) -> dict[str, int | str]:
    projects = list(db.scalars(select(Project).where(Project.record_status == "active")).all())
    relevance = relevance_scores(db, [project.id for project in projects])
    relevant = [project for project in projects if relevance.get(project.id, 0) >= 60]
    ready_ids = refined_project_ids(db, relevance=relevance)
    return {
        "schema_version": REFINEMENT_SCHEMA_VERSION,
        "raw_projects": len(projects),
        "likely_real_estate_projects": len(relevant),
        "with_exact_location": sum(bool(project.address and project.latitude is not None and project.longitude is not None) for project in relevant),
        "with_official_website": sum(bool(project.official_website_url) for project in relevant),
        "with_assigned_developer": sum(project.developer_id is not None for project in relevant),
        "export_ready_projects": len(ready_ids),
        "excluded_incomplete_projects": len(relevant) - len(ready_ids),
    }


def relevance_scores(db: Session, project_ids: list[int]) -> dict[int, int]:
    if not project_ids:
        return {}
    discoveries = list(db.scalars(select(ProjectDiscovery).where(ProjectDiscovery.project_id.in_(project_ids))).all())
    by_project: dict[int, list[ProjectDiscovery]] = defaultdict(list)
    for discovery in discoveries:
        by_project[discovery.project_id].append(discovery)
    projects = {project.id: project for project in db.scalars(select(Project).where(Project.id.in_(project_ids))).all()}
    latest_assessments: dict[int, ClassificationAssessment] = {}
    assessments = list(
        db.scalars(
            select(ClassificationAssessment)
            .where(ClassificationAssessment.project_id.in_(project_ids), ClassificationAssessment.entity_type == "project")
            .order_by(ClassificationAssessment.updated_at.desc(), ClassificationAssessment.id.desc())
        ).all()
    )
    for assessment in assessments:
        latest_assessments.setdefault(assessment.project_id, assessment)
    scores: dict[int, int] = {}
    for project_id, project in projects.items():
        rows = by_project.get(project_id, [])
        place_types = {row.google_primary_type for row in rows if row.google_primary_type}
        name = (project.name or "").casefold()
        score = 0
        if place_types & POSITIVE_PLACE_TYPES:
            score += 60
        if any(term in name for term in PROJECT_NAME_TERMS):
            score += 35
        if len({row.source_query for row in rows if row.source_query}) >= 2:
            score += 10
        if place_types and place_types <= NEGATIVE_PLACE_TYPES and not any(term in name for term in PROJECT_NAME_TERMS):
            score -= 60
        assessment = latest_assessments.get(project_id)
        if assessment:
            effective = assessment.effective_classification
            if effective in {"verified_project", "probable_project"}:
                score = max(score, assessment.system_score)
            elif effective in {"broker_listing", "project_sales_office"}:
                score -= 40
        scores[project_id] = max(0, min(100, score))
    return scores


def refined_project_ids(db: Session, *, relevance: dict[int, int] | None = None) -> list[int]:
    projects = list(
        db.scalars(
            select(Project)
            .options(selectinload(Project.developer))
            .where(Project.record_status == "active", Project.developer_id.is_not(None))
            .order_by(Project.normalized_name.asc().nulls_last(), Project.name.asc(), Project.id.asc())
        ).all()
    )
    relevance = relevance or relevance_scores(db, [project.id for project in projects])
    developer_ids = {project.developer_id for project in projects if project.developer_id is not None}
    contacts = list(db.scalars(select(Contact).where(Contact.developer_id.in_(developer_ids or {-1}), Contact.is_public_business_contact.is_(True))).all())
    types_by_developer: dict[int, set[str]] = defaultdict(set)
    for contact in contacts:
        if contact.developer_id is not None and contact.value.strip():
            types_by_developer[contact.developer_id].add(contact.contact_type)
    ready = []
    for project in projects:
        contact_types = types_by_developer.get(project.developer_id, set())
        has_phone = bool(contact_types & {"mobile", "phone", "landline", "whatsapp"})
        has_email = "email" in contact_types
        exact_location = bool(project.address and project.latitude is not None and project.longitude is not None)
        developer_name = project.developer.name.strip() if project.developer and project.developer.name else ""
        if relevance.get(project.id, 0) >= 60 and exact_location and developer_name and has_phone and has_email:
            ready.append(project.id)
    return ready


def build_refined_records(db: Session, project_ids: list[int] | None = None) -> list[dict[str, object]]:
    ids = project_ids if project_ids is not None else refined_project_ids(db)
    if not ids:
        return []
    projects = list(
        db.scalars(
            select(Project)
            .options(selectinload(Project.developer))
            .where(Project.id.in_(ids))
        ).all()
    )
    order = {project_id: index for index, project_id in enumerate(ids)}
    projects.sort(key=lambda project: order[project.id])
    developer_ids = {project.developer_id for project in projects if project.developer_id is not None}
    contacts = list(db.scalars(select(Contact).where((Contact.developer_id.in_(developer_ids or {-1})) | (Contact.project_id.in_(ids)))).all())
    by_developer: dict[int, list[Contact]] = defaultdict(list)
    by_project: dict[int, list[Contact]] = defaultdict(list)
    for contact in contacts:
        if contact.developer_id is not None:
            by_developer[contact.developer_id].append(contact)
        if contact.project_id is not None:
            by_project[contact.project_id].append(contact)
    relevance = relevance_scores(db, ids)
    records: list[dict[str, object]] = []
    for project in projects:
        developer = project.developer
        if developer is None:
            continue
        developer_contacts = by_developer.get(developer.id, [])
        project_contacts = by_project.get(project.id, [])
        records.append(
            {
                "project_id": project.id,
                "project_name": project.name,
                "developer_id": developer.id,
                "developer_name": developer.name,
                "developer_phone": _best_value(developer_contacts, ["mobile", "phone", "landline", "whatsapp"]),
                "developer_email": _best_value(developer_contacts, ["email"]),
                "developer_website": developer.website_url,
                "project_phone": _best_value(project_contacts, ["mobile", "phone", "landline", "whatsapp"]),
                "project_email": _best_value(project_contacts, ["email"]),
                "project_website": project.official_website_url,
                "address": project.address,
                "latitude": project.latitude,
                "longitude": project.longitude,
                "google_place_id": project.google_place_id,
                "google_maps_url": project.google_maps_url,
                "refinement_score": relevance.get(project.id, 0),
            }
        )
    return records


def queue_refinement(db: Session, settings: Settings | None = None) -> tuple[CollectionJob, dict[str, int]]:
    settings = settings or get_settings()
    projects = list(db.scalars(select(Project).where(Project.record_status == "active")).all())
    relevance = relevance_scores(db, [project.id for project in projects])
    existing_project_ids = set(
        db.scalars(
            select(WebsiteCrawl.project_id).where(
                WebsiteCrawl.project_id.is_not(None),
                WebsiteCrawl.status.in_({"queued", "running", "completed", "completed_with_warnings", "blocked_by_robots"}),
            )
        ).all()
    )
    queued = 0
    for project in sorted(projects, key=lambda item: (-relevance.get(item.id, 0), item.id)):
        if queued >= settings.refinement_max_websites:
            break
        if relevance.get(project.id, 0) < 60 or not project.official_website_url or project.id in existing_project_ids:
            continue
        try:
            create_project_job(
                db,
                project.id,
                WebsiteEnrichmentRequest(
                    seed_url=project.official_website_url,
                    max_pages=min(settings.refinement_max_pages_per_website, settings.website_crawler_max_pages_per_site),
                    use_playwright_fallback=True,
                    crawl_mode="project_site",
                ),
                settings,
            )
        except (UnsafeURLError, ValueError, TypeError):
            continue
        queued += 1
    job = CollectionJob(
        job_type="classification_analysis",
        status="queued",
        city="Lahore",
        search_config_json={"entity_type": "all", "entity_ids": [], "refine_clean_data": True, "rule_version": settings.intelligence_rule_version},
        progress_phase="queued",
        progress_message="Clean-data refinement queued after website enrichment",
        max_attempts=settings.worker_max_job_attempts,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job, {"website_jobs_queued": queued, "likely_real_estate_projects": sum(score >= 60 for score in relevance.values())}


def finalize_refinement(db: Session, settings: Settings | None = None) -> dict[str, int | str]:
    settings = settings or get_settings()
    repaired = _repair_explicit_developer_identities(db)
    relationships = list(db.scalars(select(ProjectDeveloperRelationship).where(ProjectDeveloperRelationship.status == "candidate")).all())
    for relationship in relationships:
        score_relationship(db, relationship.id, settings)
    promoted = 0
    by_project: dict[int, list[ProjectDeveloperRelationship]] = defaultdict(list)
    relationships = list(db.scalars(select(ProjectDeveloperRelationship).where(ProjectDeveloperRelationship.status == "candidate")).all())
    for relationship in relationships:
        by_project[relationship.project_id].append(relationship)
    for project_id, candidates in by_project.items():
        project = db.get(Project, project_id)
        if not project or project.developer_id is not None:
            continue
        ranked = sorted(candidates, key=lambda item: (item.system_score or 0, -item.id), reverse=True)
        top = ranked[0]
        if (top.system_score or 0) < settings.relationship_verified_suggestion_threshold:
            continue
        if len(ranked) > 1 and (ranked[1].system_score or 0) >= (top.system_score or 0) - 10:
            continue
        negative_codes = {signal.get("code") for signal in (top.signals_json or []) if signal.get("score", 0) < 0}
        if negative_codes:
            continue
        project.developer_id = top.developer_id
        top.status = "auto_verified"
        top.reviewed_at = utc_now()
        top.review_note = "Auto-linked by deterministic refinement from explicit official-site evidence."
        promoted += 1
    db.commit()
    contacts_copied = _copy_official_domain_contacts(db)
    summary = refinement_summary(db)
    summary.update({"developer_identities_repaired": repaired, "relationships_auto_verified": promoted, "developer_contacts_copied": contacts_copied})
    return summary


def _repair_explicit_developer_identities(db: Session) -> int:
    repaired = 0
    relationships = list(db.scalars(select(ProjectDeveloperRelationship).where(ProjectDeveloperRelationship.status == "candidate")).all())
    for relationship in relationships:
        explicit_name = explicit_developer_name(relationship.evidence_text)
        if not explicit_name:
            continue
        current = db.get(Developer, relationship.developer_id)
        normalized = normalize_name(explicit_name)
        if current and current.normalized_name == normalized:
            continue
        developer = db.scalar(select(Developer).where(Developer.normalized_name == normalized))
        project = db.get(Project, relationship.project_id)
        if developer is None:
            developer = Developer(
                name=explicit_name,
                normalized_name=normalized,
                classification="uncertain",
                verification_status="unverified",
                website_url=project.official_website_url if project else relationship.source_url,
                city="Lahore",
                country="Pakistan",
            )
            db.add(developer)
            db.flush()
        relationship.developer_id = developer.id
        if relationship.source_evidence:
            relationship.source_evidence.developer_id = developer.id
        repaired += 1
    db.commit()
    return repaired


def _copy_official_domain_contacts(db: Session) -> int:
    projects = list(db.scalars(select(Project).where(Project.developer_id.is_not(None), Project.record_status == "active")).all())
    copied = 0
    for project in projects:
        developer = db.get(Developer, project.developer_id)
        if not developer:
            continue
        developer_domain = _domain(developer.website_url or project.official_website_url)
        if not developer_domain:
            continue
        project_contacts = list(db.scalars(select(Contact).where(Contact.project_id == project.id, Contact.is_public_business_contact.is_(True))).all())
        for contact in project_contacts:
            if contact.contact_type not in {"mobile", "phone", "landline", "whatsapp", "email"}:
                continue
            if _domain(contact.source_url) != developer_domain:
                continue
            normalized = contact.normalized_value or normalize_contact_value(contact.value, contact.contact_type)
            exists = db.scalar(
                select(Contact.id).where(
                    Contact.developer_id == developer.id,
                    Contact.contact_type == contact.contact_type,
                    Contact.normalized_value == normalized,
                )
            )
            if exists:
                continue
            db.add(
                Contact(
                    developer_id=developer.id,
                    contact_type=contact.contact_type,
                    label="Official website contact",
                    value=contact.value,
                    normalized_value=normalized,
                    is_primary=not bool(db.scalar(select(Contact.id).where(Contact.developer_id == developer.id, Contact.contact_type == contact.contact_type))),
                    is_public_business_contact=True,
                    verification_status="evidence_backed",
                    source_url=contact.source_url,
                )
            )
            copied += 1
    db.commit()
    return copied


def _best_value(contacts: list[Contact], types: list[str]) -> str | None:
    priority = {contact_type: index for index, contact_type in enumerate(types)}
    matches = [contact for contact in contacts if contact.contact_type in priority and contact.value.strip()]
    matches.sort(key=lambda item: (not item.is_primary, item.verification_status not in {"verified", "evidence_backed"}, priority[item.contact_type], item.id))
    return matches[0].value if matches else None


def _domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        host = (urlsplit(url).hostname or "").casefold().strip(".")
    except ValueError:
        return None
    return host[4:] if host.startswith("www.") else host or None
