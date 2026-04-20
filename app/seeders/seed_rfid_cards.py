from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.rfid_card import RfidCard


CARD_STATUSES = ["available", "assigned", "blocked", "lost", "damaged", "inactive"]


def build_rfid_card(index: int) -> dict:
    status = CARD_STATUSES[index % len(CARD_STATUSES)]

    return {
        "uid": f"UID{index + 1:04d}RFID",
        "card_label": f"Badge {index + 1:02d}",
        "status": status,
        "issued_at": datetime.utcnow() - timedelta(days=(index + 1) * 7),
        "notes": f"Carte générée automatiquement #{index + 1}",
    }


def seed_rfid_cards(db: Session, total: int = 20) -> None:
    for i in range(total):
        item = build_rfid_card(i)
        exists = db.query(RfidCard).filter(RfidCard.uid == item["uid"]).first()
        if exists:
            continue

        db.add(RfidCard(**item))

    db.commit()
    print(f"{total} RFID cards seeded successfully.")


def main():
    db = SessionLocal()
    try:
        seed_rfid_cards(db, total=20)
    finally:
        db.close()


if __name__ == "__main__":
    main()