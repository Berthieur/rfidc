from datetime import datetime

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.core.config import settings

from app.core.database import get_db
from app.core.dependencies import require_admin, require_agent_or_admin
from app.crud.rfid_card import get_rfid_card_by_id, get_rfid_cards_paginated
from app.models.staff_user import StaffUser
from app.schemas.rfid_card import RfidCardCreate, RfidCardOut, RfidCardUpdate
from app.services.rfid_card_service import (
    RfidCardServiceError,
    create_rfid_card_service,
    update_rfid_card_service,
)
from app.services.rfid_uid_capture_service import (
    start_uid_capture,
    get_uid_capture_status,
    reset_uid_capture,
)

router = APIRouter()
templates = Jinja2Templates(directory=settings.template_path)

DEFAULT_PER_PAGE = 10
RFID_CARD_STATUSES = ["available", "assigned", "lost", "blocked", "damaged", "inactive"]


def parse_optional_datetime(value: str | None) -> datetime | None:
    if not value or not value.strip():
        return None
    return datetime.fromisoformat(value)


def clean_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


@router.get("/rfid-cards", name="rfid_cards.index", response_class=HTMLResponse)
def rfid_cards_index(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=100),
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    format: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    cards, total = get_rfid_cards_paginated(db, page=page, per_page=per_page, search=search, status=status)
    total_pages = max(1, (total + per_page - 1) // per_page)

    # ── JSON pour Flutter ──────────────────────────────────────────────────────
    if format == "json":
        items = [RfidCardOut.model_validate(c).model_dump(mode="json") for c in cards]
        return JSONResponse({"items": items, "total": total, "page": page, "total_pages": total_pages})

    # ── HTML ───────────────────────────────────────────────────────────────────
    has_previous = page > 1
    has_next = page < total_pages
    page_numbers = list(range(max(1, page - 2), min(total_pages, page + 2) + 1))
    filters = {"search": search or "", "status": status or ""}

    return templates.TemplateResponse(
        request=request, name="rfid_cards/index.html",
        context={
            "request": request, "cards": cards, "filters": filters, "statuses": RFID_CARD_STATUSES,
            "current_page": page, "total": total, "total_pages": total_pages,
            "has_previous": has_previous, "has_next": has_next,
            "previous_page": page - 1, "next_page": page + 1,
            "page_numbers": page_numbers, "current_user": current_user,
        },
    )


# ── JSON REST endpoints pour Flutter ──────────────────────────────────────────

@router.post("/rfid-cards", name="rfid_cards.api.create")
async def rfid_cards_api_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    body = await request.json()
    try:
        payload = RfidCardCreate(**body)
        card = create_rfid_card_service(db, payload)
        return JSONResponse(RfidCardOut.model_validate(card).model_dump(mode="json"), status_code=201)
    except (ValidationError, RfidCardServiceError) as e:
        return JSONResponse({"detail": str(e)}, status_code=400)


@router.put("/rfid-cards/{rfid_card_id}", name="rfid_cards.api.update")
async def rfid_cards_api_update(
    rfid_card_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    body = await request.json()
    try:
        payload = RfidCardUpdate(**body)
        card = update_rfid_card_service(db, rfid_card_id, payload)
        return JSONResponse(RfidCardOut.model_validate(card).model_dump(mode="json"))
    except (ValidationError, RfidCardServiceError) as e:
        return JSONResponse({"detail": str(e)}, status_code=400)


# ── UID Capture (JSON — déjà fonctionnel) ─────────────────────────────────────

@router.post("/rfid-cards/uid-capture/start", name="rfid_cards.uid_capture.start")
def rfid_cards_start_uid_capture(current_user: StaffUser = Depends(require_admin)):
    capture = start_uid_capture(timeout_seconds=15)
    return JSONResponse({"success": True, "capture_id": capture["capture_id"], "status": "waiting", "expires_in": 15})


@router.get("/rfid-cards/uid-capture/status/{capture_id}", name="rfid_cards.uid_capture.status")
def rfid_cards_uid_capture_status(capture_id: str, current_user: StaffUser = Depends(require_admin)):
    return JSONResponse(get_uid_capture_status(capture_id))


@router.post("/rfid-cards/uid-capture/reset", name="rfid_cards.uid_capture.reset")
def rfid_cards_uid_capture_reset(current_user: StaffUser = Depends(require_admin)):
    reset_uid_capture()
    return JSONResponse({"success": True})


# ── HTML web endpoints ─────────────────────────────────────────────────────────

@router.get("/rfid-cards/create", name="rfid_cards.create.index", response_class=HTMLResponse)
def rfid_cards_create_page(request: Request, current_user: StaffUser = Depends(require_admin)):
    return templates.TemplateResponse(
        request=request, name="rfid_cards/create.html",
        context={"request": request, "error": None, "form_data": {}, "current_user": current_user, "statuses": RFID_CARD_STATUSES},
    )


@router.post("/rfid-cards/create", name="rfid_cards.create.store", response_class=HTMLResponse)
def rfid_cards_store(
    request: Request,
    uid: str = Form(...),
    card_label: str | None = Form(None),
    status: str = Form(...),
    issued_at: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    form_data = {"uid": uid, "card_label": clean_optional_string(card_label), "status": status, "issued_at": issued_at or "", "notes": clean_optional_string(notes)}
    try:
        payload = RfidCardCreate(uid=uid, card_label=clean_optional_string(card_label), status=status, issued_at=parse_optional_datetime(issued_at), notes=clean_optional_string(notes))
        create_rfid_card_service(db, payload)
        return RedirectResponse(url=request.url_for('rfid_cards.index'), status_code=303)
    except ValidationError as e:
        error_message = e.errors()[0]["msg"] if e.errors() else "Données invalides."
        return templates.TemplateResponse(request=request, name="rfid_cards/create.html",
            context={"request": request, "error": error_message, "form_data": form_data, "current_user": current_user, "statuses": RFID_CARD_STATUSES}, status_code=400)
    except RfidCardServiceError as e:
        return templates.TemplateResponse(request=request, name="rfid_cards/create.html",
            context={"request": request, "error": str(e), "form_data": form_data, "current_user": current_user, "statuses": RFID_CARD_STATUSES}, status_code=400)


@router.get("/rfid-cards/{rfid_card_id}", name="rfid_cards.show", response_class=HTMLResponse)
def rfid_cards_show(rfid_card_id: int, request: Request, db: Session = Depends(get_db), current_user: StaffUser = Depends(require_agent_or_admin)):
    card = get_rfid_card_by_id(db, rfid_card_id)
    if not card:
        return RedirectResponse(url=request.url_for('rfid_cards.index'), status_code=303)
    return templates.TemplateResponse(request=request, name="rfid_cards/show.html",
        context={"request": request, "card": card, "current_user": current_user})


@router.get("/rfid-cards/{rfid_card_id}/edit", name="rfid_cards.edit.show", response_class=HTMLResponse)
def rfid_cards_edit_page(rfid_card_id: int, request: Request, db: Session = Depends(get_db), current_user: StaffUser = Depends(require_admin)):
    card = get_rfid_card_by_id(db, rfid_card_id)
    if not card:
        return RedirectResponse(url=request.url_for('rfid_cards.index'), status_code=303)
    form_data = {"uid": card.uid, "card_label": card.card_label or "", "status": card.status,
        "issued_at": card.issued_at.strftime("%Y-%m-%dT%H:%M") if card.issued_at else "", "notes": card.notes or ""}
    return templates.TemplateResponse(request=request, name="rfid_cards/edit.html",
        context={"request": request, "card": card, "error": None, "form_data": form_data, "current_user": current_user, "statuses": RFID_CARD_STATUSES})


@router.post("/rfid-cards/{rfid_card_id}/edit", name="rfid_cards.edit.store", response_class=HTMLResponse)
def rfid_cards_update(
    rfid_card_id: int, request: Request,
    uid: str = Form(...), card_label: str | None = Form(None), status: str = Form(...),
    issued_at: str | None = Form(None), notes: str | None = Form(None),
    db: Session = Depends(get_db), current_user: StaffUser = Depends(require_admin),
):
    card = get_rfid_card_by_id(db, rfid_card_id)
    if not card:
        return RedirectResponse(url=request.url_for('rfid_cards.index'), status_code=303)
    form_data = {"uid": uid, "card_label": clean_optional_string(card_label), "status": status, "issued_at": issued_at or "", "notes": clean_optional_string(notes)}
    try:
        payload = RfidCardUpdate(uid=uid, card_label=clean_optional_string(card_label), status=status, issued_at=parse_optional_datetime(issued_at), notes=clean_optional_string(notes))
        update_rfid_card_service(db, rfid_card_id, payload)
        return RedirectResponse(url=request.url_for('rfid_cards.show', rfid_card_id=rfid_card_id), status_code=303)
    except ValidationError as e:
        error_message = e.errors()[0]["msg"] if e.errors() else "Données invalides."
        return templates.TemplateResponse(request=request, name="rfid_cards/edit.html",
            context={"request": request, "card": card, "error": error_message, "form_data": form_data, "current_user": current_user, "statuses": RFID_CARD_STATUSES}, status_code=400)
    except RfidCardServiceError as e:
        return templates.TemplateResponse(request=request, name="rfid_cards/edit.html",
            context={"request": request, "card": card, "error": str(e), "form_data": form_data, "current_user": current_user, "statuses": RFID_CARD_STATUSES}, status_code=400)
