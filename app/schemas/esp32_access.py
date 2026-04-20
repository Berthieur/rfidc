from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


Esp32Decision = Literal["granted", "denied", "ignored"]
Esp32Direction = Literal["entry", "exit", "unknown"]


class Esp32AccessCheckRequest(BaseModel):
    device_code: str
    uid: str
    scanned_at: datetime | None = None

    @field_validator("device_code", "uid")
    @classmethod
    def validate_required_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Ce champ est obligatoire.")
        return value


class Esp32AccessCheckResponse(BaseModel):
    decision: Esp32Decision
    door_opened: bool
    direction: Esp32Direction
    reason: str
    user_id: int | None = None
    assignment_id: int | None = None
    card_id: int | None = None
    scanned_at: datetime