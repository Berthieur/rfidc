from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.config import settings

from app.core.database import get_db
from app.core.dependencies import require_agent_or_admin
from app.crud.access_log import (
    get_access_log_by_id,
    get_access_logs_paginated,
    get_devices_for_access_log_filter,
    get_users_for_access_log_filter,
)
from app.models.staff_user import StaffUser
from app.schemas.access_log import AccessLogOut

router = APIRouter()
templates = Jinja2Templates(directory=settings.template_path)

DEFAULT_PER_PAGE = 10


def parse_optional_int(value: str | None) -> int | None:
    if not value or not value.strip():
        return None
    return int(value.strip())


def format_datetime_local(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%Y-%m-%dT%H:%M:%S")


def parse_datetime_local(value: str | None) -> datetime | None:
    if not value or not value.strip():
        return None
    raw = value.strip()
    try:
        if len(raw) == 16:
            return datetime.strptime(raw, "%Y-%m-%dT%H:%M")
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


@router.get("/access-logs", name="access_logs.index", response_class=HTMLResponse)
def access_logs_index(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=100),
    uid: str | None = Query(default=None),
    device_id: str | None = Query(default=None),
    authorized_user_id: str | None = Query(default=None),
    direction: str | None = Query(default=None),
    access_status: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    format: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    now = datetime.now()
    parsed_device_id = parse_optional_int(device_id)
    parsed_authorized_user_id = parse_optional_int(authorized_user_id)
    parsed_date_from = parse_datetime_local(date_from)
    parsed_date_to = parse_datetime_local(date_to)

    if parsed_date_to is None:
        parsed_date_to = now

    logs, total = get_access_logs_paginated(
        db,
        page=page,
        per_page=per_page,
        uid=uid,
        device_id=parsed_device_id,
        authorized_user_id=parsed_authorized_user_id,
        direction=direction,
        access_status=access_status,
        date_from=parsed_date_from,
        date_to=parsed_date_to,
    )

    total_pages = max(1, (total + per_page - 1) // per_page)

    # ── JSON response for Flutter ─────────────────────────────────────────────
    if format == "json":
        items = [AccessLogOut.model_validate(log).model_dump(mode="json") for log in logs]
        return JSONResponse({
            "items": items,
            "total": total,
            "page": page,
            "total_pages": total_pages,
        })

    # ── HTML response for web browser ─────────────────────────────────────────
    devices = get_devices_for_access_log_filter(db)
    users = get_users_for_access_log_filter(db)
    has_previous = page > 1
    has_next = page < total_pages
    page_numbers = list(range(max(1, page - 2), min(total_pages, page + 2) + 1))

    filters = {
        "uid": uid or "",
        "device_id": parsed_device_id,
        "authorized_user_id": parsed_authorized_user_id,
        "direction": direction or "",
        "access_status": access_status or "",
        "date_from": format_datetime_local(parsed_date_from),
        "date_to": format_datetime_local(parsed_date_to),
    }

    return templates.TemplateResponse(
        request=request,
        name="access_logs/index.html",
        context={
            "request": request,
            "logs": logs,
            "devices": devices,
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


@router.get("/access-logs/{access_log_id}", name="access_logs.show", response_class=HTMLResponse)
def access_logs_show(
    access_log_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    log = get_access_log_by_id(db, access_log_id)

    if not log:
        return RedirectResponse(url=request.url_for('access_logs.index'), status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="access_logs/show.html",
        context={
            "request": request,
            "log": log,
            "current_user": current_user,
        },
    )
