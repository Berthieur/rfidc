from datetime import datetime

from sqlalchemy.orm import Session

from app.core.security import verify_device_token
from app.crud.access_log import (
    create_access_log,
    get_latest_access_log_for_user,
    get_recent_duplicate_scan,
)
from app.crud.device import get_device_by_code, update_device_last_seen
from app.crud.rfid_assignment import get_active_assignment_by_card_id
from app.crud.rfid_card import get_rfid_card_by_uid
from app.schemas.access_log import AccessLogCreate
from app.schemas.esp32_access import (
    Esp32AccessCheckRequest,
    Esp32AccessCheckResponse,
)


class Esp32AccessServiceError(Exception):
    pass


DUPLICATE_SCAN_WINDOW_SECONDS = 5


def _build_response(
    *,
    decision: str,
    door_opened: bool,
    direction: str,
    reason: str,
    scanned_at: datetime,
    user_id: int | None = None,
    assignment_id: int | None = None,
    card_id: int | None = None,
) -> Esp32AccessCheckResponse:
    return Esp32AccessCheckResponse(
        decision=decision,
        door_opened=door_opened,
        direction=direction,
        reason=reason,
        user_id=user_id,
        assignment_id=assignment_id,
        card_id=card_id,
        scanned_at=scanned_at,
    )


def _log_and_respond(
    db: Session,
    *,
    device_id: int,
    uid_scanned: str,
    scanned_at: datetime,
    decision: str,
    direction: str,
    reason: str,
    door_opened: bool,
    rfid_card_id: int | None = None,
    authorized_user_id: int | None = None,
    assignment_id: int | None = None,
) -> Esp32AccessCheckResponse:
    payload = AccessLogCreate(
        device_id=device_id,
        rfid_card_id=rfid_card_id,
        authorized_user_id=authorized_user_id,
        assignment_id=assignment_id,
        uid_scanned=uid_scanned,
        access_status=decision,
        access_direction=direction,
        reason=reason,
        scanned_at=scanned_at,
        door_opened=door_opened,
    )

    create_access_log(db, payload)

    return _build_response(
        decision=decision,
        door_opened=door_opened,
        direction=direction,
        reason=reason,
        scanned_at=scanned_at,
        user_id=authorized_user_id,
        assignment_id=assignment_id,
        card_id=rfid_card_id,
    )


def _determine_access_direction(db: Session, authorized_user_id: int) -> str:
    latest_log = get_latest_access_log_for_user(db, authorized_user_id)

    if not latest_log:
        return "entry"

    if latest_log.access_direction == "entry":
        return "exit"

    return "entry"


