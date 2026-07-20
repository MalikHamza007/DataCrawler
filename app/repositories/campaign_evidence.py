from __future__ import annotations

from app.models.campaign_evidence import CampaignEvidence
from app.repositories.base import Repository

campaign_evidence_repository = Repository(CampaignEvidence)

