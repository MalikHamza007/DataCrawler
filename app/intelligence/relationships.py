from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError
from app.db.base import utc_now
from app.intelligence.signals import confidence, explanation, signal
from app.models.developer import Developer
from app.models.project import Project
from app.models.project_developer_relationship import ProjectDeveloperRelationship


def score_relationship(db: Session, relationship_id: int, settings: Settings | None = None) -> ProjectDeveloperRelationship:
    settings = settings or get_settings(); relationship = db.get(ProjectDeveloperRelationship, relationship_id)
    if not relationship: raise ValueError("Relationship was not found")
    text = relationship.evidence_text.casefold(); signals = []
    if "developed by" in text: signals.append(signal("EXPLICIT_DEVELOPED_BY", "Explicit developed-by language", 70, [relationship.source_evidence_id] if relationship.source_evidence_id else []))
    if "a project by" in text: signals.append(signal("EXPLICIT_PROJECT_BY", "Explicit project-by language", 70, [relationship.source_evidence_id] if relationship.source_evidence_id else []))
    if "our project" in text or "our development" in text: signals.append(signal("OFFICIAL_PORTFOLIO", "Project appears in official portfolio", 40, [relationship.source_evidence_id] if relationship.source_evidence_id else []))
    if "marketing by" in text or "marketing partner" in text: signals.append(signal("MARKETING_ONLY", "Marketing-only relationship language", -30, [relationship.source_evidence_id] if relationship.source_evidence_id else []))
    if "authorized dealer" in text: signals.append(signal("AUTHORIZED_DEALER", "Authorized dealer language", -40, [relationship.source_evidence_id] if relationship.source_evidence_id else []))
    project, developer = db.get(Project, relationship.project_id), db.get(Developer, relationship.developer_id)
    if project.official_website_url and developer.website_url:
        from app.intelligence.normalization import domain
        if domain(project.official_website_url) == domain(developer.website_url): signals.append(signal("MATCHING_DOMAIN", "Project and developer share an official domain", 20, []))
    score = max(0, min(100, sum(item["score"] for item in signals)))
    relationship.system_score = score; relationship.confidence_level = confidence(score, signals, settings.relationship_verified_suggestion_threshold, settings.relationship_probable_threshold); relationship.signals_json = signals; relationship.explanation = explanation(signals); relationship.rule_version = settings.intelligence_rule_version; relationship.evaluated_at = utc_now()
    db.commit(); db.refresh(relationship); return relationship


def verify_relationship(db: Session, relationship_id: int, note: str) -> ProjectDeveloperRelationship:
    relationship = db.get(ProjectDeveloperRelationship, relationship_id)
    if not relationship or relationship.status != "candidate": raise ValueError("Candidate relationship was not found")
    project, developer = db.get(Project, relationship.project_id), db.get(Developer, relationship.developer_id)
    if project.record_status != "active" or developer.record_status != "active": raise ConflictError("Merged or archived records cannot be verified")
    if project.developer_id not in {None, developer.id}: raise ConflictError(f"Project already belongs to developer {project.developer_id}")
    relationship.status = "verified"; relationship.reviewed_at = utc_now(); relationship.review_note = note; project.developer_id = developer.id
    db.commit(); db.refresh(relationship); return relationship


def reject_relationship(db: Session, relationship_id: int, note: str) -> ProjectDeveloperRelationship:
    relationship = db.get(ProjectDeveloperRelationship, relationship_id)
    if not relationship: raise ValueError("Relationship was not found")
    relationship.status = "rejected"; relationship.reviewed_at = utc_now(); relationship.review_note = note
    db.commit(); db.refresh(relationship); return relationship
