from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse


class AuthRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        user_id = request.session.get("user_id")

        public_paths = {
            "/",
            "/logout",
            "/openapi.json",
            "/docs",
            "/docs/oauth2-redirect",
            "/redoc",
        }

        public_prefixes = (
            "/static/",
            "/api/",
            "/esp32/",
        )

        if path.startswith(public_prefixes):
            return await call_next(request)

        if path == request.url_for("auth.login.index").path and user_id:
            return RedirectResponse(url=request.url_for("dashboard.index"), status_code=303)

        if path in public_paths or path == request.url_for("auth.login.index").path:
            return await call_next(request)

        if not user_id:
            # Si la requête attend du JSON (Flutter / API), retourner 401 JSON
            accept = request.headers.get("accept", "")
            content_type = request.headers.get("content-type", "")
            is_api_request = (
                "application/json" in accept
                or "application/json" in content_type
                or request.query_params.get("format") == "json"
            )

            if is_api_request:
                return JSONResponse(
                    {"detail": "Non authentifié. Veuillez vous connecter."},
                    status_code=401,
                )

            # Sinon rediriger vers /login (navigateur web)
            return RedirectResponse(url=request.url_for("auth.login.index"), status_code=303)

        return await call_next(request)
