from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.staff_user import StaffUser


def get_current_user(request: Request, db: Session = Depends(get_db)) -> StaffUser:
    user_id = request.session.get("user_id")

    print('ici dans get_current_user',user_id)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non authentifié.",
        )

    user = db.query(StaffUser).filter(StaffUser.id == user_id).first()

    if not user:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable.",
        )

    if not user.is_active:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé.",
        )

    return user


def require_admin(current_user: StaffUser = Depends(get_current_user)) -> StaffUser:
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé à l'administrateur.",
        )
    return current_user


def require_agent_or_admin(current_user: StaffUser = Depends(get_current_user)) -> StaffUser:
    if not current_user.role or current_user.role.name not in ["admin", "agent"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé.",
        )
    return current_user