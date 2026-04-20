from fastapi import APIRouter, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.config import settings

from app.core.database import get_db
from app.models.staff_user import StaffUser
from app.core.security import verify_password

router = APIRouter()
templates = Jinja2Templates(directory=settings.template_path)


@router.get("/login", name="auth.login.index",response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={"request": request},
    )


@router.post("/login", name="auth.login.store",response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    email = email.strip()
    password = password.strip()

    if not email or not password:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "request": request,
                "error": "L’adresse e-mail et le mot de passe sont obligatoires.",
            },
            status_code=400,
        )

    user = db.query(StaffUser).filter(StaffUser.email == email).first()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "request": request,
                "error": "Adresse e-mail ou mot de passe incorrect.",
            },
            status_code=400,
        )

    if not user.is_active:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "request": request,
                "error": "Ce compte est inactif.",
            },
            status_code=400,
        )

    request.session["user_id"] = user.id
    request.session["full_name"] = f"{user.first_name} {user.last_name}"
    request.session["role_name"] = user.role.name if user.role else ""

    return RedirectResponse(url=request.url_for('dashboard.index'), status_code=303)


@router.get("/logout",name="auth.logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url=request.url_for('auth.login.index'), status_code=303)