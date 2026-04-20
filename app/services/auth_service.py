from datetime import datetime
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.crud.auth import get_staff_user_by_email
from app.models.staff_user import StaffUser


def authenticate_user(db: Session, email: str, password: str) -> tuple[bool, str | None, StaffUser | None]:
    user = get_staff_user_by_email(db, email)

    if not user:
        return False, "Adresse e-mail ou mot de passe incorrect.", None

    if not user.is_active:
        return False, "Votre compte est désactivé.", None

    if user.locked_until and user.locked_until > datetime.utcnow():
        return False, "Votre compte est temporairement verrouillé.", None

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        db.commit()
        return False, "Adresse e-mail ou mot de passe incorrect.", None

    user.failed_login_attempts = 0
    user.last_login_at = datetime.utcnow()
    db.commit()

    return True, None, user