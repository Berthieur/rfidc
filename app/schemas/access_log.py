from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


AccessStatus = Literal["granted", "denied", "ignored"]
AccessDirection = Literal["entry", "exit", "unknown"]


class AccessLogBase(BaseModel):
    device_id: int
    rfid_card_id: int | None = None
    authorized_user_id: int | None = None
    assignment_id: int | None = None
    uid_scanned: str
    access_status: AccessStatus
    access_direction: AccessDirection | None = None
    reason: str | None = None
    scanned_at: datetime | None = None
    door_opened: bool = False

    @field_validator("uid_scanned")
    @classmethod
    def validate_uid_scanned(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("L'UID scanné est obligatoire.")
        return value

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None


class AccessLogCreate(AccessLogBase):
    pass


class AccessLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    rfid_card_id: int | None
    authorized_user_id: int | None
    assignment_id: int | None
    uid_scanned: str
    access_status: AccessStatus
    access_direction: AccessDirection | None
    reason: str | None
    scanned_at: datetime
    door_opened: bool
    created_at: datetime