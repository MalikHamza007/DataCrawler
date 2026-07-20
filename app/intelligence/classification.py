from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.base import utc_now
from app.intelligence.constants import DEVELOPER_RULES, PROJECT_RULES
from app.intelligence.signals import confidence, explanation, signal
from app.models.developer import Developer
from app.models.intelligence import ClassificationAssessment
from app.models.project import Project
from app.models.project_developer_relationship import ProjectDeveloperRelationship
from app.models.source_evidence import SourceEvidence


def assess_developer(db: Session, developer_id: int, settings: Settings | None = None) -> ClassificationAssessment:
    settings = settings or get_settings()
    developer = db.get(Developer, developer_id)
    if not developer:
        raise ValueError("Developer was not found")
    evidence = list(db.scalars(select(SourceEvidence).where(SourceEvidence.developer_id == developer_id)).all())
    signals = _rule_signals(evidence, DEVELOPER_RULES)
    relationships = list(db.scalars(select(ProjectDeveloperRelationship).where(ProjectDeveloperRelationship.developer_id == developer_id)).all())
    if len(relationships) >= 2:
        signals.append(signal("MULTIPLE_PROJECTS", "Multiple project relationships", 15, [r.source_evidence_id for r in relationships if r.source_evidence_id], project_count=len(relationships)))
    score = max(0, min(100, sum(item["score"] for item in signals)))
    codes = {item["code"] for item in signals}
    positive_developer = bool(codes & {"OFFICIAL_DEVELOPER_LANGUAGE", "OFFICIAL_PROJECT_PORTFOLIO", "EXPLICIT_DEVELOPED_BY"})
    marketing = "MARKETING_PARTNER" in codes
    broker = bool(codes & {"AUTHORIZED_DEALER", "PROPERTY_CONSULTANT", "BUYING_SELLING"})
    construction = "CONSTRUCTION_ONLY" in codes
    if positive_developer and marketing:
        suggested = "developer_marketing_hybrid"
    elif broker:
        suggested = "broker_agency"
    elif marketing:
        suggested = "marketing_partner"
    elif construction and not positive_developer:
        suggested = "construction_company"
    elif score >= settings.classification_developer_verified_threshold:
        suggested = "verified_developer"
    elif score >= settings.classification_developer_probable_threshold:
        suggested = "probable_developer"
    else:
        suggested = "uncertain"
    return _upsert(db, "developer", developer_id, suggested, score, signals, settings)


def assess_project(db: Session, project_id: int, settings: Settings | None = None) -> ClassificationAssessment:
    settings = settings or get_settings()
    project = db.get(Project, project_id)
    if not project:
        raise ValueError("Project was not found")
    evidence = list(db.scalars(select(SourceEvidence).where(SourceEvidence.project_id == project_id)).all())
    signals = _rule_signals(evidence, PROJECT_RULES, record_text=" ".join(filter(None, [project.name, project.project_type, project.project_status, project.address, project.city])))
    if project.official_website_url and not any(s["code"] == "OFFICIAL_PROJECT_PAGE" for s in signals):
        signals.append(signal("OFFICIAL_PROJECT_PAGE", "Official project URL is recorded", 25, []))
    score = max(0, min(100, sum(item["score"] for item in signals)))
    codes = {item["code"] for item in signals}
    if "BROKER_LANGUAGE" in codes:
        suggested = "broker_listing"
    elif "GENERIC_OFFICE" in codes and score < 60:
        suggested = "project_sales_office"
    elif score >= settings.classification_project_verified_threshold:
        suggested = "verified_project"
    elif score >= settings.classification_project_probable_threshold:
        suggested = "probable_project"
    else:
        suggested = "uncertain"
    return _upsert(db, "project", project_id, suggested, score, signals, settings)


def _rule_signals(evidence: list[SourceEvidence], rules: tuple, record_text: str = "") -> list[dict]:
    found: list[dict] = []
    for code, label, points, terms in rules:
        matches = []
        for item in evidence:
            haystack = " ".join(filter(None, [item.source_type, item.field_name, item.extracted_value, item.captured_text])).casefold()
            if any(term in haystack for term in terms):
                matches.append(item.id)
        if not matches and record_text and any(term in record_text.casefold() for term in terms):
            matches = []
            found.append(signal(code, label, points, matches, source="record_field"))
        elif matches:
            found.append(signal(code, label, points, matches))
    return found


def _upsert(db: Session, entity_type: str, entity_id: int, suggested: str, score: int, signals: list[dict], settings: Settings) -> ClassificationAssessment:
    owner_filter = ClassificationAssessment.developer_id == entity_id if entity_type == "developer" else ClassificationAssessment.project_id == entity_id
    assessment = db.scalar(select(ClassificationAssessment).where(ClassificationAssessment.entity_type == entity_type, owner_filter, ClassificationAssessment.rule_version == settings.intelligence_rule_version))
    values = {"suggested_classification": suggested, "system_score": score, "confidence_level": confidence(score, signals, settings.duplicate_high_confidence_threshold, 60), "signals_json": signals, "explanation": explanation(signals)}
    if assessment:
        for key, value in values.items(): setattr(assessment, key, value)
    else:
        assessment = ClassificationAssessment(entity_type=entity_type, developer_id=entity_id if entity_type == "developer" else None, project_id=entity_id if entity_type == "project" else None, rule_version=settings.intelligence_rule_version, **values)
        db.add(assessment)
    db.commit(); db.refresh(assessment)
    return assessment


def review_assessment(db: Session, assessment_id: int, action: str, manual_classification: str | None, note: str) -> ClassificationAssessment:
    assessment = db.get(ClassificationAssessment, assessment_id)
    if not assessment:
        raise ValueError("Classification assessment was not found")
    assessment.manually_reviewed = True; assessment.reviewed_at = utc_now(); assessment.manual_note = note
    if action == "confirm":
        assessment.assessment_status = "confirmed"; assessment.manual_classification = assessment.suggested_classification
    elif action == "override":
        if not manual_classification: raise ValueError("manual_classification is required")
        assessment.assessment_status = "overridden"; assessment.manual_classification = manual_classification
    elif action == "reject":
        assessment.assessment_status = "rejected"
    else: raise ValueError("Invalid review action")
    if assessment.entity_type == "developer" and action != "reject":
        db.get(Developer, assessment.developer_id).classification = assessment.manual_classification
    db.commit(); db.refresh(assessment); return assessment
