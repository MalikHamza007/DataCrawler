from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import ConflictError, EntityNotFoundError, InvalidOwnerError
from app.db.base import utc_now
from app.models.campaign_evidence import CampaignEvidence
from app.models.contact import Contact
from app.models.developer import Developer
from app.models.project import Project
from app.models.social_capture import SocialCapture
from app.models.social_profile import SocialProfile
from app.models.source_evidence import SourceEvidence
from app.schemas.social_capture import CaptureAttachRequest, CaptureReviewRequest, SocialCaptureCreate, SocialCapturePatch, SocialCaptureResponse
from app.services.normalization import normalize_contact_value, normalize_name, normalize_url

CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SAFE_SOURCE_TYPES = {
    "facebook": "facebook",
    "instagram": "instagram",
    "x": "x",
    "linkedin": "linkedin",
    "meta_ad_library": "meta_ad_library",
    "generic": "generic_public_page",
}
CONTACT_FIELD_TYPES = {
    "phone": "phone",
    "phones": "phone",
    "business_phone": "phone",
    "whatsapp": "whatsapp",
    "email": "email",
    "emails": "email",
    "business_email": "email",
    "address": "address",
    "addresses": "address",
    "office_address": "address",
}


def _clean_text(value: str | None, limit: int = 2048) -> str | None:
    if value is None:
        return None
    text = CONTROL_CHARS_RE.sub("", value).strip()
    return text[:limit] if text else None


def _stable_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().casefold())


