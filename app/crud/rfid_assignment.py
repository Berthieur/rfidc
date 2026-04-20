from sqlalchemy.orm import Session, joinedload

from app.models.rfid_assignment import RfidAssignment
from app.models.authorized_user import AuthorizedUser
from app.models.rfid_card import RfidCard
from app.models.staff_user import StaffUser
from app.schemas.rfid_assignment import RfidAssignmentCreate, RfidAssignmentUpdate


def get_rfid_assignments(db: Session) -> list[RfidAssignment]:
    return (
        db.query(RfidAssignment)
        .options(
            joinedload(RfidAssignment.rfid_card),
            joinedload(RfidAssignment.authorized_user),
            joinedload(RfidAssignment.assigned_by_staff),
        )
        .order_by(RfidAssignment.id.desc())
        .all()
    )


def get_rfid_assignments_paginated(
    db: Session,
    *,
    page: int = 1,
    per_page: int = 10,
    rfid_card_id: int | None = None,
    authorized_user_id: int | None = None,
    assigned_by_staff_id: int | None = None,
    status: str | None = None,
) -> tuple[list[RfidAssignment], int]:
    query = (
        db.query(RfidAssignment)
        .options(
            joinedload(RfidAssignment.rfid_card),
            joinedload(RfidAssignment.authorized_user),
            joinedload(RfidAssignment.assigned_by_staff),
        )
    )

    if rfid_card_id:
        query = query.filter(RfidAssignment.rfid_card_id == rfid_card_id)

    if authorized_user_id:
        query = query.filter(RfidAssignment.authorized_user_id == authorized_user_id)

    if assigned_by_staff_id:
        query = query.filter(RfidAssignment.assigned_by_staff_id == assigned_by_staff_id)

    if status:
        query = query.filter(RfidAssignment.status == status)

    total = query.count()
    offset = (page - 1) * per_page

    assignments = (
        query.order_by(RfidAssignment.id.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return assignments, total


def get_rfid_cards_for_assignment_filter(db: Session) -> list[RfidCard]:
    return db.query(RfidCard).order_by(RfidCard.uid.asc(), RfidCard.id.asc()).all()


def get_authorized_users_for_assignment_filter(db: Session) -> list[AuthorizedUser]:
    return (
        db.query(AuthorizedUser)
        .filter(AuthorizedUser.deleted_at.is_(None))
        .order_by(AuthorizedUser.first_name.asc(), AuthorizedUser.last_name.asc(), AuthorizedUser.id.asc())
        .all()
    )


def get_staff_users_for_assignment_filter(db: Session) -> list[StaffUser]:
    return (
        db.query(StaffUser)
        .filter(StaffUser.is_active.is_(True))
        .order_by(StaffUser.first_name.asc(), StaffUser.last_name.asc(), StaffUser.id.asc())
        .all()
    )


def get_rfid_assignment_by_id(
    db: Session,
    assignment_id: int,
) -> RfidAssignment | None:
    return (
        db.query(RfidAssignment)
        .options(
            joinedload(RfidAssignment.rfid_card),
            joinedload(RfidAssignment.authorized_user),
            joinedload(RfidAssignment.assigned_by_staff),
        )
        .filter(RfidAssignment.id == assignment_id)
        .first()
    )


def get_active_assignment_by_card_id(
    db: Session,
    rfid_card_id: int,
) -> RfidAssignment | None:
    return (
        db.query(RfidAssignment)
        .options(
            joinedload(RfidAssignment.authorized_user),
            joinedload(RfidAssignment.rfid_card),
            joinedload(RfidAssignment.assigned_by_staff),
        )
        .filter(
            RfidAssignment.rfid_card_id == rfid_card_id,
            RfidAssignment.status == "active",
            RfidAssignment.unassigned_at.is_(None),
        )
        .order_by(RfidAssignment.id.desc())
        .first()
    )


def get_active_assignment_by_user_id(
    db: Session,
    authorized_user_id: int,
) -> RfidAssignment | None:
    return (
        db.query(RfidAssignment)
        .filter(
            RfidAssignment.authorized_user_id == authorized_user_id,
            RfidAssignment.status == "active",
            RfidAssignment.unassigned_at.is_(None),
        )
        .order_by(RfidAssignment.id.desc())
        .first()
    )


def create_rfid_assignment(
    db: Session,
    payload: RfidAssignmentCreate,
    assigned_by_staff_id: int,
) -> RfidAssignment:
    data = payload.model_dump()
    data["assigned_by_staff_id"] = assigned_by_staff_id

    if data.get("assigned_at") is None:
        from datetime import datetime
        data["assigned_at"] = datetime.utcnow()

    assignment = RfidAssignment(**data)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return assignment


def update_rfid_assignment(
    db: Session,
    assignment: RfidAssignment,
    payload: RfidAssignmentUpdate,
) -> RfidAssignment:
    data = payload.model_dump()

    for field, value in data.items():
        setattr(assignment, field, value)

    db.commit()
    db.refresh(assignment)

    return assignment