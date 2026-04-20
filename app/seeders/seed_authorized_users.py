from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.authorized_user import AuthorizedUser


FIRST_NAMES = [
    "Jean", "Sarah", "Mickael", "Lina", "Paul",
    "Anna", "David", "Fara", "Lucas", "Nina",
    "Eric", "Mialy", "Tiana", "Joel", "Kevin",
    "Sandra", "Hery", "Aina", "Rado", "Elisa",
]

LAST_NAMES = [
    "Rakoto", "Rabe", "Andriam", "Ranaivo", "Rasolo",
    "Andry", "Randria", "Razaka", "Ravelo", "Raman",
    "Rasoana", "Rija", "Tahina", "Miora", "Sitraka",
    "Fenosoa", "Nirina", "Haja", "Malala", "Soa",
]

GENDERS = ["Homme", "Femme"]


def build_authorized_user(index: int) -> dict:
    now = datetime.utcnow()

    first_name = FIRST_NAMES[index % len(FIRST_NAMES)]
    last_name = LAST_NAMES[index % len(LAST_NAMES)]
    gender = GENDERS[index % 2]

    validity_mode = index % 4
    if validity_mode == 0:
        valid_from = now - timedelta(days=30 + index)
        valid_until = now + timedelta(days=90 + index)
    elif validity_mode == 1:
        valid_from = now - timedelta(days=10 + index)
        valid_until = now + timedelta(days=15 + index)
    elif validity_mode == 2:
        valid_from = None
        valid_until = None
    else:
        valid_from = now - timedelta(days=60 + index)
        valid_until = now - timedelta(days=1 + index)

    is_active = (index % 5 != 0)

    return {
        "first_name": first_name,
        "last_name": last_name,
        "gender": gender,
        "phone": f"+26134{index + 100000:06d}",
        "email": f"user{index + 1:02d}@test.local",
        "reference_code": f"USR{index + 1:03d}",
        "valid_from": valid_from,
        "valid_until": valid_until,
        "is_active": is_active,
        "notes": f"Utilisateur généré automatiquement #{index + 1}",
    }


def seed_authorized_users(db: Session, total: int = 20) -> None:
    for i in range(total):
        item = build_authorized_user(i)
        exists = (
            db.query(AuthorizedUser)
            .filter(AuthorizedUser.reference_code == item["reference_code"])
            .first()
        )
        if exists:
            continue

        db.add(AuthorizedUser(**item))

    db.commit()
    print(f"{total} authorized users seeded successfully.")


def main():
    db = SessionLocal()
    try:
        seed_authorized_users(db, total=20)
    finally:
        db.close()


if __name__ == "__main__":
    main()