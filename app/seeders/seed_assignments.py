from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.authorized_user import AuthorizedUser
from app.models.rfid_assignment import RfidAssignment
from app.models.rfid_card import RfidCard
from app.models.staff_user import StaffUser


ASSIGNMENT_STATUSES = ["active", "expired", "unassigned", "revoked"]


def seed_assignments(db: Session, total: int = 20) -> None:
    admin = db.query(StaffUser).filter(StaffUser.email == "admin@rfid.local").first()
    if not admin:
        raise Exception("Admin introuvable. Lance seed_admin d'abord.")

    users = (
        db.query(AuthorizedUser)
        .order_by(AuthorizedUser.id.asc())
        .limit(total)
        .all()
    )

    cards = (
        db.query(RfidCard)
        .order_by(RfidCard.id.asc())
        .limit(total)
        .all()
    )

    max_items = min(len(users), len(cards), total)
    now = datetime.utcnow()

    for i in range(max_items):
        user = users[i]
        card = cards[i]
        status = ASSIGNMENT_STATUSES[i % len(ASSIGNMENT_STATUSES)]

        assigned_at = now - timedelta(days=20 + i)

        if status == "active":
            expired_at = now + timedelta(days=30 + i)
            unassigned_at = None
            card.status = "assigned"
        elif status == "expired":
            expired_at = now - timedelta(days=1 + i)
            unassigned_at = None
            card.status = "available"
        elif status == "unassigned":
            expired_at = None
            unassigned_at = now - timedelta(days=2 + i)
            card.status = "available"
        else:  # revoked
            expired_at = None
            unassigned_at = now - timedelta(days=3 + i)
            card.status = "available"

        exists = (
            db.query(RfidAssignment)
            .filter(
                RfidAssignment.rfid_card_id == card.id,
                RfidAssignment.authorized_user_id == user.id,
            )
            .first()
        )
        if exists:
            continue

        db.add(
            RfidAssignment(
                rfid_card_id=card.id,
                authorized_user_id=user.id,
                assigned_by_staff_id=admin.id,
                assigned_at=assigned_at,
                expired_at=expired_at,
                unassigned_at=unassigned_at,
                status=status,
                notes=f"Affectation générée automatiquement #{i + 1}",
            )
        )

    db.commit()
    print(f"{max_items} assignments seeded successfully.")


def main():
    db = SessionLocal()
    try:
        seed_assignments(db, total=20)
    finally:
        db.close()


if __name__ == "__main__":
    main()