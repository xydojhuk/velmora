from pydantic import Field

from app.schemas.common import CleanTextModel


class VisitCreate(CleanTextModel):
    page: str = Field(min_length=1, max_length=300)
    referrer: str | None = Field(default=None, max_length=1000)
    session_id: str | None = Field(default=None, max_length=120)
