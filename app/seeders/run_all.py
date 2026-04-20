from app.core.database import SessionLocal
from app.seeders.seed_roles import seed_roles
from app.seeders.seed_admin import seed_admin
from app.seeders.seed_agent import seed_agent
from app.seeders.seed_authorized_users import seed_authorized_users
from app.seeders.seed_rfid_cards import seed_rfid_cards
from app.seeders.seed_devices import seed_devices
from app.seeders.seed_assignments import seed_assignments
from app.seeders.seed_access_logs import seed_access_logs


def main():
    db = SessionLocal()
    try:
        seed_roles(db)
        seed_admin(db)
        seed_agent(db)
        seed_authorized_users(db, total=20)
        seed_rfid_cards(db, total=20)
        seed_devices(db, total=20)
        seed_assignments(db, total=20)
        seed_access_logs(db, total=20)
        print("All seeders executed successfully.")
    except Exception as e:
        print("Une erreur est survenue durant l'execution des seeds :", e)
    finally:
        db.close()


if __name__ == "__main__":
    main()

#Pour les lances : "python -m app.seeders.run_all"