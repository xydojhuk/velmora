import re

from pydantic import BaseModel, ConfigDict, field_validator

from app.utils import clean_text


_slug_re = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CleanTextModel(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def strip_control_chars(cls, value):
        if isinstance(value, str):
            return clean_text(value)
        return value


def validate_slug(value: str) -> str:
    value = value.strip().lower()
    if not _slug_re.fullmatch(value):
        raise ValueError("The page slug may contain only lowercase Latin letters, digits and hyphens")
    return value
