from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.access_log import AccessLog
from app.models.device import Device
from app.models.rfid_assignment import RfidAssignment


ACCESS_STATUSES = ["granted", "denied", "ignored"]
DIRECTIONS = ["entry", "exit", "unknown"]
REASONS = [
    "access_granted",
    "card_not_found",
    "user_inactive",
    "assignment_expired",
    "duplicate_scan_ignored",
]


def seed_access_logs(db: Session, total: int = 20) -> None:
    devices = db.query(Device).order_by(Device.id.asc()).all()
    assignments = (
        db.query(RfidAssignment)
        .order_by(RfidAssignment.id.asc())
        .all()
    )

    if not devices:
        raise Exception("Aucun device trouvé. Lance seed_devices d'abord.")

    if not assignments:
        raise Exception("Aucune affectation trouvée. Lance seed_assignments d'abord.")

    now = datetime.utcnow()

    for i in range(total):
        device = devices[i % len(devices)]
        assignment = assignments[i % len(assignments)]
        status = ACCESS_STATUSES[i % len(ACCESS_STATUSES)]
        direction = DIRECTIONS[i % len(DIRECTIONS)]
        reason = REASONS[i % len(REASONS)]
        scanned_at = now - timedelta(minutes=(i + 1) * 7)

        uid_scanned = (
            assignment.rfid_card.uid
            if assignment.rfid_card and status != "denied"
            else f"UNKNOWN_{i + 1:03d}"
        )

        exists = (
            db.query(AccessLog)
            .filter(
                AccessLog.device_id == device.id,
                AccessLog.uid_scanned == uid_scanned,
                AccessLog.scanned_at == scanned_at,
            )
            .first()
        )
        if exists:
            continue

        db.add(
            AccessLog(
                device_id=device.id,
                rfid_card_id=assignment.rfid_card_id if status != "denied" else None,
                authorized_user_id=assignment.authorized_user_id if status != "denied" else None,
                assignment_id=assignment.id if status != "denied" else None,
                uid_scanned=uid_scanned,
                access_status=status,
                access_direction=direction,
                reason=reason,
                scanned_at=scanned_at,
                door_opened=(status == "granted"),
            )
        )

    db.commit()
    print(f"{total} access logs seeded successfully.")


def main():
    db = SessionLocal()
    try:
        seed_access_logs(db, total=20)
    finally:
        db.close()


if __name__ == "__main__":
    main()