from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class DeviceBase(BaseModel):
    device_name: str
    device_code: str
    location: str | None = None
    is_active: bool = True

    @field_validator("device_name", "device_code")
    @classmethod
    def validate_required_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Ce champ est obligatoire.")
        return value

    @field_validator("location")
    @classmethod
    def validate_location(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None


class DeviceCreate(DeviceBase):
    api_token: str | None = None


class DeviceUpdate(BaseModel):
    device_name: str
    device_code: str
    location: str | None = None
    is_active: bool = True

    @field_validator("device_name", "device_code")
    @classmethod
    def validate_required_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Ce champ est obligatoire.")
        return value

    @field_validator("location")
    @classmethod
    def validate_location(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_name: str
    device_code: str
    location: str | None
    is_active: bool
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime