from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.api.esp32.enrollment import router as esp32_enrollment_router

from app.core.config import settings
from app.middleware.auth_redirect import AuthRedirectMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.authorized_users import router as authorized_users_router
from app.api.routes.rfid_cards import router as rfid_cards_router
from app.api.routes.assignments import router as assignments_router
from app.api.routes.devices import router as devices_router
from app.api.esp32.access import router as esp32_access_router
from app.api.routes.access_logs import router as access_logs_router

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.APP_DEBUG,
)


app.add_middleware(AuthRedirectMiddleware)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
)

app.mount("/static", StaticFiles(directory=settings.static_path), name="static")
templates = Jinja2Templates(directory=settings.template_path)

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(authorized_users_router)
app.include_router(rfid_cards_router)
app.include_router(assignments_router)
app.include_router(devices_router)
app.include_router(esp32_access_router)
app.include_router(access_logs_router)
app.include_router(esp32_enrollment_router)


@app.get("/")
def home(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url=request.url_for('login.index'), status_code=303)