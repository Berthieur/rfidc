from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.role import Role
from app.models.staff_user import StaffUser


def seed_agent(db: Session) -> None:
    agent_role = db.query(Role).filter(Role.name == "agent").first()

    if not agent_role:
        raise Exception("Le rôle agent n'existe pas. Lance d'abord seed_roles.")

    existing_agent = db.query(StaffUser).filter(StaffUser.email == "agent@rfid.local").first()
    if existing_agent:
        print("Agent already exists.")
        return

    agent_user = StaffUser(
        role_id=agent_role.id,
        first_name="Test",
        last_name="Agent",
        email="agent@rfid.local",
        password_hash=hash_password("agent1234"),
        is_active=True,
    )

    db.add(agent_user)
    db.commit()

    print("Agent user created successfully.")
    print("Email: agent@rfid.local")
    print("Password: agent1234")


def main():
    db = SessionLocal()
    try:
        seed_agent(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()