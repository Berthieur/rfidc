from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


RfidAssignmentStatus = Literal["active", "expired", "unassigned", "revoked"]


class RfidAssignmentBase(BaseModel):
    rfid_card_id: int
    authorized_user_id: int
    assigned_at: datetime | None = None
    expired_at: datetime | None = None
    unassigned_at: datetime | None = None
    status: RfidAssignmentStatus = "active"
    notes: str | None = None

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None

    @field_validator("expired_at")
    @classmethod
    def validate_expired_at(cls, value: datetime | None, info):
        assigned_at = info.data.get("assigned_at")
        if value and assigned_at and value < assigned_at:
            raise ValueError("La date d'expiration ne peut pas être antérieure à la date d'attribution.")
        return value

    @field_validator("unassigned_at")
    @classmethod
    def validate_unassigned_at(cls, value: datetime | None, info):
        assigned_at = info.data.get("assigned_at")
        if value and assigned_at and value < assigned_at:
            raise ValueError("La date de retrait ne peut pas être antérieure à la date d'attribution.")
        return value


class RfidAssignmentCreate(RfidAssignmentBase):
    pass


class RfidAssignmentUpdate(BaseModel):
    expired_at: datetime | None = None
    unassigned_at: datetime | None = None
    status: RfidAssignmentStatus
    notes: str | None = None

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None


class RfidAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rfid_card_id: int
    authorized_user_id: int
    assigned_by_staff_id: int
    assigned_at: datetime
    expired_at: datetime | None
    unassigned_at: datetime | None
    status: RfidAssignmentStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime