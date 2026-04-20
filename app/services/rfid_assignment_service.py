from datetime import datetime

from sqlalchemy.orm import Session

from app.crud.authorized_user import get_authorized_user_by_id
from app.crud.rfid_assignment import (
    create_rfid_assignment,
    get_active_assignment_by_card_id,
    get_rfid_assignment_by_id,
)
from app.crud.rfid_card import get_rfid_card_by_id
from app.models.rfid_assignment import RfidAssignment
from app.schemas.rfid_assignment import RfidAssignmentCreate


class RfidAssignmentServiceError(Exception):
    pass


def create_rfid_assignment_service(
    db: Session,
    payload: RfidAssignmentCreate,
    assigned_by_staff_id: int,
) -> RfidAssignment:
    card = get_rfid_card_by_id(db, payload.rfid_card_id)
    if not card:
        raise RfidAssignmentServiceError("Carte RFID introuvable.")

    user = get_authorized_user_by_id(db, payload.authorized_user_id)
    if not user:
        raise RfidAssignmentServiceError("Utilisateur autorisé introuvable.")

    if card.status in ["blocked", "lost", "damaged", "inactive"]:
        raise RfidAssignmentServiceError(
            "Cette carte ne peut pas être attribuée dans son état actuel."
        )

    active_assignment = get_active_assignment_by_card_id(db, card.id)
    if active_assignment:
        raise RfidAssignmentServiceError(
            "Cette carte possède déjà une affectation active."
        )

    assignment = create_rfid_assignment(
        db,
        payload,
        assigned_by_staff_id=assigned_by_staff_id,
    )

    # Si tu veux garder assigned comme info visuelle
    card.status = "assigned"
    db.commit()
    db.refresh(card)

    return assignment


def unassign_rfid_assignment_service(
    db: Session,
    assignment_id: int,
    notes: str | None = None,
) -> RfidAssignment:
    assignment = get_rfid_assignment_by_id(db, assignment_id)
    if not assignment:
        raise RfidAssignmentServiceError("Affectation introuvable.")

    if assignment.status != "active":
        raise RfidAssignmentServiceError("Seule une affectation active peut être retirée.")

    assignment.status = "unassigned"
    assignment.unassigned_at = datetime.utcnow()
    if notes:
        assignment.notes = notes

    if assignment.rfid_card:
        assignment.rfid_card.status = "available"

    db.commit()
    db.refresh(assignment)
    return assignment


def revoke_rfid_assignment_service(
    db: Session,
    assignment_id: int,
    notes: str | None = None,
) -> RfidAssignment:
    assignment = get_rfid_assignment_by_id(db, assignment_id)
    if not assignment:
        raise RfidAssignmentServiceError("Affectation introuvable.")

    if assignment.status != "active":
        raise RfidAssignmentServiceError("Seule une affectation active peut être révoquée.")

    assignment.status = "revoked"
    assignment.unassigned_at = datetime.utcnow()
    if notes:
        assignment.notes = notes

    if assignment.rfid_card:
        assignment.rfid_card.status = "available"

    db.commit()
    db.refresh(assignment)
    return assignment


def expire_rfid_assignment_service(
    db: Session,
    assignment_id: int,
    notes: str | None = None,
) -> RfidAssignment:
    assignment = get_rfid_assignment_by_id(db, assignment_id)
    if not assignment:
        raise RfidAssignmentServiceError("Affectation introuvable.")

    if assignment.status != "active":
        raise RfidAssignmentServiceError("Seule une affectation active peut être expirée.")

    assignment.status = "expired"
    assignment.expired_at = datetime.utcnow()
    if notes:
        assignment.notes = notes

    if assignment.rfid_card:
        assignment.rfid_card.status = "available"

    db.commit()
    db.refresh(assignment)
    return assignment