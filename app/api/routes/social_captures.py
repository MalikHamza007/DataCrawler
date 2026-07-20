from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, status

from app.api.dependencies import DbSession, pagination
from app.core.config import get_settings
from app.models.campaign_evidence import CampaignEvidence
from app.schemas.campaign_evidence import CampaignEvidenceRead
from app.schemas.social_capture import CaptureAttachRequest, CaptureReviewRequest, SocialCaptureCreate, SocialCapturePatch, SocialCaptureRead, SocialCaptureResponse
from app.services.extension_auth import validate_extension_request
from app.services import social_capture as service
from sqlalchemy import select

router = APIRouter(prefix="/social-captures", tags=["Social Captures"])


def _validate_extension_headers(
    request: Request,
    token: str | None,
    origin: str | None,
) -> None:
    content_length = request.headers.get("content-length")
    validate_extension_request(
        settings=get_settings(),
        token=token,
        origin=origin,
        content_length=int(content_length) if content_length and content_length.isdigit() else None,
    )


@router.post("", response_model=SocialCaptureResponse, status_code=status.HTTP_201_CREATED)
def create_social_capture(
    payload: SocialCaptureCreate,
    request: Request,
    db: DbSession,
    x_alduor_extension_token: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> SocialCaptureResponse:
    _validate_extension_headers(request, x_alduor_extension_token, origin)
    return service.create_social_capture(db, payload, get_settings())


@router.get("", response_model=list[SocialCaptureRead])
def list_social_captures(
    db: DbSession,
    page: Annotated[tuple[int, int], Depends(pagination)],
    platform: str | None = Query(default=None),
    page_kind: str | None = Query(default=None),
    developer_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    review_status: str | None = Query(default=None),
    captured_after: datetime | None = Query(default=None),
    captured_before: datetime | None = Query(default=None),
) -> list[object]:
    offset, limit = page
    return service.list_social_captures(
        db,
        offset=offset,
        limit=limit,
        platform=platform,
        page_kind=page_kind,
        developer_id=developer_id,
        project_id=project_id,
        review_status=review_status,
        captured_after=captured_after,
        captured_before=captured_before,
    )


@router.get("/{capture_id}", response_model=SocialCaptureRead)
def get_social_capture(capture_id: int, db: DbSession) -> object:
    return service.get_social_capture(db, capture_id)


@router.get("/{capture_id}/campaign-evidence", response_model=list[CampaignEvidenceRead])
def get_capture_campaign_evidence(capture_id: int, db: DbSession) -> list[object]:
    service.get_social_capture(db, capture_id)
    return list(db.scalars(select(CampaignEvidence).where(CampaignEvidence.social_capture_id == capture_id)).all())


@router.patch("/{capture_id}", response_model=SocialCaptureRead)
def update_social_capture(capture_id: int, payload: SocialCapturePatch, db: DbSession) -> object:
    return service.update_social_capture(db, capture_id, payload)


@router.post("/{capture_id}/attach", response_model=SocialCaptureRead)
def attach_social_capture(capture_id: int, payload: CaptureAttachRequest, db: DbSession) -> object:
    return service.attach_social_capture(db, capture_id, payload)


@router.post("/{capture_id}/accept", response_model=SocialCaptureRead)
def accept_social_capture(capture_id: int, payload: CaptureReviewRequest, db: DbSession) -> object:
    return service.review_social_capture(db, capture_id, "accept", payload)


@router.post("/{capture_id}/reject", response_model=SocialCaptureRead)
def reject_social_capture(capture_id: int, payload: CaptureReviewRequest, db: DbSession) -> object:
    return service.review_social_capture(db, capture_id, "reject", payload)


@router.post("/{capture_id}/mark-duplicate", response_model=SocialCaptureRead)
def mark_duplicate_social_capture(capture_id: int, payload: CaptureReviewRequest, db: DbSession) -> object:
    return service.review_social_capture(db, capture_id, "duplicate", payload)
