from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.rfid_card import (
    create_rfid_card,
    get_rfid_card_by_id,
    uid_exists,
    update_rfid_card,
)
from app.models.rfid_card import RfidCard
from app.schemas.rfid_card import RfidCardCreate, RfidCardUpdate


class RfidCardServiceError(Exception):
    pass


def _handle_rfid_card_integrity_error(db: Session, exc: IntegrityError) -> None:
    db.rollback()

    error_text = str(exc.orig).lower()

    if "uid" in error_text or "duplicate entry" in error_text:
        raise RfidCardServiceError("Cet UID existe déjà.")

    raise RfidCardServiceError(
        "Impossible d’enregistrer cette carte RFID à cause d’une contrainte d’unicité."
    )


def create_rfid_card_service(
    db: Session,
    payload: RfidCardCreate,
) -> RfidCard:
    if uid_exists(db, payload.uid):
        raise RfidCardServiceError("Cet UID existe déjà.")

    try:
        return create_rfid_card(db, payload)
    except IntegrityError as exc:
        _handle_rfid_card_integrity_error(db, exc)


def update_rfid_card_service(
    db: Session,
    rfid_card_id: int,
    payload: RfidCardUpdate,
) -> RfidCard:
    card = get_rfid_card_by_id(db, rfid_card_id)

    if not card:
        raise RfidCardServiceError("Carte RFID introuvable.")

    if uid_exists(db, payload.uid, exclude_card_id=card.id):
        raise RfidCardServiceError("Cet UID existe déjà.")

    try:
        return update_rfid_card(db, card, payload)
    except IntegrityError as exc:
        _handle_rfid_card_integrity_error(db, exc)