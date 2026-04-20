from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


RfidCardStatus = Literal["available", "assigned", "lost", "blocked", "damaged", "inactive"]


class RfidCardBase(BaseModel):
    uid: str
    card_label: str | None = None
    status: RfidCardStatus = "available"
    issued_at: datetime | None = None
    notes: str | None = None

    @field_validator("uid")
    @classmethod
    def validate_uid(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("L'UID est obligatoire.")
        return value

    @field_validator("card_label")
    @classmethod
    def validate_card_label(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None


class RfidCardCreate(RfidCardBase):
    pass


class RfidCardUpdate(BaseModel):
    uid: str
    card_label: str | None = None
    status: RfidCardStatus = "available"
    issued_at: datetime | None = None
    notes: str | None = None

    @field_validator("uid")
    @classmethod
    def validate_uid(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("L'UID est obligatoire.")
        return value

    @field_validator("card_label")
    @classmethod
    def validate_card_label(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None


class RfidCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uid: str
    card_label: str | None
    status: RfidCardStatus
    issued_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime