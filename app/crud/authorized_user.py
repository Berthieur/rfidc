from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.authorized_user import AuthorizedUser
from app.schemas.authorized_user import AuthorizedUserCreate, AuthorizedUserUpdate


def get_authorized_users(
    db: Session,
    search: str | None = None,
    include_deleted: bool = False,
) -> list[AuthorizedUser]:
    query = db.query(AuthorizedUser)

    if not include_deleted:
        query = query.filter(AuthorizedUser.deleted_at.is_(None))

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                AuthorizedUser.first_name.ilike(search_term),
                AuthorizedUser.last_name.ilike(search_term),
                AuthorizedUser.email.ilike(search_term),
                AuthorizedUser.phone.ilike(search_term),
                AuthorizedUser.reference_code.ilike(search_term),
            )
        )

    return query.order_by(AuthorizedUser.id.desc()).all()


def get_authorized_users_paginated(
    db: Session,
    *,
    page: int = 1,
    per_page: int = 10,
    search: str | None = None,
    is_active: str | None = None,
    validity: str | None = None,
    include_deleted: bool = False,
) -> tuple[list[AuthorizedUser], int]:
    query = db.query(AuthorizedUser)

    if not include_deleted:
        query = query.filter(AuthorizedUser.deleted_at.is_(None))

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                AuthorizedUser.first_name.ilike(search_term),
                AuthorizedUser.last_name.ilike(search_term),
                AuthorizedUser.email.ilike(search_term),
                AuthorizedUser.phone.ilike(search_term),
                AuthorizedUser.reference_code.ilike(search_term),
            )
        )

    if is_active == "active":
        query = query.filter(AuthorizedUser.is_active.is_(True))
    elif is_active == "inactive":
        query = query.filter(AuthorizedUser.is_active.is_(False))

    if validity == "with_validity":
        query = query.filter(
            or_(
                AuthorizedUser.valid_from.is_not(None),
                AuthorizedUser.valid_until.is_not(None),
            )
        )
    elif validity == "without_validity":
        query = query.filter(
            AuthorizedUser.valid_from.is_(None),
            AuthorizedUser.valid_until.is_(None),
        )

    total = query.count()
    offset = (page - 1) * per_page

    users = (
        query.order_by(AuthorizedUser.id.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return users, total


def get_authorized_user_by_id(
    db: Session,
    authorized_user_id: int,
    include_deleted: bool = False,
) -> AuthorizedUser | None:
    query = db.query(AuthorizedUser).filter(AuthorizedUser.id == authorized_user_id)

    if not include_deleted:
        query = query.filter(AuthorizedUser.deleted_at.is_(None))

    return query.first()


def get_authorized_user_by_reference_code(
    db: Session,
    reference_code: str,
) -> AuthorizedUser | None:
    return (
        db.query(AuthorizedUser)
        .filter(
            AuthorizedUser.reference_code == reference_code,
            AuthorizedUser.deleted_at.is_(None),
        )
        .first()
    )


def get_authorized_user_by_email(
    db: Session,
    email: str,
    exclude_user_id: int | None = None,
) -> AuthorizedUser | None:
    query = db.query(AuthorizedUser).filter(
        AuthorizedUser.email == email,
        AuthorizedUser.deleted_at.is_(None),
    )

    if exclude_user_id is not None:
        query = query.filter(AuthorizedUser.id != exclude_user_id)

    return query.first()


def get_authorized_user_by_phone(
    db: Session,
    phone: str,
    exclude_user_id: int | None = None,
) -> AuthorizedUser | None:
    query = db.query(AuthorizedUser).filter(
        AuthorizedUser.phone == phone,
        AuthorizedUser.deleted_at.is_(None),
    )

    if exclude_user_id is not None:
        query = query.filter(AuthorizedUser.id != exclude_user_id)

    return query.first()


def create_authorized_user(
    db: Session,
    payload: AuthorizedUserCreate,
) -> AuthorizedUser:
    data = payload.model_dump()

    authorized_user = AuthorizedUser(**data)
    db.add(authorized_user)
    db.commit()
    db.refresh(authorized_user)

    return authorized_user


def update_authorized_user(
    db: Session,
    authorized_user: AuthorizedUser,
    payload: AuthorizedUserUpdate,
) -> AuthorizedUser:
    data = payload.model_dump()

    for field, value in data.items():
        setattr(authorized_user, field, value)

    db.commit()
    db.refresh(authorized_user)

    return authorized_user


def soft_delete_authorized_user(
    db: Session,
    authorized_user: AuthorizedUser,
) -> AuthorizedUser:
    from datetime import datetime

    authorized_user.deleted_at = datetime.utcnow()
    authorized_user.is_active = False

    db.commit()
    db.refresh(authorized_user)

    return authorized_user


def reference_code_exists(
    db: Session,
    reference_code: str,
    exclude_user_id: int | None = None,
) -> bool:
    query = db.query(AuthorizedUser).filter(
        AuthorizedUser.reference_code == reference_code,
        AuthorizedUser.deleted_at.is_(None),
    )

    if exclude_user_id is not None:
        query = query.filter(AuthorizedUser.id != exclude_user_id)

    return db.query(query.exists()).scalar()


def email_exists(
    db: Session,
    email: str,
    exclude_user_id: int | None = None,
) -> bool:
    query = db.query(AuthorizedUser).filter(
        AuthorizedUser.email == email,
        AuthorizedUser.deleted_at.is_(None),
    )

    if exclude_user_id is not None:
        query = query.filter(AuthorizedUser.id != exclude_user_id)

    return db.query(query.exists()).scalar()


def phone_exists(
    db: Session,
    phone: str,
    exclude_user_id: int | None = None,
) -> bool:
    query = db.query(AuthorizedUser).filter(
        AuthorizedUser.phone == phone,
        AuthorizedUser.deleted_at.is_(None),
    )

    if exclude_user_id is not None:
        query = query.filter(AuthorizedUser.id != exclude_user_id)

    return db.query(query.exists()).scalar()