def calculate_content_hash(payload: SocialCaptureCreate) -> str:
    capture = payload.capture
    stable = {
        "platform": capture.platform,
        "canonical_url": normalize_url(capture.canonical_url or capture.source_url),
        "page_kind": capture.page_kind,
        "profile_name": normalize_name(capture.profile_name),
        "username": _stable_text(capture.username),
        "visible_text_excerpt": _stable_text(capture.visible_text_excerpt),
        "campaign_destination_url": normalize_url(capture.campaign.destination_url if capture.campaign else None),
    }
    return hashlib.sha256(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _validate_active_targets(db: Session, developer_id: int | None, project_id: int | None) -> tuple[Developer | None, Project | None]:
    developer = db.get(Developer, developer_id) if developer_id is not None else None
    project = db.get(Project, project_id) if project_id is not None else None
    if developer_id is not None and developer is None:
        raise EntityNotFoundError(f"Developer {developer_id} was not found.")
    if project_id is not None and project is None:
        raise EntityNotFoundError(f"Project {project_id} was not found.")
    if developer is not None and developer.record_status != "active":
        raise InvalidOwnerError("Selected developer was merged or is not active.")
    if project is not None and project.record_status != "active":
        raise InvalidOwnerError("Selected project was merged or is not active.")
    return developer, project


def _payload_json(payload: SocialCaptureCreate) -> str:
    return json.dumps(payload.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)


def _target_ids(field_target: str, developer_id: int | None, project_id: int | None) -> list[tuple[int | None, int | None]]:
    if field_target == "developer":
        return [(developer_id, None)] if developer_id else []
    if field_target == "project":
        return [(None, project_id)] if project_id else []
    if field_target == "capture":
        return []
    ids: list[tuple[int | None, int | None]] = []
    if developer_id:
        ids.append((developer_id, None))
    if project_id:
        ids.append((None, project_id))
    return ids


def _evidence_exists(db: Session, *, developer_id: int | None, project_id: int | None, field_name: str, value: str, source_url: str) -> bool:
    stmt = select(SourceEvidence.id).where(
        SourceEvidence.developer_id.is_(developer_id) if developer_id is None else SourceEvidence.developer_id == developer_id,
        SourceEvidence.project_id.is_(project_id) if project_id is None else SourceEvidence.project_id == project_id,
        SourceEvidence.field_name == field_name,
        SourceEvidence.extracted_value == value,
        SourceEvidence.source_url == source_url,
    )
    return db.scalar(stmt) is not None


def _create_evidence(
    db: Session,
    *,
    capture: SocialCapture,
    field_name: str,
    original: str,
    submitted: str,
    developer_id: int | None,
    project_id: int | None,
) -> bool:
    if developer_id is None and project_id is None:
        return False
    value = _clean_text(submitted)
    if not value or _evidence_exists(db, developer_id=developer_id, project_id=project_id, field_name=field_name, value=value, source_url=capture.source_url):
        return False
    captured_text = json.dumps(
        {
            "original_extracted_value": _clean_text(original),
            "submitted_value": value,
            "was_edited": _clean_text(original) != value,
            "visible_excerpt": _clean_text(capture.visible_text_excerpt, 2000),
        },
        ensure_ascii=False,
    )
    db.add(
        SourceEvidence(
            developer_id=developer_id,
            project_id=project_id,
            source_type=SAFE_SOURCE_TYPES.get(capture.platform, "generic_public_page"),
            source_url=capture.source_url,
            source_title=capture.page_title,
            captured_text=captured_text,
            field_name=field_name,
            extracted_value=value,
            verification_status="unverified",
            collected_at=capture.captured_at,
        )
    )
    return True


def _create_contact_if_needed(
    db: Session,
    *,
    developer_id: int | None,
    project_id: int | None,
    contact_type: str,
    label: str | None,
    value: str,
    source_url: str,
) -> bool:
    if developer_id is None and project_id is None:
        return False
    normalized = normalize_contact_value(value, contact_type)
    stmt = select(Contact.id).where(Contact.contact_type == contact_type, Contact.normalized_value == normalized)
    stmt = stmt.where(Contact.developer_id == developer_id) if developer_id else stmt.where(Contact.developer_id.is_(None))
    stmt = stmt.where(Contact.project_id == project_id) if project_id else stmt.where(Contact.project_id.is_(None))
    if db.scalar(stmt) is not None:
        return False
    db.add(
        Contact(
            developer_id=developer_id,
            project_id=project_id,
            contact_type=contact_type,
            label=label,
            value=value,
            normalized_value=normalized,
            is_public_business_contact=True,
            verification_status="unverified",
            source_url=source_url,
        )
    )
    return True


def _create_social_profile_if_needed(db: Session, *, capture: SocialCapture, developer_id: int | None, project_id: int | None) -> bool:
    if developer_id is None and project_id is None:
        return False
    if capture.page_kind not in {"business_profile", "company_page", "project_page"}:
        return False
    normalized = normalize_url(capture.canonical_url or capture.source_url)
    stmt = select(SocialProfile.id).where(SocialProfile.platform == capture.platform, SocialProfile.normalized_url == normalized)
    stmt = stmt.where(SocialProfile.developer_id == developer_id) if developer_id else stmt.where(SocialProfile.developer_id.is_(None))
    stmt = stmt.where(SocialProfile.project_id == project_id) if project_id else stmt.where(SocialProfile.project_id.is_(None))
    if normalized is None or db.scalar(stmt) is not None:
        return False
    db.add(
        SocialProfile(
            developer_id=developer_id,
            project_id=project_id,
            platform=capture.platform if capture.platform != "meta_ad_library" else "facebook",
            profile_name=capture.profile_name,
            profile_url=capture.canonical_url or capture.source_url,
            normalized_url=normalized,
            is_official=False,
            verification_status="unverified",
        )
    )
    return True


def _create_campaign_if_needed(db: Session, *, capture: SocialCapture, payload: SocialCaptureCreate) -> bool:
    campaign = payload.capture.campaign
    if campaign is None:
        return False
    verification_status = campaign.verification_status
    if payload.capture.platform == "meta_ad_library" and payload.capture.page_kind == "ad_library_result":
        verification_status = "captured_from_ad_library"
    elif verification_status == "captured_from_ad_library":
        verification_status = "public_post_only"
    stmt = select(CampaignEvidence.id).where(CampaignEvidence.social_capture_id == capture.id)
    if db.scalar(stmt) is not None:
        return False
    db.add(
        CampaignEvidence(
            social_capture_id=capture.id,
            developer_id=capture.developer_id,
            project_id=capture.project_id,
            platform=capture.platform,
            campaign_type=campaign.campaign_type,
            advertiser_name=_clean_text(campaign.advertiser_name, 255),
            campaign_text=_clean_text(campaign.campaign_text, 10000),
            call_to_action=_clean_text(campaign.call_to_action, 255),
            destination_url=campaign.destination_url,
            visible_status=campaign.visible_status,
            verification_status=verification_status,
            first_seen_at=capture.captured_at,
            last_seen_at=capture.captured_at,
            source_url=capture.source_url,
        )
    )
    return True


def _create_children(db: Session, capture: SocialCapture, payload: SocialCaptureCreate) -> tuple[int, int, int, int]:
    evidence_count = 0
    contact_count = 0
    social_count = 0
    for field in payload.selected_fields:
        if not field.include:
            continue
        field_name = _clean_text(field.field_name, 100) or "captured_field"
        value = _clean_text(field.submitted_value)
        original = _clean_text(field.original_extracted_value) or ""
        if not value:
            continue
        for developer_id, project_id in _target_ids(field.target_entity, capture.developer_id, capture.project_id):
            if _create_evidence(db, capture=capture, field_name=field_name, original=original, submitted=value, developer_id=developer_id, project_id=project_id):
                evidence_count += 1
            contact_type = CONTACT_FIELD_TYPES.get(field_name)
            if contact_type and _create_contact_if_needed(db, developer_id=developer_id, project_id=project_id, contact_type=contact_type, label=field.source_label, value=value, source_url=capture.source_url):
                contact_count += 1
    for developer_id, project_id in _target_ids("both", capture.developer_id, capture.project_id):
        if _create_social_profile_if_needed(db, capture=capture, developer_id=developer_id, project_id=project_id):
            social_count += 1
            evidence_count += int(
                _create_evidence(
                    db,
                    capture=capture,
                    field_name="social_profile_name",
                    original=capture.profile_name or capture.page_title or capture.source_url,
                    submitted=capture.profile_name or capture.page_title or capture.source_url,
                    developer_id=developer_id,
                    project_id=project_id,
                )
            )
    campaign_count = int(_create_campaign_if_needed(db, capture=capture, payload=payload))
    return evidence_count, contact_count, social_count, campaign_count


def create_social_capture(db: Session, payload: SocialCaptureCreate, settings: Settings) -> SocialCaptureResponse:
    _validate_active_targets(db, payload.developer_id, payload.project_id)
    raw_payload = _payload_json(payload)
    if len(raw_payload.encode("utf-8")) > settings.alduor_extension_max_capture_bytes:
        raise InvalidOwnerError("Capture payload was too large.")
    content_hash = calculate_content_hash(payload)
    existing_id = db.scalar(select(SocialCapture.id).where(SocialCapture.content_hash == content_hash))
    if existing_id is not None:
        raise ConflictError(f"Duplicate capture already exists: {existing_id}")
    capture = SocialCapture(
        platform=payload.capture.platform,
        page_kind=payload.capture.page_kind,
        source_url=payload.capture.source_url,
        canonical_url=payload.capture.canonical_url,
        page_title=_clean_text(payload.capture.page_title, 255),
        profile_name=_clean_text(payload.capture.profile_name, 255),
        username=_clean_text(payload.capture.username, 255),
        visible_text_excerpt=_clean_text(payload.capture.visible_text_excerpt, settings.alduor_extension_max_text_length),
        about_text=_clean_text(payload.capture.about_text, 10000),
        capture_payload_json=raw_payload,
        content_hash=content_hash,
        extractor_version=payload.capture.extractor_version,
        capture_version=payload.capture.capture_version,
        extension_version=payload.extension_version,
        developer_id=payload.developer_id,
        project_id=payload.project_id,
        review_status="attached" if payload.developer_id or payload.project_id else "unassigned",
        captured_at=payload.capture.captured_at,
        review_note=payload.operator_note,
    )
    db.add(capture)
    db.flush()
    evidence_count, contact_count, social_count, campaign_count = _create_children(db, capture, payload)
    db.commit()
    db.refresh(capture)
    return SocialCaptureResponse(
        id=capture.id,
        status=capture.review_status,
        developer_id=capture.developer_id,
        project_id=capture.project_id,
        source_evidence_created=evidence_count,
        contacts_created=contact_count,
        social_profiles_created=social_count,
        campaign_evidence_created=campaign_count,
        warnings=payload.capture.warnings,
    )


def list_social_captures(
    db: Session,
    *,
    offset: int,
    limit: int,
    platform: str | None = None,
    page_kind: str | None = None,
    developer_id: int | None = None,
    project_id: int | None = None,
    review_status: str | None = None,
    captured_after: Any | None = None,
    captured_before: Any | None = None,
) -> list[SocialCapture]:
    stmt = select(SocialCapture)
    for column, value in (
        (SocialCapture.platform, platform),
        (SocialCapture.page_kind, page_kind),
        (SocialCapture.developer_id, developer_id),
        (SocialCapture.project_id, project_id),
        (SocialCapture.review_status, review_status),
    ):
        if value is not None:
            stmt = stmt.where(column == value)
    if captured_after is not None:
        stmt = stmt.where(SocialCapture.captured_at >= captured_after)
    if captured_before is not None:
        stmt = stmt.where(SocialCapture.captured_at <= captured_before)
    return list(db.scalars(stmt.order_by(SocialCapture.received_at.desc()).offset(offset).limit(min(limit, 100))).all())


def get_social_capture(db: Session, capture_id: int) -> SocialCapture:
    capture = db.get(SocialCapture, capture_id)
    if capture is None:
        raise EntityNotFoundError(f"Social capture {capture_id} was not found.")
    return capture


def update_social_capture(db: Session, capture_id: int, payload: SocialCapturePatch) -> SocialCapture:
    capture = get_social_capture(db, capture_id)
    data = payload.model_dump(exclude_unset=True)
    if "review_status" in data and data["review_status"] in {"accepted", "rejected", "duplicate"}:
        data["reviewed_at"] = utc_now()
    for key, value in data.items():
        setattr(capture, key, value)
    db.commit()
    db.refresh(capture)
    return capture


def attach_social_capture(db: Session, capture_id: int, payload: CaptureAttachRequest) -> SocialCapture:
    capture = get_social_capture(db, capture_id)
    _validate_active_targets(db, payload.developer_id, payload.project_id)
    capture.developer_id = payload.developer_id
    capture.project_id = payload.project_id
    capture.review_status = "attached" if payload.developer_id or payload.project_id else "unassigned"
    capture.review_note = payload.review_note
    if payload.create_evidence:
        stored = SocialCaptureCreate.model_validate(json.loads(capture.capture_payload_json))
        _create_children(db, capture, stored)
    db.commit()
    db.refresh(capture)
    return capture


def review_social_capture(db: Session, capture_id: int, action: str, payload: CaptureReviewRequest) -> SocialCapture:
    capture = get_social_capture(db, capture_id)
    capture.review_status = {"accept": "accepted", "reject": "rejected"}.get(action, "duplicate")
    capture.review_note = payload.review_note
    capture.reviewed_at = utc_now()
    db.commit()
    db.refresh(capture)
    return capture

