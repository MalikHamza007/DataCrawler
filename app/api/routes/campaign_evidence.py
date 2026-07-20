from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.dependencies import DbSession
from app.models.campaign_evidence import CampaignEvidence
from app.schemas.campaign_evidence import CampaignEvidenceRead

router = APIRouter(prefix="/campaign-evidence", tags=["Campaign Evidence"])


@router.get("", response_model=list[CampaignEvidenceRead])
def list_campaign_evidence(
    db: DbSession,
    platform: str | None = None,
    campaign_type: str | None = None,
    visible_status: str | None = None,
    verification_status: str | None = None,
    developer_id: int | None = None,
    project_id: int | None = None,
    first_seen_after: datetime | None = None,
    last_seen_before: datetime | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
) -> list[object]:
    stmt = select(CampaignEvidence)
    for column, value in (
        (CampaignEvidence.platform, platform),
        (CampaignEvidence.campaign_type, campaign_type),
        (CampaignEvidence.visible_status, visible_status),
        (CampaignEvidence.verification_status, verification_status),
        (CampaignEvidence.developer_id, developer_id),
        (CampaignEvidence.project_id, project_id),
    ):
        if value is not None:
            stmt = stmt.where(column == value)
    if first_seen_after is not None:
        stmt = stmt.where(CampaignEvidence.first_seen_at >= first_seen_after)
    if last_seen_before is not None:
        stmt = stmt.where(CampaignEvidence.last_seen_at <= last_seen_before)
    return list(db.scalars(stmt.order_by(CampaignEvidence.first_seen_at.desc()).offset(offset).limit(limit)).all())

