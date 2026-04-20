from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.role import Role
from app.models.staff_user import StaffUser


def seed_admin(db: Session) -> None:
    admin_role = db.query(Role).filter(Role.name == "admin").first()

    if not admin_role:
        raise Exception("Le rôle admin n'existe pas. Lance d'abord seed_roles.")

    existing_admin = db.query(StaffUser).filter(StaffUser.email == "admin@rfid.local").first()
    if existing_admin:
        print("Admin already exists.")
        return

    admin_user = StaffUser(
        role_id=admin_role.id,
        first_name="Super",
        last_name="Admin",
        email="admin@rfid.local",
        password_hash=hash_password("admin1234"),
        is_active=True,
    )

    db.add(admin_user)
    db.commit()

    print("Admin user created successfully.")
    print("Email: admin@rfid.local")
    print("Password: admin1234")


def main():
    db = SessionLocal()
    try:
        seed_admin(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()