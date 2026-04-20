from datetime import datetime
from app.core.config import settings

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin, require_agent_or_admin
from app.crud.rfid_assignment import (
    get_authorized_users_for_assignment_filter,
    get_rfid_assignment_by_id,
    get_rfid_assignments_paginated,
    get_rfid_cards_for_assignment_filter,
    get_staff_users_for_assignment_filter,
)
from app.crud.authorized_user import get_authorized_users
from app.crud.rfid_card import get_assignable_rfid_cards
from app.models.staff_user import StaffUser
from app.schemas.rfid_assignment import RfidAssignmentCreate, RfidAssignmentOut
from app.services.rfid_assignment_service import (
    RfidAssignmentServiceError,
    create_rfid_assignment_service,
    expire_rfid_assignment_service,
    revoke_rfid_assignment_service,
    unassign_rfid_assignment_service,
)

router = APIRouter()
templates = Jinja2Templates(directory=settings.template_path)

DEFAULT_PER_PAGE = 10
ASSIGNMENT_STATUSES = ["active", "expired", "unassigned", "revoked"]


def parse_optional_datetime(value: str | None) -> datetime | None:
    if not value or not value.strip():
        return None
    return datetime.fromisoformat(value)


def clean_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def parse_optional_int(value: str | None) -> int | None:
    if not value or not value.strip():
        return None
    return int(value.strip())


