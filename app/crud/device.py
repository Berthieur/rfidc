from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.device import Device


def get_devices(
    db: Session,
    search: str | None = None,
) -> list[Device]:
    query = db.query(Device)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Device.device_name.ilike(search_term),
                Device.device_code.ilike(search_term),
                Device.location.ilike(search_term),
            )
        )

    return query.order_by(Device.id.desc()).all()


def get_devices_paginated(
    db: Session,
    *,
    page: int = 1,
    per_page: int = 10,
    search: str | None = None,
    is_active: str | None = None,
) -> tuple[list[Device], int]:
    query = db.query(Device)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Device.device_name.ilike(search_term),
                Device.device_code.ilike(search_term),
                Device.location.ilike(search_term),
            )
        )

    if is_active == "active":
        query = query.filter(Device.is_active.is_(True))
    elif is_active == "inactive":
        query = query.filter(Device.is_active.is_(False))

    total = query.count()
    offset = (page - 1) * per_page

    devices = (
        query.order_by(Device.id.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return devices, total


def get_device_by_id(
    db: Session,
    device_id: int,
) -> Device | None:
    return db.query(Device).filter(Device.id == device_id).first()


def get_device_by_code(
    db: Session,
    device_code: str,
) -> Device | None:
    return db.query(Device).filter(Device.device_code == device_code).first()


def create_device(
    db: Session,
    *,
    device_name: str,
    device_code: str,
    api_token_hash: str,
    location: str | None = None,
    is_active: bool = True,
) -> Device:
    device = Device(
        device_name=device_name,
        device_code=device_code,
        api_token_hash=api_token_hash,
        location=location,
        is_active=is_active,
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    return device


def update_device(
    db: Session,
    device: Device,
    *,
    device_name: str,
    device_code: str,
    location: str | None,
    is_active: bool,
) -> Device:
    device.device_name = device_name
    device.device_code = device_code
    device.location = location
    device.is_active = is_active
    device.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(device)

    return device


def update_device_token_hash(
    db: Session,
    device: Device,
    api_token_hash: str,
) -> Device:
    db.query(Device).filter(Device.id == device.id).update(
        {
            Device.api_token_hash: api_token_hash,
            Device.updated_at: datetime.utcnow(),
        },
        synchronize_session=False,
    )
    db.commit()

    updated_device = db.query(Device).filter(Device.id == device.id).first()
    return updated_device


def update_device_last_seen(
    db: Session,
    device: Device,
) -> Device:
    device.last_seen_at = datetime.utcnow()
    device.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(device)

    return device


def device_code_exists(
    db: Session,
    device_code: str,
    exclude_device_id: int | None = None,
) -> bool:
    query = db.query(Device).filter(Device.device_code == device_code)

    if exclude_device_id is not None:
        query = query.filter(Device.id != exclude_device_id)

    return db.query(query.exists()).scalar()