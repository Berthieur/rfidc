from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from app.models.access_log import AccessLog
from app.models.authorized_user import AuthorizedUser
from app.models.device import Device
from app.schemas.access_log import AccessLogCreate


def get_access_logs(db: Session) -> list[AccessLog]:
    return (
        db.query(AccessLog)
        .options(
            joinedload(AccessLog.device),
            joinedload(AccessLog.rfid_card),
            joinedload(AccessLog.authorized_user),
            joinedload(AccessLog.assignment),
        )
        .order_by(AccessLog.scanned_at.desc(), AccessLog.id.desc())
        .all()
    )


def get_access_logs_paginated(
    db: Session,
    *,
    page: int = 1,
    per_page: int = 20,
    uid: str | None = None,
    device_id: int | None = None,
    authorized_user_id: int | None = None,
    direction: str | None = None,
    access_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[AccessLog], int]:
    query = (
        db.query(AccessLog)
        .options(
            joinedload(AccessLog.device),
            joinedload(AccessLog.rfid_card),
            joinedload(AccessLog.authorized_user),
            joinedload(AccessLog.assignment),
        )
    )

    if uid:
        query = query.filter(AccessLog.uid_scanned.ilike(f"%{uid.strip()}%"))

    if device_id:
        query = query.filter(AccessLog.device_id == device_id)

    if authorized_user_id:
        query = query.filter(AccessLog.authorized_user_id == authorized_user_id)

    if direction:
        query = query.filter(AccessLog.access_direction == direction)

    if access_status:
        query = query.filter(AccessLog.access_status == access_status)

    if date_from:
        query = query.filter(AccessLog.scanned_at >= date_from)

    if date_to:
        query = query.filter(AccessLog.scanned_at <= date_to)

    total = query.count()

    offset = (page - 1) * per_page

    logs = (
        query.order_by(AccessLog.scanned_at.desc(), AccessLog.id.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return logs, total


def get_devices_for_access_log_filter(db: Session) -> list[Device]:
    return db.query(Device).order_by(Device.device_name.asc(), Device.id.asc()).all()


def get_users_for_access_log_filter(db: Session) -> list[AuthorizedUser]:
    return (
        db.query(AuthorizedUser)
        .filter(AuthorizedUser.deleted_at.is_(None))
        .order_by(AuthorizedUser.first_name.asc(), AuthorizedUser.last_name.asc(), AuthorizedUser.id.asc())
        .all()
    )


def get_access_log_by_id(
    db: Session,
    access_log_id: int,
) -> AccessLog | None:
    return (
        db.query(AccessLog)
        .options(
            joinedload(AccessLog.device),
            joinedload(AccessLog.rfid_card),
            joinedload(AccessLog.authorized_user),
            joinedload(AccessLog.assignment),
        )
        .filter(AccessLog.id == access_log_id)
        .first()
    )


def create_access_log(
    db: Session,
    payload: AccessLogCreate,
) -> AccessLog:
    data = payload.model_dump()

    if data.get("scanned_at") is None:
        data["scanned_at"] = datetime.utcnow()

    access_log = AccessLog(**data)
    db.add(access_log)
    db.commit()
    db.refresh(access_log)

    return access_log


def get_latest_access_log_for_user(
    db: Session,
    authorized_user_id: int,
) -> AccessLog | None:
    return (
        db.query(AccessLog)
        .filter(
            AccessLog.authorized_user_id == authorized_user_id,
            AccessLog.access_status == "granted",
        )
        .order_by(AccessLog.scanned_at.desc(), AccessLog.id.desc())
        .first()
    )


def get_latest_access_log_for_card(
    db: Session,
    rfid_card_id: int,
) -> AccessLog | None:
    return (
        db.query(AccessLog)
        .filter(AccessLog.rfid_card_id == rfid_card_id)
        .order_by(AccessLog.scanned_at.desc(), AccessLog.id.desc())
        .first()
    )


def get_recent_duplicate_scan(
    db: Session,
    *,
    device_id: int,
    uid_scanned: str,
    within_seconds: int = 5,
) -> AccessLog | None:
    threshold = datetime.utcnow() - timedelta(seconds=within_seconds)

    return (
        db.query(AccessLog)
        .filter(
            AccessLog.device_id == device_id,
            AccessLog.uid_scanned == uid_scanned,
            AccessLog.scanned_at >= threshold,
        )
        .order_by(AccessLog.scanned_at.desc(), AccessLog.id.desc())
        .first()
    )