@router.get("/assignments", name="assignments.index", response_class=HTMLResponse)
def assignments_index(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=100),
    rfid_card_id: str | None = Query(default=None),
    authorized_user_id: str | None = Query(default=None),
    assigned_by_staff_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    format: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    parsed_rfid_card_id = parse_optional_int(rfid_card_id)
    parsed_authorized_user_id = parse_optional_int(authorized_user_id)
    parsed_assigned_by_staff_id = parse_optional_int(assigned_by_staff_id)

    assignments, total = get_rfid_assignments_paginated(
        db,
        page=page,
        per_page=per_page,
        rfid_card_id=parsed_rfid_card_id,
        authorized_user_id=parsed_authorized_user_id,
        assigned_by_staff_id=parsed_assigned_by_staff_id,
        status=status,
    )

    total_pages = max(1, (total + per_page - 1) // per_page)

    # ── JSON pour Flutter ──────────────────────────────────────────────────────
    if format == "json":
        items = [RfidAssignmentOut.model_validate(a).model_dump(mode="json") for a in assignments]
        return JSONResponse({
            "items": items,
            "total": total,
            "page": page,
            "total_pages": total_pages,
        })

    # ── HTML pour navigateur ───────────────────────────────────────────────────
    cards = get_rfid_cards_for_assignment_filter(db)
    users = get_authorized_users_for_assignment_filter(db)
    staff_users = get_staff_users_for_assignment_filter(db)

    has_previous = page > 1
    has_next = page < total_pages
    page_numbers = list(range(max(1, page - 2), min(total_pages, page + 2) + 1))

    filters = {
        "rfid_card_id": parsed_rfid_card_id,
        "authorized_user_id": parsed_authorized_user_id,
        "assigned_by_staff_id": parsed_assigned_by_staff_id,
        "status": status or "",
    }

    return templates.TemplateResponse(
        request=request,
        name="assignments/index.html",
        context={
            "request": request,
            "assignments": assignments,
            "cards": cards,
            "users": users,
            "staff_users": staff_users,
            "filters": filters,
            "statuses": ASSIGNMENT_STATUSES,
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


# ── JSON REST endpoints pour Flutter ──────────────────────────────────────────

@router.post("/assignments", name="assignments.api.create")
async def assignments_api_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    """Création d'une assignation via JSON (Flutter)."""
    body = await request.json()
    try:
        payload = RfidAssignmentCreate(**body)
        assignment = create_rfid_assignment_service(db, payload, assigned_by_staff_id=current_user.id)
        return JSONResponse(RfidAssignmentOut.model_validate(assignment).model_dump(mode="json"), status_code=201)
    except (ValidationError, RfidAssignmentServiceError) as e:
        return JSONResponse({"detail": str(e)}, status_code=400)


@router.post("/assignments/{assignment_id}/unassign", name="assignments.unassign")
async def assignments_unassign(
    request: Request,
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    """Supporte à la fois Flutter (JSON) et le navigateur (form)."""
    content_type = request.headers.get("content-type", "")
    notes = None

    if "application/json" in content_type:
        # Appel Flutter
        try:
            body = await request.json()
            notes = clean_optional_string(body.get("notes"))
        except Exception:
            pass
        try:
            unassign_rfid_assignment_service(db, assignment_id, notes=notes)
            return JSONResponse({"success": True})
        except RfidAssignmentServiceError as e:
            return JSONResponse({"detail": str(e)}, status_code=400)
    else:
        # Appel navigateur (form)
        form = await request.form()
        notes = clean_optional_string(form.get("notes"))
        try:
            unassign_rfid_assignment_service(db, assignment_id, notes=notes)
        except RfidAssignmentServiceError:
            pass
        return RedirectResponse(url=request.url_for('assignments.show', assignment_id=assignment_id), status_code=303)


@router.post("/assignments/{assignment_id}/revoke", name="assignments.revoke")
async def assignments_revoke(
    request: Request,
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    content_type = request.headers.get("content-type", "")
    notes = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            notes = clean_optional_string(body.get("notes"))
        except Exception:
            pass
        try:
            revoke_rfid_assignment_service(db, assignment_id, notes=notes)
            return JSONResponse({"success": True})
        except RfidAssignmentServiceError as e:
            return JSONResponse({"detail": str(e)}, status_code=400)
    else:
        form = await request.form()
        notes = clean_optional_string(form.get("notes"))
        try:
            revoke_rfid_assignment_service(db, assignment_id, notes=notes)
        except RfidAssignmentServiceError:
            pass
        return RedirectResponse(url=request.url_for('assignments.show', assignment_id=assignment_id), status_code=303)


@router.post("/assignments/{assignment_id}/expire", name="assignments.expire")
async def assignments_expire(
    request: Request,
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    content_type = request.headers.get("content-type", "")
    notes = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            notes = clean_optional_string(body.get("notes"))
        except Exception:
            pass
        try:
            expire_rfid_assignment_service(db, assignment_id, notes=notes)
            return JSONResponse({"success": True})
        except RfidAssignmentServiceError as e:
            return JSONResponse({"detail": str(e)}, status_code=400)
    else:
        form = await request.form()
        notes = clean_optional_string(form.get("notes"))
        try:
            expire_rfid_assignment_service(db, assignment_id, notes=notes)
        except RfidAssignmentServiceError:
            pass
        return RedirectResponse(url=request.url_for('assignments.show', assignment_id=assignment_id), status_code=303)


# ── HTML web endpoints ─────────────────────────────────────────────────────────

@router.get("/assignments/create", name="assignments.create.index", response_class=HTMLResponse)
def assignments_create_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    cards = get_assignable_rfid_cards(db)
    users = get_authorized_users(db)
    now = datetime.now()
    request.state.now = now

    return templates.TemplateResponse(
        request=request,
        name="assignments/create.html",
        context={
            "request": request,
            "error": None,
            "form_data": {},
            "cards": cards,
            "users": users,
            "current_user": current_user,
            "statuses": ASSIGNMENT_STATUSES,
        },
    )


@router.post("/assignments/create", name="assignments.create.store", response_class=HTMLResponse)
def assignments_store(
    request: Request,
    rfid_card_id: int = Form(...),
    authorized_user_id: int = Form(...),
    assigned_at: str | None = Form(None),
    expired_at: str | None = Form(None),
    unassigned_at: str | None = Form(None),
    status: str = Form(...),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    cards = get_assignable_rfid_cards(db)
    users = get_authorized_users(db)

    form_data = {
        "rfid_card_id": rfid_card_id,
        "authorized_user_id": authorized_user_id,
        "assigned_at": assigned_at or "",
        "expired_at": expired_at or "",
        "unassigned_at": unassigned_at or "",
        "status": status,
        "notes": clean_optional_string(notes),
    }

    try:
        payload = RfidAssignmentCreate(
            rfid_card_id=rfid_card_id,
            authorized_user_id=authorized_user_id,
            assigned_at=parse_optional_datetime(assigned_at),
            expired_at=parse_optional_datetime(expired_at),
            unassigned_at=parse_optional_datetime(unassigned_at),
            status=status,
            notes=clean_optional_string(notes),
        )
        create_rfid_assignment_service(db, payload, assigned_by_staff_id=current_user.id)
        return RedirectResponse(url=str(request.url_for("assignments.index")), status_code=303)

    except ValidationError as e:
        error_message = e.errors()[0]["msg"] if e.errors() else "Données invalides."
        return templates.TemplateResponse(
            request=request, name="assignments/create.html",
            context={"request": request, "error": error_message, "form_data": form_data,
                     "cards": cards, "users": users, "current_user": current_user, "statuses": ASSIGNMENT_STATUSES},
            status_code=400,
        )
    except RfidAssignmentServiceError as e:
        return templates.TemplateResponse(
            request=request, name="assignments/create.html",
            context={"request": request, "error": str(e), "form_data": form_data,
                     "cards": cards, "users": users, "current_user": current_user, "statuses": ASSIGNMENT_STATUSES},
            status_code=400,
        )


@router.get("/assignments/{assignment_id}", name="assignments.show", response_class=HTMLResponse)
def assignments_show(
    assignment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    assignment = get_rfid_assignment_by_id(db, assignment_id)
    if not assignment:
        return RedirectResponse(url=str(request.url_for("assignments.index")), status_code=303)

    return templates.TemplateResponse(
        request=request, name="assignments/show.html",
        context={"request": request, "assignment": assignment, "current_user": current_user},
    )
