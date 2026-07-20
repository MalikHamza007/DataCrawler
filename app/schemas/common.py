from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

NameStr = Annotated[str, Field(min_length=1, max_length=255)]
LongText = Annotated[str, Field(max_length=10000)]
CapturedText = Annotated[str, Field(max_length=20000)]
UrlStr = Annotated[str, Field(min_length=1, max_length=2048, pattern=r"^https?://")]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DeveloperLink(BaseModel):
    developer_id: int | None = None
