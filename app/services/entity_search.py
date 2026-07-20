from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.developer import Developer
from app.models.project import Project
from app.schemas.social_capture import EntitySearchItem, EntitySearchResponse


def search_entities(
    db: Session,
    *,
    q: str,
    entity_type: str,
    limit: int,
    include_merged: bool,
) -> EntitySearchResponse:
    text = q.strip()
    if not text:
        return EntitySearchResponse(items=[])
    capped_limit = min(limit, 25)
    items: list[EntitySearchItem] = []
    pattern = f"%{text}%"
    if entity_type in {"developer", "all"}:
        stmt = select(Developer).where(or_(Developer.name.ilike(pattern), Developer.legal_name.ilike(pattern)))
        if not include_merged:
            stmt = stmt.where(Developer.record_status == "active")
        for developer in db.scalars(stmt.order_by(Developer.name).limit(capped_limit)).all():
            items.append(EntitySearchItem(entity_type="developer", id=developer.id, name=developer.name, subtitle=developer.city, classification=developer.classification, record_status=developer.record_status))
    if entity_type in {"project", "all"} and len(items) < capped_limit:
        stmt = select(Project).where(or_(Project.name.ilike(pattern), Project.address.ilike(pattern), Project.lahore_zone.ilike(pattern)))
        if not include_merged:
            stmt = stmt.where(Project.record_status == "active")
        for project in db.scalars(stmt.order_by(Project.name).limit(capped_limit - len(items))).all():
            subtitle = project.lahore_zone or project.address or project.city
            items.append(EntitySearchItem(entity_type="project", id=project.id, name=project.name, subtitle=subtitle, classification=getattr(project, "classification", None), record_status=project.record_status))
    return EntitySearchResponse(items=items)

