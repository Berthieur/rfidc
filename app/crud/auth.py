from sqlalchemy.orm import Session

from app.models.staff_user import StaffUser


def get_staff_user_by_email(db: Session, email: str) -> StaffUser | None:
    return db.query(StaffUser).filter(StaffUser.email == email).first()