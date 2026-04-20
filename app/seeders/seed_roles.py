from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.role import Role


def seed_roles(db: Session) -> None:
    roles_to_create = [
        {"name": "admin", "description": "Administrateur de la plateforme"},
        {"name": "agent", "description": "Agent de consultation et de gestion"},
    ]

    for role_data in roles_to_create:
        existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing_role:
            role = Role(**role_data)
            db.add(role)

    db.commit()


def main():
    db = SessionLocal()
    try:
        seed_roles(db)
        print("Roles seeded successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()