import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import CleanTextModel, ORMModel


class IconAssetRead(ORMModel):
    id: uuid.UUID
    key: str
    label: str
    svg_markup: str
    original_name: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime


class PublicIconAsset(ORMModel):
    key: str
    label: str
    svg_markup: str


class IconAssetUpdate(CleanTextModel):
    label: str = Field(min_length=1, max_length=120)
