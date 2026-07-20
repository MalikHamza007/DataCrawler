from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class Repository(Generic[ModelT]):
    def __init__(self, model: type[ModelT]) -> None:
        self.model = model

    def get(self, db: Session, item_id: int) -> ModelT | None:
        return db.get(self.model, item_id)

    def list(self, db: Session, *, offset: int = 0, limit: int = 50, filters: dict | None = None) -> list[ModelT]:
        stmt = select(self.model)
        for field, value in (filters or {}).items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, field) == value)
        return list(db.scalars(stmt.offset(offset).limit(limit)).all())

    def create(self, db: Session, data: dict) -> ModelT:
        item = self.model(**data)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def update(self, db: Session, item: ModelT, data: BaseModel | dict) -> ModelT:
        values = data if isinstance(data, dict) else data.model_dump(exclude_unset=True)
        for field, value in values.items():
            setattr(item, field, value)
        db.commit()
        db.refresh(item)
        return item

    def delete(self, db: Session, item: ModelT) -> None:
        db.delete(item)
        db.commit()