def check_esp32_access_service(
    db: Session,
    *,
    payload: Esp32AccessCheckRequest,
    bearer_token: str,
) -> Esp32AccessCheckResponse:
    
    print('bearer_token : ',bearer_token)

    scanned_at = payload.scanned_at or datetime.utcnow()

    device = get_device_by_code(db, payload.device_code)

    if not device:
        raise Esp32AccessServiceError("Appareil introuvable.")

    if not device.is_active:
        raise Esp32AccessServiceError("Appareil inactif.")

    if not verify_device_token(bearer_token, device.api_token_hash):
        raise Esp32AccessServiceError("Token appareil invalide.")

    update_device_last_seen(db, device)

    duplicate_log = get_recent_duplicate_scan(
        db,
        device_id=device.id,
        uid_scanned=payload.uid,
        within_seconds=DUPLICATE_SCAN_WINDOW_SECONDS,
    )
    if duplicate_log:
        return _log_and_respond(
            db,
            device_id=device.id,
            uid_scanned=payload.uid,
            scanned_at=scanned_at,
            decision="ignored",
            direction="unknown",
            reason="duplicate_scan_ignored",
            door_opened=False,
            rfid_card_id=duplicate_log.rfid_card_id,
            authorized_user_id=duplicate_log.authorized_user_id,
            assignment_id=duplicate_log.assignment_id,
        )

    card = get_rfid_card_by_uid(db, payload.uid)
    if not card:
        return _log_and_respond(
            db,
            device_id=device.id,
            uid_scanned=payload.uid,
            scanned_at=scanned_at,
            decision="denied",
            direction="unknown",
            reason="card_not_found",
            door_opened=False,
        )

    if card.status in {"blocked", "lost", "damaged", "inactive"}:
        return _log_and_respond(
            db,
            device_id=device.id,
            uid_scanned=payload.uid,
            scanned_at=scanned_at,
            decision="denied",
            direction="unknown",
            reason=f"card_{card.status}",
            door_opened=False,
            rfid_card_id=card.id,
        )

    assignment = get_active_assignment_by_card_id(db, card.id)
    if not assignment:
        return _log_and_respond(
            db,
            device_id=device.id,
            uid_scanned=payload.uid,
            scanned_at=scanned_at,
            decision="denied",
            direction="unknown",
            reason="no_active_assignment",
            door_opened=False,
            rfid_card_id=card.id,
        )

    user = assignment.authorized_user
    if not user:
        return _log_and_respond(
            db,
            device_id=device.id,
            uid_scanned=payload.uid,
            scanned_at=scanned_at,
            decision="denied",
            direction="unknown",
            reason="assigned_user_not_found",
            door_opened=False,
            rfid_card_id=card.id,
            assignment_id=assignment.id,
        )

    if user.deleted_at is not None:
        return _log_and_respond(
            db,
            device_id=device.id,
            uid_scanned=payload.uid,
            scanned_at=scanned_at,
            decision="denied",
            direction="unknown",
            reason="user_deleted",
            door_opened=False,
            rfid_card_id=card.id,
            authorized_user_id=user.id,
            assignment_id=assignment.id,
        )

    if not user.is_active:
        return _log_and_respond(
            db,
            device_id=device.id,
            uid_scanned=payload.uid,
            scanned_at=scanned_at,
            decision="denied",
            direction="unknown",
            reason="user_inactive",
            door_opened=False,
            rfid_card_id=card.id,
            authorized_user_id=user.id,
            assignment_id=assignment.id,
        )

    if user.valid_from and scanned_at < user.valid_from:
        return _log_and_respond(
            db,
            device_id=device.id,
            uid_scanned=payload.uid,
            scanned_at=scanned_at,
            decision="denied",
            direction="unknown",
            reason="validity_not_started",
            door_opened=False,
            rfid_card_id=card.id,
            authorized_user_id=user.id,
            assignment_id=assignment.id,
        )

    if user.valid_until and scanned_at > user.valid_until:
        return _log_and_respond(
            db,
            device_id=device.id,
            uid_scanned=payload.uid,
            scanned_at=scanned_at,
            decision="denied",
            direction="unknown",
            reason="validity_expired",
            door_opened=False,
            rfid_card_id=card.id,
            authorized_user_id=user.id,
            assignment_id=assignment.id,
        )

    if assignment.expired_at and scanned_at > assignment.expired_at:
        return _log_and_respond(
            db,
            device_id=device.id,
            uid_scanned=payload.uid,
            scanned_at=scanned_at,
            decision="denied",
            direction="unknown",
            reason="assignment_expired",
            door_opened=False,
            rfid_card_id=card.id,
            authorized_user_id=user.id,
            assignment_id=assignment.id,
        )

    if assignment.unassigned_at is not None or assignment.status != "active":
        return _log_and_respond(
            db,
            device_id=device.id,
            uid_scanned=payload.uid,
            scanned_at=scanned_at,
            decision="denied",
            direction="unknown",
            reason="assignment_not_active",
            door_opened=False,
            rfid_card_id=card.id,
            authorized_user_id=user.id,
            assignment_id=assignment.id,
        )

    direction = _determine_access_direction(db, user.id)

    return _log_and_respond(
        db,
        device_id=device.id,
        uid_scanned=payload.uid,
        scanned_at=scanned_at,
        decision="granted",
        direction=direction,
        reason="access_granted",
        door_opened=True,
        rfid_card_id=card.id,
        authorized_user_id=user.id,
        assignment_id=assignment.id,
    )