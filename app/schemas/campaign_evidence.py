from __future__ import annotations

from datetime import datetime

from app.schemas.common import ORMModel


class CampaignEvidenceRead(ORMModel):
    id: int
    social_capture_id: int
    developer_id: int | None
    project_id: int | None
    platform: str
    campaign_type: str
    advertiser_name: str | None
    campaign_text: str | None
    call_to_action: str | None
    destination_url: str | None
    visible_status: str
    verification_status: str
    first_seen_at: datetime
    last_seen_at: datetime
    source_url: str
    created_at: datetime
    updated_at: datetime

