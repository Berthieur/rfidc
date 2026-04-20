from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy import not_

from app.models.rfid_card import RfidCard
from app.schemas.rfid_card import RfidCardCreate, RfidCardUpdate

from app.models.rfid_assignment import RfidAssignment




def get_assignable_rfid_cards(db: Session) -> list[RfidCard]:
    return (
        db.query(RfidCard)
        .filter(
            RfidCard.status.notin_(["blocked", "lost", "damaged", "inactive"])
        )
        .filter(
            ~db.query(RfidAssignment)
            .filter(
                RfidAssignment.rfid_card_id == RfidCard.id,
                RfidAssignment.status == "active",
                RfidAssignment.unassigned_at.is_(None),
            )
            .exists()
        )
        .order_by(RfidCard.uid.asc(), RfidCard.id.asc())
        .all()
    )


def get_rfid_cards_paginated(
    db: Session,
    *,
    page: int = 1,
    per_page: int = 10,
    search: str | None = None,
    status: str | None = None,
) -> tuple[list[RfidCard], int]:
    query = db.query(RfidCard)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                RfidCard.uid.ilike(search_term),
                RfidCard.card_label.ilike(search_term),
                RfidCard.status.ilike(search_term),
            )
        )

    if status:
        query = query.filter(RfidCard.status == status)

    total = query.count()
    offset = (page - 1) * per_page

    cards = (
        query.order_by(RfidCard.id.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return cards, total



def get_rfid_card_by_id(
    db: Session,
    rfid_card_id: int,
) -> RfidCard | None:
    return db.query(RfidCard).filter(RfidCard.id == rfid_card_id).first()


def get_rfid_card_by_uid(
    db: Session,
    uid: str,
) -> RfidCard | None:
    return db.query(RfidCard).filter(RfidCard.uid == uid).first()


def create_rfid_card(
    db: Session,
    payload: RfidCardCreate,
) -> RfidCard:
    data = payload.model_dump()

    rfid_card = RfidCard(**data)
    db.add(rfid_card)
    db.commit()
    db.refresh(rfid_card)

    return rfid_card


def update_rfid_card(
    db: Session,
    rfid_card: RfidCard,
    payload: RfidCardUpdate,
) -> RfidCard:
    data = payload.model_dump()

    for field, value in data.items():
        setattr(rfid_card, field, value)

    db.commit()
    db.refresh(rfid_card)

    return rfid_card


def uid_exists(
    db: Session,
    uid: str,
    exclude_card_id: int | None = None,
) -> bool:
    query = db.query(RfidCard).filter(RfidCard.uid == uid)

    if exclude_card_id is not None:
        query = query.filter(RfidCard.id != exclude_card_id)

    return db.query(query.exists()).scalar()