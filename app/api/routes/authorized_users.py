from datetime import datetime

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import require_admin, require_agent_or_admin
from app.crud.authorized_user import (
    get_authorized_user_by_id,
    get_authorized_users_paginated,
)
from app.models.staff_user import StaffUser
from app.schemas.authorized_user import AuthorizedUserCreate, AuthorizedUserOut, AuthorizedUserUpdate
from app.services.authorized_user_service import (
    AuthorizedUserServiceError,
    create_authorized_user_service,
    soft_delete_authorized_user_service,
    update_authorized_user_service,
)

router = APIRouter()
templates = Jinja2Templates(directory=settings.template_path)

DEFAULT_PER_PAGE = 10


def parse_optional_datetime(value: str | None) -> datetime | None:
    if not value or not value.strip():
        return None
    return datetime.fromisoformat(value)


def clean_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


@router.get("/authorized-users", name="authorized_users.index", response_class=HTMLResponse)
def authorized_users_index(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=100),
    search: str | None = Query(default=None),
    is_active: str | None = Query(default=None),
    validity: str | None = Query(default=None),
    format: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    users, total = get_authorized_users_paginated(
        db,
        page=page,
        per_page=per_page,
        search=search,
        is_active=is_active,
        validity=validity,
    )

    total_pages = max(1, (total + per_page - 1) // per_page)

    # ── JSON pour Flutter ──────────────────────────────────────────────────────
    if format == "json":
        items = [AuthorizedUserOut.model_validate(u).model_dump(mode="json") for u in users]
        return JSONResponse({
            "items": items,
            "total": total,
            "page": page,
            "total_pages": total_pages,
        })

    # ── HTML pour navigateur ───────────────────────────────────────────────────
    has_previous = page > 1
    has_next = page < total_pages
    page_numbers = list(range(max(1, page - 2), min(total_pages, page + 2) + 1))
    filters = {"search": search or "", "is_active": is_active or "", "validity": validity or ""}

    return templates.TemplateResponse(
        request=request,
        name="authorized_users/index.html",
        context={
            "request": request,
            "users": users,
            "filters": filters,
            "current_page": page,
            "total": total,
            "total_pages": total_pages,
            "has_previous": has_previous,
            "has_next": has_next,
            "previous_page": page - 1,
            "next_page": page + 1,
            "page_numbers": page_numbers,
            "current_user": current_user,
        },
    )


# ── JSON REST endpoints for Flutter ───────────────────────────────────────────

@router.post("/authorized-users", name="authorized_users.api.create")
async def authorized_users_api_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    """Création via JSON (Flutter)."""
    body = await request.json()
    try:
        payload = AuthorizedUserCreate(**body)
        user = create_authorized_user_service(db, payload)
        return JSONResponse(AuthorizedUserOut.model_validate(user).model_dump(mode="json"), status_code=201)
    except (ValidationError, AuthorizedUserServiceError) as e:
        return JSONResponse({"detail": str(e)}, status_code=400)


@router.put("/authorized-users/{authorized_user_id}", name="authorized_users.api.update")
async def authorized_users_api_update(
    authorized_user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    """Mise à jour via JSON (Flutter)."""
    body = await request.json()
    try:
        payload = AuthorizedUserUpdate(**body)
        user = update_authorized_user_service(db, authorized_user_id, payload)
        return JSONResponse(AuthorizedUserOut.model_validate(user).model_dump(mode="json"))
    except (ValidationError, AuthorizedUserServiceError) as e:
        return JSONResponse({"detail": str(e)}, status_code=400)


@router.delete("/authorized-users/{authorized_user_id}", name="authorized_users.api.delete")
def authorized_users_api_delete(
    authorized_user_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    """Suppression douce via JSON (Flutter)."""
    try:
        soft_delete_authorized_user_service(db, authorized_user_id)
        return JSONResponse({"success": True})
    except AuthorizedUserServiceError as e:
        return JSONResponse({"detail": str(e)}, status_code=400)


# ── HTML web endpoints ─────────────────────────────────────────────────────────

@router.get("/authorized-users/create", name="authorized_users.create.index", response_class=HTMLResponse)
def authorized_users_create_page(
    request: Request,
    current_user: StaffUser = Depends(require_admin),
):
    now = datetime.now()
    request.state.now = now
    return templates.TemplateResponse(
        request=request,
        name="authorized_users/create.html",
        context={"request": request, "error": None, "form_data": {}, "current_user": current_user},
    )


@router.post("/authorized-users/create", name="authorized_users.create.store", response_class=HTMLResponse)
def authorized_users_store(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    gender: str | None = Form(None),
    phone: str | None = Form(None),
    email: str | None = Form(None),
    reference_code: str | None = Form(None),
    valid_from: str | None = Form(None),
    valid_until: str | None = Form(None),
    is_active: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    form_data = {
        "first_name": first_name, "last_name": last_name,
        "gender": clean_optional_string(gender), "phone": clean_optional_string(phone),
        "email": clean_optional_string(email), "reference_code": clean_optional_string(reference_code),
        "valid_from": valid_from or "", "valid_until": valid_until or "",
        "is_active": is_active == "on", "notes": clean_optional_string(notes),
    }
    try:
        payload = AuthorizedUserCreate(
            first_name=first_name, last_name=last_name,
            gender=clean_optional_string(gender), phone=clean_optional_string(phone),
            email=clean_optional_string(email), reference_code=clean_optional_string(reference_code),
            valid_from=parse_optional_datetime(valid_from),
            valid_until=parse_optional_datetime(valid_until),
            is_active=is_active == "on", notes=clean_optional_string(notes),
        )
        create_authorized_user_service(db, payload)
        return RedirectResponse(url=request.url_for("authorized_users.index"), status_code=303)
    except ValidationError as e:
        error_message = e.errors()[0]["msg"] if e.errors() else "Données invalides."
        return templates.TemplateResponse(
            request=request, name="authorized_users/create.html",
            context={"request": request, "error": error_message, "form_data": form_data, "current_user": current_user},
            status_code=400,
        )
    except AuthorizedUserServiceError as e:
        return templates.TemplateResponse(
            request=request, name="authorized_users/create.html",
            context={"request": request, "error": str(e), "form_data": form_data, "current_user": current_user},
            status_code=400,
        )


@router.get("/authorized-users/{authorized_user_id}/edit", name="authorized_users.edit", response_class=HTMLResponse)
def authorized_users_edit_page(
    authorized_user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    user = get_authorized_user_by_id(db, authorized_user_id)
    if not user:
        return RedirectResponse(url=request.url_for("authorized_users.index"), status_code=303)

    form_data = {
        "first_name": user.first_name, "last_name": user.last_name,
        "gender": user.gender or "", "phone": user.phone or "",
        "email": user.email or "", "reference_code": user.reference_code or "",
        "valid_from": user.valid_from.strftime("%Y-%m-%dT%H:%M") if user.valid_from else "",
        "valid_until": user.valid_until.strftime("%Y-%m-%dT%H:%M") if user.valid_until else "",
        "is_active": user.is_active, "notes": user.notes or "",
    }
    return templates.TemplateResponse(
        request=request, name="authorized_users/edit.html",
        context={"request": request, "user": user, "error": None, "form_data": form_data, "current_user": current_user},
    )


@router.post("/authorized-users/{authorized_user_id}/edit", name="authorized_users.edit.store", response_class=HTMLResponse)
def authorized_users_update(
    authorized_user_id: int,
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    gender: str | None = Form(None),
    phone: str | None = Form(None),
    email: str | None = Form(None),
    reference_code: str | None = Form(None),
    valid_from: str | None = Form(None),
    valid_until: str | None = Form(None),
    is_active: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    user = get_authorized_user_by_id(db, authorized_user_id)
    if not user:
        return RedirectResponse(url=request.url_for("authorized_users.index"), status_code=303)

    form_data = {
        "first_name": first_name, "last_name": last_name,
        "gender": clean_optional_string(gender), "phone": clean_optional_string(phone),
        "email": clean_optional_string(email), "reference_code": clean_optional_string(reference_code),
        "valid_from": valid_from or "", "valid_until": valid_until or "",
        "is_active": is_active == "on", "notes": clean_optional_string(notes),
    }
    try:
        payload = AuthorizedUserUpdate(
            first_name=first_name, last_name=last_name,
            gender=clean_optional_string(gender), phone=clean_optional_string(phone),
            email=clean_optional_string(email), reference_code=clean_optional_string(reference_code),
            valid_from=parse_optional_datetime(valid_from),
            valid_until=parse_optional_datetime(valid_until),
            is_active=is_active == "on", notes=clean_optional_string(notes),
        )
        update_authorized_user_service(db, authorized_user_id, payload)
        return RedirectResponse(
            url=request.url_for("authorized_users.show", authorized_user_id=authorized_user_id),
            status_code=303,
        )
    except ValidationError as e:
        error_message = e.errors()[0]["msg"] if e.errors() else "Données invalides."
        return templates.TemplateResponse(
            request=request, name="authorized_users/edit.html",
            context={"request": request, "user": user, "error": error_message, "form_data": form_data, "current_user": current_user},
            status_code=400,
        )
    except AuthorizedUserServiceError as e:
        return templates.TemplateResponse(
            request=request, name="authorized_users/edit.html",
            context={"request": request, "user": user, "error": str(e), "form_data": form_data, "current_user": current_user},
            status_code=400,
        )


@router.post("/authorized-users/{authorized_user_id}/delete", name="authorized_users.delete")
def authorized_users_delete(
    request: Request,
    authorized_user_id: int,
    db: Session = Depends(get_db),
):
    try:
        soft_delete_authorized_user_service(db, authorized_user_id)
    except AuthorizedUserServiceError:
        pass
    return RedirectResponse(
        url=request.url_for("authorized_users.show", authorized_user_id=authorized_user_id),
        status_code=303,
    )


@router.get("/authorized-users/{authorized_user_id}", name="authorized_users.show", response_class=HTMLResponse)
def authorized_users_show(
    authorized_user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    user = get_authorized_user_by_id(db, authorized_user_id)
    if not user:
        return RedirectResponse(url=request.url_for("authorized_users.index"), status_code=303)
    return templates.TemplateResponse(
        request=request, name="authorized_users/show.html",
        context={"request": request, "user": user, "current_user": current_user},
    )
