from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.core.config import settings

from app.core.database import get_db
from app.core.dependencies import require_admin, require_agent_or_admin
from app.crud.device import get_device_by_id, get_devices_paginated
from app.models.staff_user import StaffUser
from app.schemas.device import DeviceCreate, DeviceOut, DeviceUpdate
from app.services.device_service import (
    DeviceServiceError,
    create_device_service,
    regenerate_device_token_service,
    update_device_service,
)

router = APIRouter()
templates = Jinja2Templates(directory=settings.template_path)

DEFAULT_PER_PAGE = 10


def clean_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


@router.get("/devices", name="devices.index", response_class=HTMLResponse)
def devices_index(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=100),
    search: str | None = Query(default=None),
    is_active: str | None = Query(default=None),
    format: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    devices, total = get_devices_paginated(db, page=page, per_page=per_page, search=search, is_active=is_active)
    total_pages = max(1, (total + per_page - 1) // per_page)

    # ── JSON pour Flutter ──────────────────────────────────────────────────────
    if format == "json":
        items = [DeviceOut.model_validate(d).model_dump(mode="json") for d in devices]
        return JSONResponse({"items": items, "total": total, "page": page, "total_pages": total_pages})

    # ── HTML ───────────────────────────────────────────────────────────────────
    has_previous = page > 1
    has_next = page < total_pages
    page_numbers = list(range(max(1, page - 2), min(total_pages, page + 2) + 1))
    filters = {"search": search or "", "is_active": is_active or ""}

    return templates.TemplateResponse(
        request=request, name="devices/index.html",
        context={
            "request": request, "devices": devices, "filters": filters,
            "current_page": page, "total": total, "total_pages": total_pages,
            "has_previous": has_previous, "has_next": has_next,
            "previous_page": page - 1, "next_page": page + 1,
            "page_numbers": page_numbers, "current_user": current_user,
        },
    )


# ── JSON REST endpoints for Flutter ───────────────────────────────────────────

@router.post("/devices", name="devices.api.create")
async def devices_api_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    body = await request.json()
    try:
        payload = DeviceCreate(**body)
        device, plain_token = create_device_service(db, payload)
        result = DeviceOut.model_validate(device).model_dump(mode="json")
        result["api_token"] = plain_token
        return JSONResponse(result, status_code=201)
    except (ValidationError, DeviceServiceError) as e:
        return JSONResponse({"detail": str(e)}, status_code=400)


@router.put("/devices/{device_id}", name="devices.api.update")
async def devices_api_update(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    body = await request.json()
    try:
        payload = DeviceUpdate(**body)
        device = update_device_service(db, device_id, payload)
        return JSONResponse(DeviceOut.model_validate(device).model_dump(mode="json"))
    except (ValidationError, DeviceServiceError) as e:
        return JSONResponse({"detail": str(e)}, status_code=400)


@router.post("/devices/{device_id}/regenerate-token", name="devices.regenerate_token.api")
def devices_api_regenerate_token(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    device = get_device_by_id(db, device_id)
    if not device:
        return JSONResponse({"detail": "Device non trouvé."}, status_code=404)
    try:
        updated_device, plain_token = regenerate_device_token_service(db, device_id)
        result = DeviceOut.model_validate(updated_device).model_dump(mode="json")
        result["api_token"] = plain_token
        return JSONResponse(result)
    except DeviceServiceError as e:
        return JSONResponse({"detail": str(e)}, status_code=400)


# ── HTML web endpoints ─────────────────────────────────────────────────────────

@router.get("/devices/create", name="devices.create.index", response_class=HTMLResponse)
def devices_create_page(
    request: Request,
    current_user: StaffUser = Depends(require_admin),
):
    return templates.TemplateResponse(
        request=request, name="devices/create.html",
        context={"request": request, "error": None, "form_data": {}, "current_user": current_user, "generated_token": None},
    )


@router.post("/devices/create", name="devices.create.store", response_class=HTMLResponse)
def devices_store(
    request: Request,
    device_name: str = Form(...),
    device_code: str = Form(...),
    location: str | None = Form(None),
    is_active: str | None = Form(None),
    api_token: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    form_data = {
        "device_name": device_name, "device_code": device_code,
        "location": clean_optional_string(location), "is_active": is_active == "on",
        "api_token": clean_optional_string(api_token),
    }
    try:
        payload = DeviceCreate(
            device_name=device_name, device_code=device_code,
            location=clean_optional_string(location), is_active=is_active == "on",
            api_token=clean_optional_string(api_token),
        )
        device, plain_token = create_device_service(db, payload)
        return templates.TemplateResponse(
            request=request, name="devices/show_created_token.html",
            context={"request": request, "device": device, "generated_token": plain_token, "current_user": current_user},
        )
    except ValidationError as e:
        error_message = e.errors()[0]["msg"] if e.errors() else "Données invalides."
        return templates.TemplateResponse(
            request=request, name="devices/create.html",
            context={"request": request, "error": error_message, "form_data": form_data, "current_user": current_user, "generated_token": None},
            status_code=400,
        )
    except DeviceServiceError as e:
        return templates.TemplateResponse(
            request=request, name="devices/create.html",
            context={"request": request, "error": str(e), "form_data": form_data, "current_user": current_user, "generated_token": None},
            status_code=400,
        )


@router.get("/devices/{device_id}", name="devices.show", response_class=HTMLResponse)
def devices_show(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    device = get_device_by_id(db, device_id)
    if not device:
        return RedirectResponse(url=request.url_for('devices.index'), status_code=303)
    return templates.TemplateResponse(
        request=request, name="devices/show.html",
        context={"request": request, "device": device, "current_user": current_user, "error": None},
    )


@router.get("/devices/{device_id}/edit", name="devices.edit.show", response_class=HTMLResponse)
def devices_edit_page(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    device = get_device_by_id(db, device_id)
    if not device:
        return RedirectResponse(url=request.url_for('devices.index'), status_code=303)

    form_data = {
        "device_name": device.device_name, "device_code": device.device_code,
        "location": device.location or "", "is_active": device.is_active,
    }
    return templates.TemplateResponse(
        request=request, name="devices/edit.html",
        context={"request": request, "device": device, "error": None, "form_data": form_data, "current_user": current_user},
    )


@router.post("/devices/{device_id}/edit", name="devices.edit.store", response_class=HTMLResponse)
def devices_update(
    device_id: int,
    request: Request,
    device_name: str = Form(...),
    device_code: str = Form(...),
    location: str | None = Form(None),
    is_active: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    device = get_device_by_id(db, device_id)
    if not device:
        return RedirectResponse(url="/devices", status_code=303)

    form_data = {
        "device_name": device_name, "device_code": device_code,
        "location": clean_optional_string(location), "is_active": is_active == "on",
    }
    try:
        payload = DeviceUpdate(
            device_name=device_name, device_code=device_code,
            location=clean_optional_string(location), is_active=is_active == "on",
        )
        update_device_service(db, device_id, payload)
        return RedirectResponse(url=request.url_for('devices.show', device_id=device_id), status_code=303)
    except ValidationError as e:
        error_message = e.errors()[0]["msg"] if e.errors() else "Données invalides."
        return templates.TemplateResponse(
            request=request, name="devices/edit.html",
            context={"request": request, "device": device, "error": error_message, "form_data": form_data, "current_user": current_user},
            status_code=400,
        )
    except DeviceServiceError as e:
        return templates.TemplateResponse(
            request=request, name="devices/edit.html",
            context={"request": request, "device": device, "error": str(e), "form_data": form_data, "current_user": current_user},
            status_code=400,
        )


@router.post("/devices/{device_id}/regenerate-token/web", name="devices.regenerate_token.web", response_class=HTMLResponse)
def devices_regenerate_token_web(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    device = get_device_by_id(db, device_id)
    if not device:
        return RedirectResponse(url=request.url_for('devices.index'), status_code=303)
    try:
        updated_device, plain_token = regenerate_device_token_service(db, device_id)
        return templates.TemplateResponse(
            request=request, name="devices/show_created_token.html",
            context={"request": request, "device": updated_device, "generated_token": plain_token, "current_user": current_user},
        )
    except DeviceServiceError as e:
        return templates.TemplateResponse(
            request=request, name="devices/show.html",
            context={"request": request, "device": device, "current_user": current_user, "error": str(e)},
            status_code=400,
        )
