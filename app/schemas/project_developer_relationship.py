from datetime import datetime

from app.schemas.common import ORMModel


class ProjectDeveloperRelationshipRead(ORMModel):
    id: int
    project_id: int
    developer_id: int
    relationship_type: str
    status: str
    source_evidence_id: int | None
    source_url: str
    evidence_text: str
    created_at: datetime
    updated_at: datetime
