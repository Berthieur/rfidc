from datetime import datetime, time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.config import settings

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.access_log import AccessLog
from app.models.authorized_user import AuthorizedUser
from app.models.device import Device
from app.models.rfid_assignment import RfidAssignment
from app.models.rfid_card import RfidCard
from app.models.staff_user import StaffUser

router = APIRouter()
templates = Jinja2Templates(directory=settings.template_path)


def _build_kpis(db: Session) -> dict:
    now = datetime.now()
    today_start = datetime.combine(now.date(), time.min)
    today_end = datetime.combine(now.date(), time.max)

    def count(q): return q.scalar() or 0

    return {
        "granted_today": count(db.query(func.count(AccessLog.id)).filter(
            AccessLog.access_status == "granted",
            AccessLog.scanned_at >= today_start, AccessLog.scanned_at <= today_end,
        )),
        "denied_today": count(db.query(func.count(AccessLog.id)).filter(
            AccessLog.access_status == "denied",
            AccessLog.scanned_at >= today_start, AccessLog.scanned_at <= today_end,
        )),
        "ignored_today": count(db.query(func.count(AccessLog.id)).filter(
            AccessLog.access_status == "ignored",
            AccessLog.scanned_at >= today_start, AccessLog.scanned_at <= today_end,
        )),
        "entries_today": count(db.query(func.count(AccessLog.id)).filter(
            AccessLog.access_status == "granted",
            AccessLog.access_direction == "entry",
            AccessLog.scanned_at >= today_start, AccessLog.scanned_at <= today_end,
        )),
        "active_authorized_users": count(db.query(func.count(AuthorizedUser.id)).filter(
            AuthorizedUser.deleted_at.is_(None), AuthorizedUser.is_active.is_(True),
        )),
        "active_assignments": count(db.query(func.count(RfidAssignment.id)).filter(
            RfidAssignment.status == "active",
        )),
        "available_cards": count(db.query(func.count(RfidCard.id)).filter(
            RfidCard.status == "available",
        )),
        "active_devices": count(db.query(func.count(Device.id)).filter(
            Device.is_active.is_(True),
        )),
        "expired_users": count(db.query(func.count(AuthorizedUser.id)).filter(
            AuthorizedUser.deleted_at.is_(None),
            AuthorizedUser.valid_until.is_not(None),
            AuthorizedUser.valid_until < now,
        )),
        "expired_assignments": count(db.query(func.count(RfidAssignment.id)).filter(
            RfidAssignment.expired_at.is_not(None),
            RfidAssignment.expired_at < now,
        )),
        "abnormal_cards": count(db.query(func.count(RfidCard.id)).filter(
            RfidCard.status.in_(["blocked", "lost", "damaged", "inactive"]),
        )),
        "inactive_devices": count(db.query(func.count(Device.id)).filter(
            Device.is_active.is_(False),
        )),
    }


# ── JSON endpoint pour Flutter ────────────────────────────────────────────────
@router.get("/dashboard/stats", name="dashboard.stats")
def dashboard_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user),
):
    """Retourne les KPIs en JSON pour l'application Flutter."""
    return JSONResponse(_build_kpis(db))


# ── HTML endpoint pour le navigateur ─────────────────────────────────────────
@router.get("/dashboard", name="dashboard.index", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user),
):
    kpis = _build_kpis(db)

    recent_events = (
        db.query(AccessLog)
        .order_by(AccessLog.scanned_at.desc(), AccessLog.id.desc())
        .limit(5)
        .all()
    )

    recent_denied_events = (
        db.query(AccessLog)
        .filter(AccessLog.access_status == "denied")
        .order_by(AccessLog.scanned_at.desc(), AccessLog.id.desc())
        .limit(5)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={
            "request": request,
            "current_user": current_user,
            "kpis": kpis,
            "recent_events": recent_events,
            "recent_denied_events": recent_denied_events,
        },
    )
