from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_device_token
from app.crud.device import (
    create_device,
    device_code_exists,
    get_device_by_id,
    update_device,
    update_device_token_hash,
)
from app.models.device import Device
from app.schemas.device import DeviceCreate, DeviceUpdate
from app.utils.helpers import generate_device_token


class DeviceServiceError(Exception):
    pass


def _handle_device_integrity_error(db: Session, exc: IntegrityError) -> None:
    db.rollback()

    error_text = str(exc.orig).lower()

    if "device_code" in error_text or "duplicate entry" in error_text:
        raise DeviceServiceError("Ce code appareil existe déjà.")

    raise DeviceServiceError(
        "Impossible d’enregistrer cet appareil à cause d’une contrainte d’unicité."
    )


def create_device_service(
    db: Session,
    payload: DeviceCreate,
) -> tuple[Device, str]:
    if device_code_exists(db, payload.device_code):
        raise DeviceServiceError("Ce code appareil existe déjà.")

    plain_token = payload.api_token if payload.api_token else generate_device_token()
    api_token_hash = hash_device_token(plain_token)

    try:
        device = create_device(
            db,
            device_name=payload.device_name,
            device_code=payload.device_code,
            api_token_hash=api_token_hash,
            location=payload.location,
            is_active=payload.is_active,
        )
    except IntegrityError as exc:
        _handle_device_integrity_error(db, exc)

    return device, plain_token


def update_device_service(
    db: Session,
    device_id: int,
    payload: DeviceUpdate,
) -> Device:
    device = get_device_by_id(db, device_id)

    if not device:
        raise DeviceServiceError("Appareil introuvable.")

    if device_code_exists(db, payload.device_code, exclude_device_id=device.id):
        raise DeviceServiceError("Ce code appareil existe déjà.")

    try:
        return update_device(
            db,
            device,
            device_name=payload.device_name,
            device_code=payload.device_code,
            location=payload.location,
            is_active=payload.is_active,
        )
    except IntegrityError as exc:
        _handle_device_integrity_error(db, exc)


def regenerate_device_token_service(
    db: Session,
    device_id: int,
) -> tuple[Device, str]:
    device = get_device_by_id(db, device_id)

    if not device:
        raise DeviceServiceError("Appareil introuvable.")

    plain_token = generate_device_token()
    api_token_hash = hash_device_token(plain_token)

    updated_device = update_device_token_hash(db, device, api_token_hash)

    return updated_device, plain_token