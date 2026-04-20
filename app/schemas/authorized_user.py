from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from typing import Literal
import re

GenderType = Literal["Homme", "Femme"]
PHONE_REGEX = re.compile(r"^\+[0-9]{8,15}$")

class AuthorizedUserBase(BaseModel):
    first_name: str
    last_name: str
    gender: GenderType
    phone: str | None = None
    email: EmailStr | None = None
    reference_code: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool = True
    notes: str | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_required_names(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Ce champ est obligatoire.")
        return value

    @field_validator("reference_code")
    @classmethod
    def validate_reference_code(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        if not value:
            return None

        if not PHONE_REGEX.fullmatch(value):
            raise ValueError(
                "Le téléphone doit commencer par + et contenir uniquement 8 à 15 chiffres."
            )

        return value

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None

    @field_validator("valid_until")
    @classmethod
    def validate_validity_dates(cls, value: datetime | None, info):
        valid_from = info.data.get("valid_from")
        if value and valid_from and value < valid_from:
            raise ValueError("La date de fin ne peut pas être antérieure à la date de début.")
        return value


class AuthorizedUserCreate(AuthorizedUserBase):
    pass


class AuthorizedUserUpdate(BaseModel):
    first_name: str
    last_name: str
    gender: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    reference_code: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool = True
    notes: str | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_required_names(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Ce champ est obligatoire.")
        return value

    @field_validator("reference_code")
    @classmethod
    def validate_reference_code(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
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

    @field_validator("valid_until")
    @classmethod
    def validate_validity_dates(cls, value: datetime | None, info):
        valid_from = info.data.get("valid_from")
        if value and valid_from and value < valid_from:
            raise ValueError("La date de fin ne peut pas être antérieure à la date de début.")
        return value


class AuthorizedUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    gender: str | None
    phone: str | None
    email: EmailStr | None
    reference_code: str | None
    valid_from: datetime | None
    valid_until: datetime | None
    is_active: bool
    deleted_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime