from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_device_token
from app.models.device import Device


LOCATIONS = [
    "Entrée principale",
    "Sortie principale",
    "Bureau administratif",
    "Salle technique",
    "Stock",
    "Salle serveur",
    "Porte nord",
    "Porte sud",
    "Porte est",
    "Porte ouest",
]


def build_device(index: int) -> dict:
    device_code = f"ESP32_DEVICE_{index + 1:03d}"
    return {
        "device_name": f"ESP32 Porte {index + 1:02d}",
        "device_code": device_code,
        "api_token_hash": hash_device_token(f"token_device_{index + 1:03d}"),
        "location": LOCATIONS[index % len(LOCATIONS)],
        "is_active": (index % 4 != 0),
    }


def seed_devices(db: Session, total: int = 20) -> None:
    for i in range(total):
        item = build_device(i)
        exists = db.query(Device).filter(Device.device_code == item["device_code"]).first()
        if exists:
            continue

        db.add(Device(**item))

    db.commit()
    print(f"{total} devices seeded successfully.")


def main():
    db = SessionLocal()
    try:
        seed_devices(db, total=20)
    finally:
        db.close()


if __name__ == "__main__":
    main()