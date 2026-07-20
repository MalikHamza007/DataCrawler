from __future__ import annotations

from sqlalchemy.orm import Session


def init_db(_: Session) -> None:
    """Database schema is managed by Alembic, not create_all()."""
